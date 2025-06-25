#!/usr/bin/env python3
"""
Adaptive Echo Server
Handles variable-size audio frames from Asterisk without padding or truncating.
"""

import time
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class AdaptiveEchoServer:
    """Echo server that adapts to variable frame sizes"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("adaptive_echo")
        
        self.logger.info(f"Adaptive Echo Server started on {host}:{port}")
        self.logger.info("This server adapts to variable frame sizes from Asterisk")
        self.logger.info("Features:")
        self.logger.info("- Handles variable frame sizes (160, 320, 640+ bytes)")
        self.logger.info("- No padding or truncating of audio")
        self.logger.info("- Real-time echo with correct timing")
        self.logger.info("- Frame size monitoring and logging")
        self.logger.info("")
        
    def handle_connection(self, call):
        """Handle AudioSocket connection with adaptive frame handling"""
        self.logger.info("=" * 60)
        self.logger.info("ADAPTIVE ECHO SERVER - NEW CONNECTION")
        self.logger.info("=" * 60)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        total_bytes = 0
        frame_sizes = []
        start_time = time.time()
        last_frame_time = start_time
        
        # Frame timing analysis
        frame_intervals = []
        
        # Frame size tracking
        size_distribution = {}
        
        try:
            # Echo loop
            while call.connected:
                # Read incoming audio (this gets the raw frame from the connection)
                audio_data = call.read()
                current_time = time.time()
                
                # Skip empty frames
                if len(audio_data) == 0:
                    time.sleep(0.001)
                    continue
                
                frame_count += 1
                total_bytes += len(audio_data)
                frame_sizes.append(len(audio_data))
                
                # Track frame size distribution
                size = len(audio_data)
                size_distribution[size] = size_distribution.get(size, 0) + 1
                
                # Calculate frame interval
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    frame_intervals.append(interval)
                last_frame_time = current_time
                
                # Log first 10 frames with size info
                if frame_count <= 10:
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes")
                
                # Echo immediately without any modification
                call.write(audio_data)
                
                # Log every 100 frames with statistics
                if frame_count % 100 == 0:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    avg_interval = sum(frame_intervals[-10:]) / min(10, len(frame_intervals)) if frame_intervals else 0
                    
                    # Show frame size distribution
                    size_info = ", ".join([f"{size}b: {count}" for size, count in sorted(size_distribution.items())[-3:]])
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, "
                                   f"FPS: {fps:.1f}, Interval: {avg_interval*1000:.1f}ms")
                    self.logger.info(f"  Frame sizes: {size_info}")
                
                # Small delay to prevent overwhelming
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during echo: {e}")
        
        # Final statistics
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("ADAPTIVE ECHO SESSION SUMMARY")
        self.logger.info("=" * 60)
        
        self.logger.info(f"Total frames processed: {frame_count}")
        self.logger.info(f"Total bytes: {total_bytes}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            # Frame rate analysis
            avg_fps = frame_count / total_time if total_time > 0 else 0
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Expected FPS: 50.0 (20ms intervals)")
            
            # Frame size analysis
            if frame_sizes:
                avg_size = sum(frame_sizes) / len(frame_sizes)
                min_size = min(frame_sizes)
                max_size = max(frame_sizes)
                size_variation = max_size - min_size
                
                self.logger.info(f"Frame size analysis:")
                self.logger.info(f"  Average: {avg_size:.1f} bytes")
                self.logger.info(f"  Range: {min_size} - {max_size} bytes")
                self.logger.info(f"  Variation: {size_variation} bytes")
                
                # Show size distribution
                self.logger.info(f"  Size distribution:")
                for size, count in sorted(size_distribution.items()):
                    percentage = (count / frame_count) * 100
                    self.logger.info(f"    {size} bytes: {count} frames ({percentage:.1f}%)")
                
                # Check for variable frame sizes
                if len(size_distribution) > 1:
                    self.logger.info("✅ Variable frame sizes detected and handled")
                else:
                    self.logger.info("ℹ️  Fixed frame size detected")
            
            # Frame timing analysis
            if frame_intervals:
                avg_interval = sum(frame_intervals) / len(frame_intervals)
                min_interval = min(frame_intervals)
                max_interval = max(frame_intervals)
                
                self.logger.info(f"Frame timing analysis:")
                self.logger.info(f"  Average interval: {avg_interval*1000:.1f}ms")
                self.logger.info(f"  Range: {min_interval*1000:.1f} - {max_interval*1000:.1f}ms")
                
                # Check for consistent timing
                expected_interval = 0.02  # 20ms
                timing_variation = abs(avg_interval - expected_interval)
                if timing_variation < 0.005:
                    self.logger.info("✅ Frame timing is consistent")
                else:
                    self.logger.warning(f"⚠️  Frame timing variation: {timing_variation*1000:.1f}ms from expected")
            
            # Quality assessment
            speed_ratio = avg_fps / 50.0 if avg_fps > 0 else 0
            if abs(speed_ratio - 1.0) < 0.1:
                self.logger.info("✅ Frame rate is correct")
            else:
                self.logger.warning(f"⚠️  Frame rate is {speed_ratio:.1f}x expected")
        
        self.logger.info("=" * 60)
        self.logger.info("")
    
    def start(self):
        """Start the adaptive echo server"""
        self.logger.info("Adaptive Echo Server is running...")
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
            self.logger.info("Adaptive Echo Server stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Adaptive Echo Server")
    print("===================")
    print("This server adapts to variable frame sizes from Asterisk.")
    print("\nKey improvements:")
    print("- Handles 160, 320, 640+ byte frames")
    print("- No audio padding or truncating")
    print("- Real-time echo with correct timing")
    print("- Frame size monitoring and logging")
    print("\nThis should fix the choppy/faint audio issues.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = AdaptiveEchoServer()
    server.start()


if __name__ == "__main__":
    main() 
