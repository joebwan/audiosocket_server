#!/usr/bin/env python3
"""
Simple Pass-Through Echo Server
Minimal processing - just echoes exactly what Asterisk sends.
"""

import time
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class SimplePassthroughEcho:
    """Simple pass-through echo server with minimal processing"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("passthrough")
        
        self.logger.info(f"Simple Pass-Through Echo Server started on {host}:{port}")
        self.logger.info("This server does minimal processing:")
        self.logger.info("- Accepts any frame size from Asterisk")
        self.logger.info("- No audio format conversion")
        self.logger.info("- No resampling or processing")
        self.logger.info("- Pure pass-through echo")
        self.logger.info("")
        
    def handle_connection(self, call):
        """Handle connection with pure pass-through"""
        self.logger.info("=" * 50)
        self.logger.info("SIMPLE PASS-THROUGH ECHO - NEW CONNECTION")
        self.logger.info("=" * 50)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        total_bytes = 0
        start_time = time.time()
        
        try:
            # Simple pass-through loop
            while call.connected:
                # Read incoming audio (raw from Asterisk)
                audio_data = call.read()
                
                # Skip empty frames
                if len(audio_data) == 0:
                    time.sleep(0.001)
                    continue
                
                frame_count += 1
                total_bytes += len(audio_data)
                
                # Log first 10 frames
                if frame_count <= 10:
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes")
                
                # Echo immediately without any modification
                call.write(audio_data)
                
                # Log every 100 frames
                if frame_count % 100 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, FPS: {fps:.1f}")
                
                # Minimal delay
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during pass-through: {e}")
        
        # Final statistics
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 50)
        self.logger.info("PASS-THROUGH SESSION SUMMARY")
        self.logger.info("=" * 50)
        
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total bytes: {total_bytes}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            avg_fps = frame_count / total_time if total_time > 0 else 0
            avg_frame_size = total_bytes / frame_count if frame_count > 0 else 0
            
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Average frame size: {avg_frame_size:.1f} bytes")
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
        """Start the pass-through server"""
        self.logger.info("Simple Pass-Through Echo Server is running...")
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
            self.logger.info("Simple Pass-Through Echo Server stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Simple Pass-Through Echo Server")
    print("===============================")
    print("This server does minimal processing and just echoes what Asterisk sends.")
    print("\nKey features:")
    print("- Accepts any frame size from Asterisk")
    print("- No audio format conversion")
    print("- No resampling or processing")
    print("- Pure pass-through echo")
    print("\nThis should give us the cleanest possible audio.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = SimplePassthroughEcho()
    server.start()


if __name__ == "__main__":
    main() 