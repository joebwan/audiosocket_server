#!/usr/bin/env python3
"""
Test Tone Generator
Generates a test tone to verify the audio path is working correctly.
"""

import time
import numpy as np
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class TestToneGenerator:
    """Generates test tones to verify audio path"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Don't set audio format - use defaults
        self.logger = ColouredLogger("tone_generator")
        self.logger.info(f"Test tone generator started on {host}:{port}")
        self.logger.info("This generates test tones to verify audio path")
        
        # Generate test tones
        self.test_tones = self.generate_test_tones()
        
    def generate_test_tones(self):
        """Generate various test tones"""
        tones = {}
        
        # 1kHz sine wave (20ms at 8kHz = 160 samples)
        sample_rate = 8000
        duration = 0.02  # 20ms
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        
        # 1kHz tone
        tone_1khz = np.sin(2 * np.pi * 1000 * t) * 0.5
        tone_1khz = (tone_1khz * 32767).astype(np.int16)
        tones['1khz'] = tone_1khz.tobytes()
        
        # 500Hz tone
        tone_500hz = np.sin(2 * np.pi * 500 * t) * 0.5
        tone_500hz = (tone_500hz * 32767).astype(np.int16)
        tones['500hz'] = tone_500hz.tobytes()
        
        # 2kHz tone
        tone_2khz = np.sin(2 * np.pi * 2000 * t) * 0.5
        tone_2khz = (tone_2khz * 32767).astype(np.int16)
        tones['2khz'] = tone_2khz.tobytes()
        
        # White noise
        noise = np.random.normal(0, 0.3, len(t))
        noise = (noise * 32767).astype(np.int16)
        tones['noise'] = noise.tobytes()
        
        return tones
        
    def handle_connection(self, call):
        """Handle connection with test tone generation"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting test tone generation...")
        self.logger.info("You should hear test tones in this order:")
        self.logger.info("1. 1kHz tone (5 seconds)")
        self.logger.info("2. 500Hz tone (5 seconds)")
        self.logger.info("3. 2kHz tone (5 seconds)")
        self.logger.info("4. White noise (5 seconds)")
        self.logger.info("5. Echo mode (your voice)")
        
        frame_count = 0
        start_time = time.time()
        tone_phase = 0
        tone_start_time = start_time
        
        while call.connected:
            try:
                # Read incoming audio
                audio_data = call.read()
                frame_size = len(audio_data)
                
                frame_count += 1
                current_time = time.time()
                
                # Phase 1-4: Generate test tones
                if tone_phase < 4:
                    elapsed = current_time - tone_start_time
                    
                    if elapsed >= 5:  # Switch tone every 5 seconds
                        tone_phase += 1
                        tone_start_time = current_time
                        self.logger.info(f"Switching to tone phase {tone_phase + 1}")
                    
                    # Generate appropriate test tone
                    if tone_phase == 0:
                        # 1kHz tone
                        tone_name = "1kHz"
                        tone_data = self.test_tones['1khz']
                    elif tone_phase == 1:
                        # 500Hz tone
                        tone_name = "500Hz"
                        tone_data = self.test_tones['500hz']
                    elif tone_phase == 2:
                        # 2kHz tone
                        tone_name = "2kHz"
                        tone_data = self.test_tones['2khz']
                    elif tone_phase == 3:
                        # White noise
                        tone_name = "Noise"
                        tone_data = self.test_tones['noise']
                    
                    # Send test tone
                    call.write(tone_data)
                    
                    # Log every 50 frames
                    if frame_count % 50 == 0:
                        self.logger.info(f"Frame {frame_count}: Sending {tone_name} tone")
                
                # Phase 5: Echo mode
                else:
                    # Echo the incoming audio
                    call.write(audio_data)
                    
                    # Log every 100 frames
                    if frame_count % 100 == 0:
                        self.logger.info(f"Frame {frame_count}: Echo mode - {frame_size} bytes")
                
                # Add small delay
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error in tone generation loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the test tone generator"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Tone generator stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Test Tone Generator")
    print("==================")
    print("This generates test tones to verify the audio path is working.")
    print("\nTest sequence:")
    print("1. 1kHz tone (5 seconds) - Should hear a clear tone")
    print("2. 500Hz tone (5 seconds) - Should hear a lower tone")
    print("3. 2kHz tone (5 seconds) - Should hear a higher tone")
    print("4. White noise (5 seconds) - Should hear static")
    print("5. Echo mode - Your voice should echo back")
    print("\nIf you don't hear the tones, there's an audio routing issue.")
    print("If you hear the tones but not your voice, the echo path has issues.\n")
    
    generator = TestToneGenerator()
    generator.start()


if __name__ == "__main__":
    main() 