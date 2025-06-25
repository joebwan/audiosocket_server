#!/usr/bin/env python3
"""
16kHz Test Tone Generator
Generates tones at 16kHz to match Asterisk audio format.
This should eliminate choppy audio and delays.
"""

import time
import numpy as np
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class TestToneGenerator16kHz:
    """16kHz test tone generator"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Configure for 16kHz to match Asterisk
        self.sample_rate = 16000
        self.channels = 1  # Mono
        self.frame_duration = 0.02  # 20ms frames
        
        # Calculate frame size for 16kHz, mono, 16-bit PCM
        self.frame_size = int(self.sample_rate * self.channels * 2 * self.frame_duration)
        
        self.logger = ColouredLogger("tone_16khz")
        self.logger.info(f"16kHz tone generator started on {host}:{port}")
        self.logger.info(f"Audio config: {self.sample_rate}Hz, {self.channels} channel(s), 16-bit PCM")
        self.logger.info(f"Frame size: {self.frame_size} bytes ({self.frame_duration*1000:.0f}ms)")
        
    def generate_tone(self, frequency, duration, volume=0.3):
        """Generate a tone at the specified frequency"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)
        tone = np.sin(2 * np.pi * frequency * t) * volume
        tone = (tone * 32767).astype(np.int16)
        return tone.tobytes()
    
    def handle_connection(self, call):
        """Handle connection with 16kHz tone generation"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting 16kHz tone test...")
        
        frame_count = 0
        start_time = time.time()
        last_frame_time = start_time
        
        # Tone sequence
        tones = [
            (1000, 3, "1kHz tone"),   # 1kHz for 3 seconds
            (2000, 3, "2kHz tone"),   # 2kHz for 3 seconds
            (500, 3, "500Hz tone"),   # 500Hz for 3 seconds
            (1500, 3, "1.5kHz tone"), # 1.5kHz for 3 seconds
        ]
        
        current_tone = 0
        tone_start_time = time.time()
        
        while call.connected:
            try:
                # Read incoming audio (to maintain connection)
                audio_data = call.read()
                current_time = time.time()
                
                frame_count += 1
                
                # Track timing
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    if interval > 0.05:  # Log slow frames
                        self.logger.warning(f"Slow frame: {interval*1000:.1f}ms")
                last_frame_time = current_time
                
                # Generate and send tone
                if current_tone < len(tones):
                    elapsed = current_time - tone_start_time
                    frequency, duration, description = tones[current_tone]
                    
                    if elapsed >= duration:
                        current_tone += 1
                        tone_start_time = current_time
                        if current_tone < len(tones):
                            self.logger.info(f"Switching to: {tones[current_tone][2]}")
                        else:
                            self.logger.info("Switching to echo mode")
                    
                    # Generate tone matching frame size
                    tone_data = self.generate_tone(frequency, self.frame_duration, 0.3)
                    
                    # Ensure frame size matches
                    if len(tone_data) != self.frame_size:
                        # Pad or truncate to match frame size
                        if len(tone_data) < self.frame_size:
                            # Pad with silence
                            padding = b'\x00' * (self.frame_size - len(tone_data))
                            tone_data += padding
                        else:
                            # Truncate
                            tone_data = tone_data[:self.frame_size]
                    
                    # Send the tone
                    call.write(tone_data)
                    
                    # Log every 50 frames
                    if frame_count % 50 == 0:
                        self.logger.info(f"Frame {frame_count}: Sending {len(tone_data)} byte {description}")
                
                # Echo mode after tones
                else:
                    # Echo the incoming audio
                    call.write(audio_data)
                    
                    # Log every 100 frames
                    if frame_count % 100 == 0:
                        self.logger.info(f"Frame {frame_count}: Echo mode - {len(audio_data)} bytes")
                
                # Small delay to prevent overwhelming
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error: {e}")
                break
        
        # Performance summary
        total_time = time.time() - start_time
        fps = frame_count / total_time if total_time > 0 else 0
        
        self.logger.info("\n" + "="*50)
        self.logger.info("16kHz TONE TEST COMPLETE")
        self.logger.info("="*50)
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total time: {total_time:.1f}s")
        self.logger.info(f"Average FPS: {fps:.1f}")
        self.logger.info(f"Expected FPS: {1/self.frame_duration:.1f}")
        
        if fps > 40:
            self.logger.info("✅ Good performance - tones should be smooth")
        else:
            self.logger.info("⚠️  Low performance - may cause choppy audio")
        
        self.logger.info("="*50)
    
    def start(self):
        """Start the 16kHz tone generator"""
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
    print("16kHz Test Tone Generator")
    print("========================")
    print("This generator creates tones at 16kHz to match Asterisk format.")
    print("\nWhat you should hear:")
    print("1. 1kHz tone for 3 seconds")
    print("2. 2kHz tone for 3 seconds") 
    print("3. 500Hz tone for 3 seconds")
    print("4. 1.5kHz tone for 3 seconds")
    print("5. Echo of your voice")
    print("\nIf tones are smooth and clear, the format is correct.\n")
    
    generator = TestToneGenerator16kHz()
    generator.start()


if __name__ == "__main__":
    main() 