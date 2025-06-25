#!/usr/bin/env python3
"""
Threaded Voice Buffer Test
Records voice during speech and plays it back during silence.
Uses separate threads for input and output to prevent blocking.
"""

import time
import numpy as np
import queue
from threading import Thread, Lock

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class ThreadedVoiceBufferTest:
    """Threaded voice buffer test"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Configure for 8kHz telephony standard
        self.sample_rate = 8000
        self.channels = 1  # Mono
        self.frame_duration = 0.02  # 20ms frames
        
        # Calculate frame size for 8kHz, mono, 16-bit PCM
        self.frame_size = int(self.sample_rate * self.channels * 2 * self.frame_duration)
        
        self.logger = ColouredLogger("threaded_voice")
        self.logger.info(f"Threaded voice buffer test started on {host}:{port}")
        self.logger.info(f"Audio config: {self.sample_rate}Hz, {self.channels} channel(s), 16-bit PCM")
        self.logger.info(f"Frame size: {self.frame_size} bytes ({self.frame_duration*1000:.0f}ms)")
        
        # Voice activity detection parameters
        self.silence_threshold = 100  # Lower threshold for better detection
        self.speech_frames = 0  # Count consecutive speech frames
        self.silence_frames = 0  # Count consecutive silence frames
        self.min_speech_frames = 3  # Minimum speech frames to start recording
        self.min_silence_frames = 15  # Minimum silence frames to trigger playback
        
        # Thread-safe state
        self.lock = Lock()
        self.voice_buffer = []
        self.is_recording = False
        self.has_prompted = False
        self.should_play_prompt = False
        self.should_play_back = False
        self.connected = False
        
        # Audio queues
        self.output_queue = queue.Queue()
        
    def generate_prompt_tone(self, frequency=1000, duration=0.5, volume=0.3):
        """Generate a prompt tone"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)
        tone = np.sin(2 * np.pi * frequency * t) * volume
        tone = (tone * 32767).astype(np.int16)
        return tone.tobytes()
    
    def detect_voice_activity(self, audio_data):
        """Detect if audio contains speech or silence"""
        # Convert bytes to 16-bit integers
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate RMS (root mean square) amplitude
        rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
        
        return rms > self.silence_threshold
    
    def input_thread(self, call):
        """Handle incoming audio in separate thread"""
        frame_count = 0
        
        while self.connected:
            try:
                # Read incoming audio
                audio_data = call.read()
                frame_count += 1
                
                # Detect voice activity
                has_speech = self.detect_voice_activity(audio_data)
                
                # Log amplitude for debugging
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                
                with self.lock:
                    if has_speech:
                        self.speech_frames += 1
                        self.silence_frames = 0
                        
                        # Start recording after minimum speech frames
                        if self.speech_frames >= self.min_speech_frames:
                            if not self.is_recording:
                                self.is_recording = True
                                self.logger.info(f"🎤 Recording started! (RMS: {rms:.0f})")
                            
                            # Add to voice buffer
                            self.voice_buffer.append(audio_data)
                            
                            # Log recording progress
                            if len(self.voice_buffer) % 25 == 0:
                                duration = len(self.voice_buffer) * self.frame_duration
                                self.logger.info(f"Recording: {duration:.1f}s ({len(self.voice_buffer)} frames)")
                    
                    else:
                        self.silence_frames += 1
                        self.speech_frames = 0
                        
                        # Prompt to speak if we haven't prompted yet and have been silent
                        if not self.has_prompted and self.silence_frames >= 50:  # 1 second of silence
                            self.logger.info("🔊 Queueing prompt tone - please speak now!")
                            self.should_play_prompt = True
                            self.has_prompted = True
                        
                        # Stop recording and start playback after minimum silence
                        if self.silence_frames >= self.min_silence_frames:
                            if self.is_recording and self.voice_buffer:
                                self.is_recording = False
                                duration = len(self.voice_buffer) * self.frame_duration
                                self.logger.info(f"🔊 Queueing playback of {duration:.1f}s of recorded voice...")
                                self.should_play_back = True
                
                # Log status every 50 frames
                if frame_count % 50 == 0:
                    with self.lock:
                        if self.is_recording:
                            duration = len(self.voice_buffer) * self.frame_duration
                            self.logger.info(f"Frame {frame_count}: Recording ({duration:.1f}s, RMS: {rms:.0f})")
                        elif self.silence_frames < self.min_silence_frames:
                            self.logger.info(f"Frame {frame_count}: Silence ({self.silence_frames}/{self.min_silence_frames}, RMS: {rms:.0f})")
                        else:
                            self.logger.info(f"Frame {frame_count}: Waiting for speech (RMS: {rms:.0f})")
                
            except Exception as e:
                self.logger.error(f"Input thread error: {e}")
                break
        
        self.logger.info("Input thread ended")
    
    def output_thread(self, call):
        """Handle outgoing audio in separate thread"""
        while self.connected:
            try:
                # Check for prompt tone
                with self.lock:
                    if self.should_play_prompt:
                        self.should_play_prompt = False
                        self.logger.info("🔊 Playing prompt tone...")
                        prompt_tone = self.generate_prompt_tone()
                        call.write(prompt_tone)
                        self.logger.info("✅ Prompt tone sent")
                    
                    # Check for playback
                    if self.should_play_back:
                        self.should_play_back = False
                        duration = len(self.voice_buffer) * self.frame_duration
                        self.logger.info(f"🔊 Playing back {duration:.1f}s of recorded voice...")
                        
                        # Play back the recorded voice
                        for i, recorded_frame in enumerate(self.voice_buffer):
                            call.write(recorded_frame)
                            
                            # Log playback progress
                            if i % 25 == 0:
                                progress = (i / len(self.voice_buffer)) * 100
                                self.logger.info(f"Playback: {progress:.0f}% complete")
                        
                        self.logger.info("✅ Playback complete - speak again to record more")
                        
                        # Clear buffer for next recording
                        self.voice_buffer.clear()
                        self.has_prompted = False  # Reset for next cycle
                
                # Small delay to prevent busy waiting
                time.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Output thread error: {e}")
                break
        
        self.logger.info("Output thread ended")
    
    def handle_connection(self, call):
        """Handle connection with threaded voice buffer test"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting threaded voice buffer test...")
        
        # Reset state
        with self.lock:
            self.voice_buffer.clear()
            self.is_recording = False
            self.has_prompted = False
            self.should_play_prompt = False
            self.should_play_back = False
            self.connected = True
        
        start_time = time.time()
        
        # Start input and output threads
        input_thread = Thread(target=self.input_thread, args=(call,))
        output_thread = Thread(target=self.output_thread, args=(call,))
        
        input_thread.daemon = True
        output_thread.daemon = True
        
        input_thread.start()
        output_thread.start()
        
        # Wait for threads to complete
        while self.connected and call.connected:
            time.sleep(0.1)
        
        # Clean up
        self.connected = False
        input_thread.join(timeout=1)
        output_thread.join(timeout=1)
        
        # Summary
        total_time = time.time() - start_time
        self.logger.info(f"\nThreaded voice buffer test completed:")
        self.logger.info(f"Total time: {total_time:.1f}s")
    
    def start(self):
        """Start the threaded voice buffer test"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Threaded voice buffer test stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Threaded Voice Buffer Test")
    print("=========================")
    print("This test records your voice and plays it back during silence.")
    print("Uses separate threads for input and output to prevent blocking.")
    print("\nHow it works:")
    print("1. Wait for the prompt tone (1kHz beep)")
    print("2. Speak for at least 60ms to start recording")
    print("3. Continue speaking - your voice is being recorded")
    print("4. Be silent for at least 300ms to trigger playback")
    print("5. Hear your recorded voice played back")
    print("6. Repeat the cycle")
    print("\nThis tests both audio quality and buffering.\n")
    
    test = ThreadedVoiceBufferTest()
    test.start()


if __name__ == "__main__":
    main() 