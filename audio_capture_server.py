#!/usr/bin/env python3
"""
Audio Capture Server
Captures real audio from live Asterisk AudioSocket connections and saves to WAV files.
"""

import time
import threading
import wave
import os
from datetime import datetime
from collections import deque
import audioop

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class AudioCaptureServer:
    """Server that captures audio from AudioSocket connections and saves to WAV files"""
    
    def __init__(self, host="0.0.0.0", port=6050, output_dir="captured_audio"):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.output_dir = output_dir
        
        # Audio configuration (8kHz, mono, 16-bit PCM)
        self.sample_rate = 8000
        self.channels = 1
        self.sample_width = 2  # 16-bit = 2 bytes
        
        # Audio buffer for WAV file
        self.audio_buffer = deque()
        self.buffer_lock = threading.Lock()
        
        # Voice activity detection
        self.silence_threshold = 500  # Adjust based on your audio levels
        self.speech_frames = 0
        self.silence_frames = 0
        
        # Statistics
        self.total_frames = 0
        self.audio_frames = 0
        self.silence_frames_count = 0
        
        # Logging
        self.logger = ColouredLogger("audio_capture")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        self.logger.info(f"Audio Capture Server started on {host}:{port}")
        self.logger.info(f"Audio config: {self.sample_rate}Hz, {self.channels} channel(s), {self.sample_width*8}-bit PCM")
        self.logger.info(f"Output directory: {output_dir}")
        self.logger.info(f"Silence threshold: {self.silence_threshold}")
        
    def detect_voice_activity(self, audio_data):
        """Detect if audio frame contains speech or silence"""
        if len(audio_data) < 2:
            return False, 0
        
        # Calculate RMS (Root Mean Square) of the audio frame
        # This gives us a measure of the audio level
        try:
            rms = audioop.rms(audio_data, self.sample_width)
        except:
            # If audioop fails, use a simple calculation
            rms = sum(abs(int.from_bytes(audio_data[i:i+2], 'little', signed=True)) 
                     for i in range(0, len(audio_data)-1, 2)) / (len(audio_data) // 2)
        
        # Determine if this is speech or silence
        is_speech = rms > self.silence_threshold
        
        return is_speech, rms
    
    def save_audio_to_wav(self, call_id):
        """Save buffered audio to WAV file"""
        with self.buffer_lock:
            if not self.audio_buffer:
                self.logger.warning("No audio data to save")
                return None
            
            # Create filename with timestamp and call ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"call_{call_id}_{timestamp}.wav"
            filepath = os.path.join(self.output_dir, filename)
            
            # Convert deque to bytes
            audio_data = b''.join(self.audio_buffer)
            
            # Write WAV file
            with wave.open(filepath, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(self.sample_width)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            
            # Calculate duration
            duration = len(audio_data) / (self.sample_rate * self.channels * self.sample_width)
            
            self.logger.info(f"✅ Saved audio to: {filepath}")
            self.logger.info(f"  Duration: {duration:.2f}s")
            self.logger.info(f"  Size: {len(audio_data)} bytes")
            self.logger.info(f"  Frames: {len(self.audio_buffer)}")
            self.logger.info(f"  Speech frames: {self.speech_frames}")
            self.logger.info(f"  Silence frames: {self.silence_frames_count}")
            
            return filepath
    
    def handle_connection(self, call):
        """Handle AudioSocket connection and capture audio"""
        call_id = call.uuid if hasattr(call, 'uuid') and call.uuid else "unknown"
        self.logger.info(f"New connection from {call.peer_addr} (Call ID: {call_id})")
        self.logger.info("Starting audio capture...")
        
        # Reset statistics for this connection
        self.total_frames = 0
        self.audio_frames = 0
        self.silence_frames_count = 0
        self.speech_frames = 0
        
        # Clear audio buffer
        with self.buffer_lock:
            self.audio_buffer.clear()
        
        start_time = time.time()
        last_log_time = start_time
        
        try:
            while call.connected:
                # Read incoming audio
                audio_data = call.read()
                self.total_frames += 1
                
                # Detect voice activity
                is_speech, rms = self.detect_voice_activity(audio_data)
                
                if is_speech:
                    self.speech_frames += 1
                    self.audio_frames += 1
                    # Add audio frame to buffer
                    with self.buffer_lock:
                        self.audio_buffer.append(audio_data)
                else:
                    self.silence_frames_count += 1
                    # Also buffer silence frames for complete audio
                    with self.buffer_lock:
                        self.audio_buffer.append(audio_data)
                
                # Log progress every 5 seconds
                current_time = time.time()
                if current_time - last_log_time >= 5.0:
                    elapsed = current_time - start_time
                    fps = self.total_frames / elapsed if elapsed > 0 else 0
                    
                    self.logger.info(f"Capture progress: {self.total_frames} frames, "
                                   f"{self.speech_frames} speech, {self.silence_frames_count} silence, "
                                   f"FPS: {fps:.1f}, RMS: {rms:.1f}")
                    last_log_time = current_time
                
                # Small delay to prevent overwhelming
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during capture: {e}")
        
        # Save audio when connection ends
        self.logger.info("Connection ended, saving audio...")
        wav_file = self.save_audio_to_wav(call_id)
        
        # Final statistics
        total_time = time.time() - start_time
        self.logger.info("\n" + "="*50)
        self.logger.info("CAPTURE SUMMARY")
        self.logger.info("="*50)
        self.logger.info(f"Total frames: {self.total_frames}")
        self.logger.info(f"Speech frames: {self.speech_frames}")
        self.logger.info(f"Silence frames: {self.silence_frames_count}")
        self.logger.info(f"Total time: {total_time:.2f}s")
        self.logger.info(f"Average FPS: {self.total_frames/total_time:.1f}")
        
        if self.speech_frames > 0:
            speech_percentage = (self.speech_frames / self.total_frames) * 100
            self.logger.info(f"Speech percentage: {speech_percentage:.1f}%")
            self.logger.info("✅ Audio captured successfully!")
        else:
            self.logger.warning("⚠️  No speech detected - only silence captured")
        
        self.logger.info("="*50)
        
        return wav_file
    
    def start(self):
        """Start the audio capture server"""
        self.logger.info("Audio Capture Server is running...")
        self.logger.info("Waiting for Asterisk AudioSocket connections...")
        self.logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                # Accept connections
                call = self.audiosocket.listen()
                
                # Handle each connection in a separate thread
                thread = threading.Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
                
        except KeyboardInterrupt:
            self.logger.info("Audio Capture Server stopped by user")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Audio Capture Server")
    print("===================")
    print("This server captures real audio from live Asterisk AudioSocket connections.")
    print("\nFeatures:")
    print("- Captures audio from live Asterisk connections")
    print("- Detects speech vs silence")
    print("- Saves audio to WAV files (8kHz, mono, 16-bit PCM)")
    print("- Provides detailed statistics")
    print("\nUsage:")
    print("1. Start this server")
    print("2. Configure Asterisk to connect to this server")
    print("3. Make a call through Asterisk")
    print("4. Audio will be saved to 'captured_audio/' directory")
    print("5. Play the WAV files to verify audio quality")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = AudioCaptureServer()
    server.start()


if __name__ == "__main__":
    main() 