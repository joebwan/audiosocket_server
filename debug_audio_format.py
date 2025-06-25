#!/usr/bin/env python3
"""
Audio Format Diagnostic Tool
Analyzes incoming audio from Asterisk to determine the actual format being sent.
"""

import time
import wave
import numpy as np
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class AudioFormatAnalyzer:
    """Analyzes incoming audio to determine format and configuration"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Start with 8kHz mono as default
        self.audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
        self.audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)
        
        self.logger = ColouredLogger("audio_analyzer")
        self.logger.info(f"Audio analyzer started on {host}:{port}")
        
        # Statistics tracking
        self.frame_sizes = []
        self.frame_timings = []
        self.last_frame_time = None
        
    def analyze_frame_size(self, frame_size):
        """Analyze what the frame size tells us about the audio format"""
        self.logger.info(f"Analyzing frame size: {frame_size} bytes")
        
        # Calculate possible configurations
        possibilities = []
        
        # 16-bit PCM calculations
        for sample_rate in [8000, 16000, 22050, 44100]:
            for channels in [1, 2]:
                for frame_duration in [0.01, 0.02, 0.04, 0.05]:  # 10ms, 20ms, 40ms, 50ms
                    expected_bytes = int(sample_rate * frame_duration * channels * 2)  # 16-bit = 2 bytes
                    if expected_bytes == frame_size:
                        possibilities.append({
                            'sample_rate': sample_rate,
                            'channels': channels,
                            'frame_duration': frame_duration,
                            'frame_duration_ms': frame_duration * 1000
                        })
        
        # 8-bit PCM calculations
        for sample_rate in [8000, 16000, 22050, 44100]:
            for channels in [1, 2]:
                for frame_duration in [0.01, 0.02, 0.04, 0.05]:
                    expected_bytes = int(sample_rate * frame_duration * channels * 1)  # 8-bit = 1 byte
                    if expected_bytes == frame_size:
                        possibilities.append({
                            'sample_rate': sample_rate,
                            'channels': channels,
                            'frame_duration': frame_duration,
                            'frame_duration_ms': frame_duration * 1000,
                            'bit_depth': 8
                        })
        
        # ULAW calculations (8-bit)
        for sample_rate in [8000, 16000, 22050, 44100]:
            for channels in [1, 2]:
                for frame_duration in [0.01, 0.02, 0.04, 0.05]:
                    expected_bytes = int(sample_rate * frame_duration * channels * 1)  # ULAW = 1 byte
                    if expected_bytes == frame_size:
                        possibilities.append({
                            'sample_rate': sample_rate,
                            'channels': channels,
                            'frame_duration': frame_duration,
                            'frame_duration_ms': frame_duration * 1000,
                            'format': 'ULAW'
                        })
        
        return possibilities
    
    def analyze_audio_content(self, audio_data):
        """Analyze the audio content to determine format"""
        if len(audio_data) == 0:
            return "Empty frame"
        
        # Convert to numpy array for analysis
        try:
            # Try 16-bit PCM first
            samples_16bit = np.frombuffer(audio_data, dtype=np.int16)
            
            # Check if it looks like valid 16-bit PCM
            if len(samples_16bit) * 2 == len(audio_data):
                # Analyze the values
                min_val = np.min(samples_16bit)
                max_val = np.max(samples_16bit)
                mean_val = np.mean(samples_16bit)
                std_val = np.std(samples_16bit)
                
                self.logger.info(f"16-bit PCM analysis:")
                self.logger.info(f"  Samples: {len(samples_16bit)}")
                self.logger.info(f"  Min: {min_val}, Max: {max_val}")
                self.logger.info(f"  Mean: {mean_val:.2f}, Std: {std_val:.2f}")
                
                # Check if it's likely ULAW (converted to PCM)
                if abs(mean_val) < 100 and std_val < 1000:
                    return "Likely ULAW converted to 16-bit PCM"
                else:
                    return "16-bit PCM"
            
            # Try 8-bit PCM
            samples_8bit = np.frombuffer(audio_data, dtype=np.uint8)
            if len(samples_8bit) == len(audio_data):
                min_val = np.min(samples_8bit)
                max_val = np.max(samples_8bit)
                mean_val = np.mean(samples_8bit)
                
                self.logger.info(f"8-bit analysis:")
                self.logger.info(f"  Samples: {len(samples_8bit)}")
                self.logger.info(f"  Min: {min_val}, Max: {max_val}")
                self.logger.info(f"  Mean: {mean_val:.2f}")
                
                # ULAW typically has values around 128 (silence)
                if 120 <= mean_val <= 136:
                    return "Likely ULAW"
                else:
                    return "8-bit PCM"
                    
        except Exception as e:
            self.logger.error(f"Error analyzing audio content: {e}")
        
        return "Unknown format"
    
    def handle_connection(self, call):
        """Handle connection and analyze audio format"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting audio format analysis...")
        
        frame_count = 0
        start_time = time.time()
        
        # Collect first few frames for analysis
        analysis_frames = []
        
        while call.connected and frame_count < 50:  # Analyze first 50 frames
            try:
                # Read audio data
                audio_data = call.read()
                current_time = time.time()
                
                frame_size = len(audio_data)
                self.frame_sizes.append(frame_size)
                
                # Track timing
                if self.last_frame_time:
                    interval = current_time - self.last_frame_time
                    self.frame_timings.append(interval)
                self.last_frame_time = current_time
                
                frame_count += 1
                
                # Store first few frames for detailed analysis
                if frame_count <= 5:
                    analysis_frames.append(audio_data)
                
                # Echo back to maintain connection
                call.write(audio_data)
                
                # Log frame info
                self.logger.info(f"Frame {frame_count}: {frame_size} bytes")
                
                # Analyze frame size possibilities
                if frame_count == 1:
                    possibilities = self.analyze_frame_size(frame_size)
                    self.logger.info("Possible audio configurations:")
                    for i, config in enumerate(possibilities):
                        self.logger.info(f"  {i+1}. {config['sample_rate']}Hz, {config['channels']}ch, "
                                       f"{config['frame_duration_ms']:.0f}ms frame")
                        if 'format' in config:
                            self.logger.info(f"     Format: {config['format']}")
                        if 'bit_depth' in config:
                            self.logger.info(f"     Bit depth: {config['bit_depth']}")
                
                # Analyze audio content of first frame
                if frame_count == 1:
                    format_analysis = self.analyze_audio_content(audio_data)
                    self.logger.info(f"Audio content analysis: {format_analysis}")
                
                # Add small delay
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error in analysis loop: {e}")
                break
        
        # Final analysis
        self.logger.info("\n" + "="*50)
        self.logger.info("FINAL ANALYSIS")
        self.logger.info("="*50)
        
        if self.frame_sizes:
            unique_sizes = set(self.frame_sizes)
            self.logger.info(f"Frame sizes observed: {unique_sizes}")
            
            if len(unique_sizes) == 1:
                frame_size = list(unique_sizes)[0]
                self.logger.info(f"Consistent frame size: {frame_size} bytes")
                
                # Recommend configuration
                if frame_size == 320:
                    self.logger.info("✓ Expected format: 8kHz, mono, 16-bit PCM, 20ms frames")
                elif frame_size == 640:
                    self.logger.info("⚠️  Detected format: Likely 16kHz, mono, 16-bit PCM, 20ms frames")
                    self.logger.info("   OR 8kHz, mono, 16-bit PCM, 40ms frames")
                    self.logger.info("   Recommendation: Check Asterisk sample rate and frame duration")
                else:
                    self.logger.info(f"⚠️  Unexpected frame size: {frame_size} bytes")
                    self.logger.info("   Recommendation: Analyze Asterisk configuration")
        
        if self.frame_timings:
            avg_interval = sum(self.frame_timings) / len(self.frame_timings)
            self.logger.info(f"Average frame interval: {avg_interval*1000:.1f}ms")
            
            if 15 <= avg_interval*1000 <= 25:
                self.logger.info("✓ Frame timing is appropriate for 20ms frames")
            elif 35 <= avg_interval*1000 <= 45:
                self.logger.info("✓ Frame timing is appropriate for 40ms frames")
            else:
                self.logger.info(f"⚠️  Unexpected frame timing: {avg_interval*1000:.1f}ms")
        
        self.logger.info(f"Total frames analyzed: {frame_count}")
        self.logger.info("="*50)
        
        # Continue normal echo operation
        self.logger.info("Switching to normal echo mode...")
        while call.connected:
            try:
                audio_data = call.read()
                call.write(audio_data)
                time.sleep(0.001)
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the analyzer server"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Analyzer stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Audio Format Diagnostic Tool")
    print("============================")
    print("This tool will analyze incoming audio from Asterisk to determine:")
    print("- Sample rate (8kHz, 16kHz, etc.)")
    print("- Channel count (mono/stereo)")
    print("- Frame duration (20ms, 40ms, etc.)")
    print("- Audio format (PCM, ULAW, etc.)")
    print("- Frame timing consistency")
    print("\nConnect your Asterisk AudioSocket to this server and make a call.")
    print("The tool will analyze the first 50 frames and provide recommendations.\n")
    
    analyzer = AudioFormatAnalyzer()
    analyzer.start()


if __name__ == "__main__":
    main() 
