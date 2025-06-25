#!/usr/bin/env python3
"""
Simple Pass-Through Echo Server
Echoes audio exactly as received without any processing or format conversion.
This eliminates all format-related audio issues.
"""

import time
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class SimplePassthroughEchoServer:
    """Simple echo server that passes through audio without processing"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # IMPORTANT: Don't set any audio format - let it use defaults
        # This allows the server to handle any format without conversion
        
        self.logger = ColouredLogger("passthrough_echo")
        self.logger.info(f"Simple pass-through echo server started on {host}:{port}")
        self.logger.info("This server echoes audio exactly as received - no processing")
        self.logger.info("This should eliminate ALL format-related audio issues")
        
    def handle_connection(self, call):
        """Handle connection with simple pass-through"""
        self.logger.info(f"New connection from {call.peer_addr}")
        
        frame_count = 0
        start_time = time.time()
        last_log_time = start_time
        
        while call.connected:
            try:
                # Read audio data exactly as received
                audio_data = call.read()
                frame_size = len(audio_data)
                
                frame_count += 1
                
                # Echo audio back exactly as received (no processing)
                call.write(audio_data)
                
                # Log statistics every 5 seconds
                current_time = time.time()
                if current_time - last_log_time >= 5:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed
                    self.logger.info(f"Frames: {frame_count}, FPS: {fps:.1f}, "
                                   f"Frame size: {frame_size}, Elapsed: {elapsed:.1f}s")
                    last_log_time = current_time
                
                # Minimal delay to prevent overwhelming
                time.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the simple pass-through echo server"""
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
    print("Simple Pass-Through Echo Server")
    print("===============================")
    print("This server echoes audio exactly as received.")
    print("No format conversion, no processing - just pure echo.")
    print("\nBenefits:")
    print("- Works with ANY audio format")
    print("- No format conversion issues")
    print("- No sample rate problems")
    print("- No frame size mismatches")
    print("- Maximum compatibility")
    print("\nConnect your Asterisk AudioSocket and test.\n")
    
    server = SimplePassthroughEchoServer()
    server.start()


if __name__ == "__main__":
    main() 