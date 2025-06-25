#!/usr/bin/env python3
"""
Fixed Echo Server
Simple echo server using the corrected AudioSocket implementation with proper variable-length frame parsing.
"""

import time
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class FixedEchoServer:
    """Echo server with proper AudioSocket frame parsing"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("fixed_echo")
        
        self.logger.info(f"Fixed Echo Server started on {host}:{port}")
        self.logger.info("This server uses proper variable-length frame parsing")
        self.logger.info("Features:")
        self.logger.info("- Correct AudioSocket protocol implementation")
        self.logger.info("- Variable-length frame parsing")
        self.logger.info("- Proper frame boundary detection")
        self.logger.info("- Real-time echo with correct timing")
        self.logger.info("")
        
    def handle_connection(self, call):
        """Handle AudioSocket connection with proper echo"""
        self.logger.info("=" * 50)
        self.logger.info("FIXED ECHO SERVER - NEW CONNECTION")
        self.logger.info("=" * 50)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        start_time = time.time()
        
        try:
            # Echo loop
            while call.connected:
                # Read incoming audio
                audio_data = call.read()
                frame_count += 1
                
                # Log first few frames
                if frame_count <= 5:
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes")
                
                # Echo immediately
                call.write(audio_data)
                
                # Log every 100 frames
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Frame {frame_count}: FPS={fps:.1f}")
                
                # Small delay to prevent overwhelming
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during echo: {e}")
        
        # Final statistics
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 50)
        self.logger.info("ECHO SESSION SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Total frames processed: {frame_count}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            avg_fps = frame_count / total_time if total_time > 0 else 0
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Expected FPS: 50.0 (20ms intervals)")
            
            # Check frame rate
            speed_ratio = avg_fps / 50.0 if avg_fps > 0 else 0
            if abs(speed_ratio - 1.0) < 0.1:
                self.logger.info("✅ Frame rate is correct")
            else:
                self.logger.warning(f"⚠️  Frame rate is {speed_ratio:.1f}x expected")
        
        self.logger.info("=" * 50)
        self.logger.info("")
    
    def start(self):
        """Start the fixed echo server"""
        self.logger.info("Fixed Echo Server is running...")
        self.logger.info("Waiting for AudioSocket connections...")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("")
        
        connection_count = 0
        
        try:
            while True:
                # Accept connections
                call = self.audiosocket.listen()
                connection_count += 1
                
                self.logger.info(f"Connection #{connection_count} accepted")
                
                # Handle connection
                self.handle_connection(call)
                
        except KeyboardInterrupt:
            self.logger.info("")
            self.logger.info("Fixed Echo Server stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Fixed Echo Server")
    print("================")
    print("This server uses the corrected AudioSocket implementation.")
    print("\nKey improvements:")
    print("- Proper variable-length frame parsing")
    print("- Correct frame boundary detection")
    print("- Spec-compliant protocol handling")
    print("- Real-time echo with correct timing")
    print("\nThis should fix the 14x speed issue and provide clean audio.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = FixedEchoServer()
    server.start()


if __name__ == "__main__":
    main() 