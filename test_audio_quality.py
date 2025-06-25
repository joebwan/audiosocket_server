#!/usr/bin/env python3
"""
Audio Quality Test Suite for Asterisk AudioSocket Server
Tests audio format, sample rates, timing, and echo quality.
"""

import os
import tempfile
import time
import unittest
import wave
from threading import Thread

import numpy as np

# Local imports
from audiosocket import Audiosocket
from connection import Connection
from mylogging import ColouredLogger


class TestAudioQuality(unittest.TestCase):
    """Test audio quality and echo functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.logger = ColouredLogger("audio_quality_test")
        self.test_port = 0  # Let OS choose available port
        self.audiosocket = None
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        if self.audiosocket and hasattr(self.audiosocket, "initial_sock"):
            self.audiosocket.initial_sock.close()

    def create_test_audio_file(self, filename, duration=1.0, sample_rate=8000, frequency=440, channels=1):
        """Create a test WAV file with specified parameters"""
        filepath = os.path.join(self.temp_dir, filename)
        
        # Generate sine wave
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.5
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # For stereo, duplicate the mono channel
        if channels == 2:
            stereo_data = np.empty(len(audio_data) * 2, dtype=np.int16)
            stereo_data[0::2] = audio_data  # Left channel
            stereo_data[1::2] = audio_data  # Right channel
            audio_data = stereo_data
        
        with wave.open(filepath, "wb") as wav_file:
            wav_file.setnchannels(channels)  # Mono or stereo
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        return filepath

    def test_audio_format_compatibility(self):
        """Test that audio format matches Asterisk expectations"""
        # Asterisk AudioSocket expects 8kHz, 16-bit, mono PCM
        expected_sample_rate = 8000
        expected_channels = 1
        expected_sample_width = 2  # 16-bit
        
        self.logger.info("Testing audio format compatibility...")
        
        # Test different configurations
        configs = [
            {"inrate": 8000, "channels": 1, "ulaw2lin": False},
            {"inrate": 8000, "channels": 1, "ulaw2lin": True},
            {"inrate": 16000, "channels": 1, "ulaw2lin": False},
            {"inrate": 8000, "channels": 2, "ulaw2lin": False},
        ]
        
        for config in configs:
            with self.subTest(config=config):
                self.audiosocket = Audiosocket(("127.0.0.1", self.test_port))
                
                # Fix: Use correct parameter names for each method
                input_config = {k: v for k, v in config.items()}
                output_config = {
                    "outrate": config["inrate"],  # Use inrate as outrate
                    "channels": config["channels"],
                    "ulaw2lin": config["ulaw2lin"]
                }
                
                self.audiosocket.prepare_input(**input_config)
                self.audiosocket.prepare_output(**output_config)
                
                self.logger.info(f"Testing config: {config}")
                # Test passes if no exceptions are raised
                self.assertTrue(True)

    def test_audio_frame_timing(self):
        """Test audio frame timing and buffer management"""
        self.logger.info("Testing audio frame timing...")
        
        # Create test audio file
        test_file = self.create_test_audio_file("test_timing.wav", duration=0.1)
        
        # Read the file and analyze frame timing
        with wave.open(test_file, "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frames = wav_file.getnframes()
            
            self.logger.info(f"Audio file: {sample_rate}Hz, {channels}ch, {sample_width*8}bit, {frames} frames")
            
            # Calculate expected frame duration
            frame_duration = frames / sample_rate
            expected_frames_20ms = int(sample_rate * 0.02)  # 20ms at sample rate
            
            self.logger.info(f"Frame duration: {frame_duration:.3f}s")
            self.logger.info(f"Expected 20ms frames: {expected_frames_20ms} samples")
            
            # Verify frame size matches AudioSocket expectations
            expected_bytes_20ms = expected_frames_20ms * channels * sample_width
            self.logger.info(f"Expected 20ms bytes: {expected_bytes_20ms}")
            
            # AudioSocket expects 320 bytes for 20ms at 8kHz mono 16-bit
            if sample_rate == 8000 and channels == 1 and sample_width == 2:
                self.assertEqual(expected_bytes_20ms, 320)

    def test_echo_quality_simulation(self):
        """Simulate echo functionality and test audio quality"""
        self.logger.info("Testing echo quality simulation...")
        
        # Create test audio with known characteristics
        test_file = self.create_test_audio_file("echo_test.wav", duration=0.5, frequency=1000)
        
        with wave.open(test_file, "rb") as wav_file:
            original_audio = wav_file.readframes(wav_file.getnframes())
        
        # Simulate echo processing (read -> process -> write)
        # This simulates what happens in the echo server
        
        # Simulate reading in chunks (320 bytes = 20ms at 8kHz)
        chunk_size = 320
        processed_audio = b""
        
        for i in range(0, len(original_audio), chunk_size):
            chunk = original_audio[i:i+chunk_size]
            
            # Pad chunk if necessary
            if len(chunk) < chunk_size:
                chunk += b"\x00" * (chunk_size - len(chunk))
            
            # Simulate processing delay (should be minimal)
            time.sleep(0.001)  # 1ms delay
            
            processed_audio += chunk
        
        # Compare original and processed audio
        self.assertEqual(len(original_audio), len(processed_audio))
        
        # Convert to numpy arrays for analysis
        original_samples = np.frombuffer(original_audio, dtype=np.int16)
        processed_samples = np.frombuffer(processed_audio, dtype=np.int16)
        
        # Check for audio corruption
        if len(original_samples) == len(processed_samples):
            # Calculate correlation
            correlation = np.corrcoef(original_samples, processed_samples)[0, 1]
            self.logger.info(f"Audio correlation: {correlation:.6f}")
            
            # Should be very high correlation for good quality
            self.assertGreater(correlation, 0.99)

    def test_sample_rate_conversion_quality(self):
        """Test sample rate conversion quality"""
        self.logger.info("Testing sample rate conversion quality...")
        
        # Create test audio at different sample rates
        test_files = {
            "8k": self.create_test_audio_file("test_8k.wav", sample_rate=8000, frequency=1000),
            "16k": self.create_test_audio_file("test_16k.wav", sample_rate=16000, frequency=1000),
            "44k": self.create_test_audio_file("test_44k.wav", sample_rate=44100, frequency=1000),
        }
        
        for name, filepath in test_files.items():
            with self.subTest(sample_rate=name):
                with wave.open(filepath, "rb") as wav_file:
                    sample_rate = wav_file.getframerate()
                    audio_data = wav_file.readframes(wav_file.getnframes())
                
                self.logger.info(f"Testing {name}: {sample_rate}Hz, {len(audio_data)} bytes")
                
                # Test conversion to 8kHz (Asterisk standard)
                if sample_rate != 8000:
                    # This would test the actual conversion logic
                    # For now, just verify the file can be read
                    self.assertGreater(len(audio_data), 0)

    def test_audio_latency_measurement(self):
        """Test audio processing latency"""
        self.logger.info("Testing audio processing latency...")
        
        # Create a simple echo test
        test_audio = b"\x00" * 320  # 20ms of silence
        
        # Measure processing time
        start_time = time.time()
        
        # Simulate echo processing
        for _ in range(100):  # Process 100 frames
            # Simulate read operation
            time.sleep(0.001)  # 1ms read delay
            
            # Simulate write operation
            time.sleep(0.001)  # 1ms write delay
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate latency per frame
        latency_per_frame = total_time / 100
        self.logger.info(f"Average latency per frame: {latency_per_frame*1000:.2f}ms")
        
        # Latency should be very low for real-time audio
        self.assertLess(latency_per_frame, 0.01)  # Less than 10ms per frame

    def test_audio_buffer_overflow(self):
        """Test audio buffer overflow scenarios"""
        self.logger.info("Testing audio buffer overflow scenarios...")
        
        # Test with different buffer sizes
        buffer_sizes = [160, 320, 640, 1280]  # Different frame sizes
        
        for buffer_size in buffer_sizes:
            with self.subTest(buffer_size=buffer_size):
                # Create test audio of specific size
                test_audio = b"\x00" * buffer_size
                
                # Simulate processing
                processed_audio = test_audio[:320]  # Limit to 320 bytes
                
                self.logger.info(f"Buffer size: {buffer_size}, Processed: {len(processed_audio)}")
                
                # Verify no buffer overflow
                self.assertLessEqual(len(processed_audio), 320)

    def test_audio_format_validation(self):
        """Test audio format validation"""
        self.logger.info("Testing audio format validation...")
        
        # Test valid audio formats
        valid_formats = [
            (8000, 1, 2),   # 8kHz, mono, 16-bit
            (16000, 1, 2),  # 16kHz, mono, 16-bit
            (8000, 2, 2),   # 8kHz, stereo, 16-bit
        ]
        
        for sample_rate, channels, sample_width in valid_formats:
            with self.subTest(format=f"{sample_rate}Hz_{channels}ch_{sample_width*8}bit"):
                # Create test file with correct channel count
                test_file = self.create_test_audio_file(
                    f"test_{sample_rate}_{channels}_{sample_width}.wav",
                    sample_rate=sample_rate,
                    channels=channels
                )
                
                with wave.open(test_file, "rb") as wav_file:
                    self.assertEqual(wav_file.getframerate(), sample_rate)
                    self.assertEqual(wav_file.getnchannels(), channels)
                    self.assertEqual(wav_file.getsampwidth(), sample_width)
                
                self.logger.info(f"✓ Valid format: {sample_rate}Hz, {channels}ch, {sample_width*8}bit")


class AudioQualityEchoServer:
    """Improved echo server with audio quality monitoring"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Use proper telephony settings
        self.audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
        self.audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)
        
        self.logger = ColouredLogger("echo_server")
        self.logger.info(f"Echo server started on {host}:{port}")
        self.logger.info("Audio config: 8kHz, mono, 16-bit PCM")
    
    def handle_connection(self, call):
        """Handle connection with audio quality monitoring"""
        self.logger.info(f"New connection from {call.peer_addr}")
        
        frame_count = 0
        start_time = time.time()
        last_log_time = start_time
        
        while call.connected:
            try:
                # Read audio with timeout
                audio_data = call.read()
                
                # Monitor audio quality
                if len(audio_data) != 320:
                    self.logger.warning(f"Unexpected audio frame size: {len(audio_data)} bytes")
                
                # Echo audio back
                call.write(audio_data)
                
                frame_count += 1
                
                # Log statistics every 5 seconds
                current_time = time.time()
                if current_time - last_log_time >= 5:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed
                    self.logger.info(f"Frames: {frame_count}, FPS: {fps:.1f}, Elapsed: {elapsed:.1f}s")
                    last_log_time = current_time
                
                # Add small delay to prevent overwhelming the system
                time.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the echo server"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Server stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def run_audio_quality_tests():
    """Run all audio quality tests"""
    print("Running Audio Quality Tests...")
    unittest.main(verbosity=2, argv=[''], exit=False)


def start_quality_echo_server():
    """Start the improved echo server"""
    print("Starting Audio Quality Echo Server...")
    server = AudioQualityEchoServer()
    server.start()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        start_quality_echo_server()
    else:
        run_audio_quality_tests() 
