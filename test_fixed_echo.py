#!/usr/bin/env python3
"""
Test Fixed Echo Server
Tests the connection.py fix that eliminates the 64ms blocking delay.
"""

import time
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class TestFixedEchoServer:
    """Simple echo server to test the connection.py fix"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Don't set any audio format - let it use defaults
        self.logger = ColouredLogger("test_fixed_echo")
        self.logger.info(f"Test fixed echo server started on {host}:{port}")
        self.logger.info("Testing the connection.py fix for non-blocking reads")
        
    def handle_connection(self, call):
        """Handle connection and test performance"""
        self.logger.info(f"New connection from {call.peer_addr}")
        
        frame_count = 0
        start_time = time.time()
        last_log_time = start_time
        last_frame_time = start_time
        
        while call.connected:
            try:
                # Measure timing
                current_time = time.time()
                
                # Read audio data (should now be non-blocking)
                audio_data = call.read()
                frame_size = len(audio_data)
                
                frame_count += 1
                
                # Calculate frame interval
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    if interval > 0.1:  # Log if interval is unusually high
                        self.logger.warning(f"High frame interval: {interval*1000:.1f}ms")
                
                last_frame_time = current_time
                
                # Echo audio back
                call.write(audio_data)
                
                # Log statistics every 5 seconds
                if current_time - last_log_time >= 5:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed
                    self.logger.info(f"Frames: {frame_count}, FPS: {fps:.1f}, "
                                   f"Frame size: {frame_size}, Elapsed: {elapsed:.1f}s")
                    last_log_time = current_time
                
                # Add minimal delay
                time.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the test echo server"""
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
    print("Test Fixed Echo Server")
    print("=====================")
    print("This server tests the connection.py fix for non-blocking reads.")
    print("The fix should eliminate the 64ms blocking delay and choppy audio.")
    print("\nExpected improvements:")
    print("- Frame rate should be ~50 FPS (not 15 FPS)")
    print("- Frame intervals should be ~20ms (not 65ms)")
    print("- Audio should be clear without chopping")
    print("\nConnect your Asterisk AudioSocket and test.\n")
    
    server = TestFixedEchoServer()
    server.start()


if __name__ == "__main__":
    main() 