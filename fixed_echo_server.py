#!/usr/bin/env python3
"""
Fixed Echo Server
Uses the corrected connection.py with non-blocking reads to eliminate choppy audio.
"""

import time
from threading import Thread
import sys
import os

# Add the current directory to the path so we can import our fixed connection
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the fixed connection module
from connection_fixed import Connection
from audiosocket import Audiosocket
from mylogging import ColouredLogger


class FixedEchoServer:
    """Echo server using the fixed connection with non-blocking reads"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        # Create audiosocket but we'll override the connection creation
        self.audiosocket = Audiosocket((host, port))
        
        # Override the connection creation to use our fixed version
        self.audiosocket._create_connection = self._create_fixed_connection
        
        self.logger = ColouredLogger("fixed_echo")
        self.logger.info(f"Fixed echo server started on {host}:{port}")
        self.logger.info("Using non-blocking reads to eliminate choppy audio")
        
    def _create_fixed_connection(self, conn, peer_addr, user_resample, asterisk_resample):
        """Create a connection using our fixed connection class"""
        return Connection(conn, peer_addr, user_resample, asterisk_resample)
        
    def handle_connection(self, call):
        """Handle connection with fixed non-blocking reads"""
        self.logger.info(f"New connection from {call.peer_addr}")
        
        frame_count = 0
        start_time = time.time()
        last_log_time = start_time
        
        while call.connected:
            try:
                # Read audio data (now non-blocking)
                audio_data = call.read()
                frame_size = len(audio_data)
                
                frame_count += 1
                
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
                
                # Add minimal delay to prevent overwhelming the system
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
    print("Fixed Echo Server")
    print("================")
    print("This server uses the corrected connection.py with non-blocking reads.")
    print("This should eliminate the choppy audio caused by 64ms blocking delays.")
    print("\nKey fix:")
    print("- Changed from blocking read (timeout=0.2) to non-blocking read (get_nowait())")
    print("- Eliminates 64ms delays that were causing choppy audio")
    print("- Maintains real-time audio performance")
    print("\nConnect your Asterisk AudioSocket and test the audio quality.\n")
    
    server = FixedEchoServer()
    server.start()


if __name__ == "__main__":
    main() 