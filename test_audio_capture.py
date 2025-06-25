#!/usr/bin/env python3
"""
Test Audio Capture
Tests the audio capture server by sending test audio and verifying it saves correctly.
"""

import socket
import time
import threading
import wave
import os
from simple_audio_reception_test import SimpleAudioReceptionTest


class TestAudioCapture:
    """Test the audio capture server"""
    
    def __init__(self, host="127.0.0.1", port=6050):
        self.host = host
        self.port = port
        self.test_client = SimpleAudioReceptionTest(host, port)
        
    def start_capture_server(self):
        """Start the audio capture server in background"""
        from audio_capture_server import AudioCaptureServer
        
        self.logger.info("Starting audio capture server...")
        self.server = AudioCaptureServer(self.host, self.port)
        self.server_running = False
        
        def server_thread():
            try:
                self.server_running = True
                # Start server (this will block, so we run it in a thread)
                self.server.start()
            except Exception as e:
                self.logger.error(f"Server error: {e}")
                self.server_running = False
        
        # Start server thread
        server_thread = threading.Thread(target=server_thread)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        if not self.server_running:
            raise Exception("Server failed to start")
        
        self.logger.info("Audio capture server started successfully")
    
    def send_test_audio(self):
        """Send test audio to the capture server"""
        self.logger.info("Sending test audio to capture server...")
        
        # Use the existing test client to send audio
        self.test_client.send_test_audio()
        
        self.logger.info("Test audio sent")
    
    def verify_captured_audio(self):
        """Verify that audio was captured and saved correctly"""
        self.logger.info("Verifying captured audio...")
        
        # Look for WAV files in the captured_audio directory
        output_dir = "captured_audio"
        if not os.path.exists(output_dir):
            self.logger.error(f"Output directory {output_dir} not found")
            return False
        
        wav_files = [f for f in os.listdir(output_dir) if f.endswith('.wav')]
        if not wav_files:
            self.logger.error("No WAV files found in output directory")
            return False
        
        # Get the most recent WAV file
        latest_wav = max(wav_files, key=lambda f: os.path.getctime(os.path.join(output_dir, f)))
        wav_path = os.path.join(output_dir, latest_wav)
        
        self.logger.info(f"Found captured audio: {wav_path}")
        
        # Verify WAV file properties
        try:
            with wave.open(wav_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                frames = wav_file.getnframes()
                duration = frames / frame_rate
                
                self.logger.info(f"WAV file properties:")
                self.logger.info(f"  Channels: {channels}")
                self.logger.info(f"  Sample width: {sample_width} bytes ({sample_width*8}-bit)")
                self.logger.info(f"  Frame rate: {frame_rate} Hz")
                self.logger.info(f"  Frames: {frames}")
                self.logger.info(f"  Duration: {duration:.2f}s")
                
                # Verify expected properties
                if channels != 1:
                    self.logger.error(f"Expected 1 channel, got {channels}")
                    return False
                
                if sample_width != 2:
                    self.logger.error(f"Expected 2 bytes per sample (16-bit), got {sample_width}")
                    return False
                
                if frame_rate != 8000:
                    self.logger.error(f"Expected 8000 Hz, got {frame_rate}")
                    return False
                
                if duration < 0.5:  # Should be at least 0.5 seconds
                    self.logger.error(f"Audio too short: {duration:.2f}s")
                    return False
                
                self.logger.info("✅ WAV file properties are correct")
                
        except Exception as e:
            self.logger.error(f"Error reading WAV file: {e}")
            return False
        
        return True
    
    def run_test(self):
        """Run the audio capture test"""
        from mylogging import ColouredLogger
        self.logger = ColouredLogger("capture_test")
        
        self.logger.info("Audio Capture Test")
        self.logger.info("=" * 40)
        self.logger.info("Testing audio capture server with live audio")
        self.logger.info("")
        
        try:
            # Start capture server
            self.start_capture_server()
            
            # Send test audio
            self.send_test_audio()
            
            # Wait for server to process and save
            time.sleep(3)
            
            # Verify captured audio
            success = self.verify_captured_audio()
            
            if success:
                self.logger.info("")
                self.logger.info("=" * 40)
                self.logger.info("✅ TEST PASSED")
                self.logger.info("✅ Audio capture server is working correctly")
                self.logger.info("✅ Audio was captured and saved to WAV file")
                self.logger.info("=" * 40)
            else:
                self.logger.error("")
                self.logger.error("=" * 40)
                self.logger.error("❌ TEST FAILED")
                self.logger.error("❌ Audio capture verification failed")
                self.logger.error("=" * 40)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Test failed: {e}")
            return False


def main():
    """Main function"""
    test = TestAudioCapture()
    success = test.run_test()
    
    if success:
        print("\n✅ Audio capture test completed successfully!")
        print("You can now play the captured WAV file to verify audio quality.")
    else:
        print("\n❌ Audio capture test failed!")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 