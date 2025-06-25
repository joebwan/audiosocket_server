#!/usr/bin/env python3
"""
Fixed 16kHz Echo Server
Properly configured for 16kHz audio from Asterisk to eliminate choppy audio.
"""

import time
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class Fixed16kHzEchoServer:
    """Echo server properly configured for 16kHz Asterisk audio"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # FIXED: Use 16kHz to match Asterisk configuration
        self.audiosocket.prepare_input(inrate=16000, channels=1, ulaw2lin=True)
        self.audiosocket.prepare_output(outrate=16000, channels=1, ulaw2lin=True)
        
        self.logger = ColouredLogger("fixed_16khz_echo")
        self.logger.info(f"Fixed 16kHz echo server started on {host}:{port}")
        self.logger.info("Audio config: 16kHz, mono, 16-bit PCM (matches Asterisk)")
        
        # Frame size for 16kHz: 16000 * 0.02 * 1 * 2 = 640 bytes
        self.expected_frame_size = 640
        
    def handle_connection(self, call):
        """Handle connection with proper 16kHz configuration"""
        self.logger.info(f"New connection from {call.peer_addr}")
        
        frame_count = 0
        start_time = time.time()
        last_log_time = start_time
        
        while call.connected:
            try:
                # Read audio data
                audio_data = call.read()
                frame_size = len(audio_data)
                
                frame_count += 1
                
                # Monitor frame size (should be 640 bytes for 16kHz)
                if frame_size != self.expected_frame_size:
                    self.logger.warning(f"Unexpected frame size: {frame_size} bytes (expected {self.expected_frame_size})")
                else:
                    # Log success occasionally
                    if frame_count % 100 == 0:
                        self.logger.info(f"Frame {frame_count}: {frame_size} bytes ✓")
                
                # Echo audio back
                call.write(audio_data)
                
                # Log statistics every 5 seconds
                current_time = time.time()
                if current_time - last_log_time >= 5:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed
                    self.logger.info(f"Frames: {frame_count}, FPS: {fps:.1f}, "
                                   f"Frame size: {frame_size}, Elapsed: {elapsed:.1f}s")
                    last_log_time = current_time
                
                # Add small delay to prevent overwhelming the system
                time.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the fixed echo server"""
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


def main():
    """Main function"""
    print("Fixed 16kHz Echo Server")
    print("=======================")
    print("This server is configured to match your Asterisk 16kHz audio format.")
    print("This should eliminate the choppy audio you were experiencing.")
    print("\nConfiguration:")
    print("- Sample rate: 16kHz (matches Asterisk)")
    print("- Channels: Mono")
    print("- Format: 16-bit PCM")
    print("- Frame size: 640 bytes (20ms at 16kHz)")
    print("\nConnect your Asterisk AudioSocket and test the audio quality.\n")
    
    server = Fixed16kHzEchoServer()
    server.start()


if __name__ == "__main__":
    main() 