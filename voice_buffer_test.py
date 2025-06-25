#!/usr/bin/env python3
"""
Voice Buffer Test
Records voice during speech and plays it back during silence.
"""

import time
import numpy as np
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class VoiceBufferTest:
    """Voice buffer test"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Configure for 8kHz telephony standard
        self.sample_rate = 8000
        self.channels = 1  # Mono
        self.frame_duration = 0.02  # 20ms frames
        
        # Calculate frame size for 8kHz, mono, 16-bit PCM
        self.frame_size = int(self.sample_rate * self.channels * 2 * self.frame_duration)
        
        self.logger = ColouredLogger("voice_buffer")
        self.logger.info(f"Voice buffer test started on {host}:{port}")
        self.logger.info(f"Audio config: {self.sample_rate}Hz, {self.channels} channel(s), 16-bit PCM")
        self.logger.info(f"Frame size: {self.frame_size} bytes ({self.frame_duration*1000:.0f}ms)")
        
        # Voice activity detection parameters
        self.silence_threshold = 500  # Amplitude threshold for silence
        self.speech_frames = 0  # Count consecutive speech frames
        self.silence_frames = 0  # Count consecutive silence frames
        self.min_speech_frames = 5  # Minimum speech frames to start recording
        self.min_silence_frames = 10  # Minimum silence frames to trigger playback
        
        # Buffer for recorded voice
        self.voice_buffer = []
        self.is_recording = False
        
    def detect_voice_activity(self, audio_data):
        """Detect if audio contains speech or silence"""
        # Convert bytes to 16-bit integers
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate RMS (root mean square) amplitude
        rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
        
        return rms > self.silence_threshold
    
    def handle_connection(self, call):
        """Handle connection with voice buffer test"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting voice buffer test...")
        self.logger.info("Speak to record your voice, then be silent to hear playback")
        
        frame_count = 0
        start_time = time.time()
        
        while call.connected:
            try:
                # Read incoming audio
                audio_data = call.read()
                frame_count += 1
                
                # Detect voice activity
                has_speech = self.detect_voice_activity(audio_data)
                
                if has_speech:
                    self.speech_frames += 1
                    self.silence_frames = 0
                    
                    # Start recording after minimum speech frames
                    if self.speech_frames >= self.min_speech_frames:
                        if not self.is_recording:
                            self.is_recording = True
                            self.logger.info("🎤 Recording started...")
                        
                        # Add to voice buffer
                        self.voice_buffer.append(audio_data)
                        
                        # Log recording progress
                        if len(self.voice_buffer) % 50 == 0:
                            duration = len(self.voice_buffer) * self.frame_duration
                            self.logger.info(f"Recording: {duration:.1f}s ({len(self.voice_buffer)} frames)")
                
                else:
                    self.silence_frames += 1
                    self.speech_frames = 0
                    
                    # Stop recording and start playback after minimum silence
                    if self.silence_frames >= self.min_silence_frames:
                        if self.is_recording and self.voice_buffer:
                            self.is_recording = False
                            duration = len(self.voice_buffer) * self.frame_duration
                            self.logger.info(f"🔊 Playing back {duration:.1f}s of recorded voice...")
                            
                            # Play back the recorded voice
                            for i, recorded_frame in enumerate(self.voice_buffer):
                                call.write(recorded_frame)
                                
                                # Log playback progress
                                if i % 50 == 0:
                                    progress = (i / len(self.voice_buffer)) * 100
                                    self.logger.info(f"Playback: {progress:.0f}% complete")
                            
                            self.logger.info("✅ Playback complete")
                            
                            # Clear buffer for next recording
                            self.voice_buffer.clear()
                
                # Log status every 100 frames
                if frame_count % 100 == 0:
                    if self.is_recording:
                        duration = len(self.voice_buffer) * self.frame_duration
                        self.logger.info(f"Frame {frame_count}: Recording ({duration:.1f}s)")
                    elif self.silence_frames < self.min_silence_frames:
                        self.logger.info(f"Frame {frame_count}: Silence ({self.silence_frames}/{self.min_silence_frames})")
                    else:
                        self.logger.info(f"Frame {frame_count}: Waiting for speech")
                
                # Small delay to prevent overwhelming
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error: {e}")
                break
        
        # Summary
        total_time = time.time() - start_time
        self.logger.info(f"\nVoice buffer test completed:")
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total time: {total_time:.1f}s")
    
    def start(self):
        """Start the voice buffer test"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Voice buffer test stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Voice Buffer Test")
    print("================")
    print("This test records your voice and plays it back during silence.")
    print("\nHow it works:")
    print("1. Speak for at least 100ms to start recording")
    print("2. Continue speaking - your voice is being recorded")
    print("3. Be silent for at least 200ms to trigger playback")
    print("4. Hear your recorded voice played back")
    print("5. Repeat the cycle")
    print("\nThis tests both audio quality and buffering.\n")
    
    test = VoiceBufferTest()
    test.start()


if __name__ == "__main__":
    main() 