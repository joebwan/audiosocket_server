#!/usr/bin/env python3
"""
Instrumented Server
Accepts AudioSocket connections, logs detailed information for 3 seconds, then hangs up.
Assumes the Asterisk AudioSocket connection is correct and focuses on understanding the protocol.
"""

import time
from audiosocket import Audiosocket
from mylogging import ColouredLogger


class InstrumentedServer:
    """Server with detailed instrumentation for AudioSocket analysis"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("instrumented")
        
        self.logger.info(f"Instrumented Server started on {host}:{port}")
        self.logger.info("This server will:")
        self.logger.info("1. Accept AudioSocket connections")
        self.logger.info("2. Log detailed frame information for 3 seconds")
        self.logger.info("3. Send hangup message after 3 seconds")
        self.logger.info("4. Provide comprehensive analysis")
        self.logger.info("")
        
    def analyze_frame(self, frame_data, frame_num):
        """Analyze a single frame in detail"""
        self.logger.info(f"Frame {frame_num} Analysis:")
        self.logger.info(f"  Length: {len(frame_data)} bytes")
        
        # Show first 32 bytes in hex
        hex_data = frame_data[:32].hex()
        self.logger.info(f"  First 32 bytes: {hex_data}")
        
        # Show first 32 bytes as ASCII (if printable)
        ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in frame_data[:32])
        self.logger.info(f"  ASCII: {ascii_data}")
        
        # Analyze byte patterns
        if len(frame_data) > 0:
            # Check for common patterns
            all_zeros = all(b == 0 for b in frame_data)
            all_ff = all(b == 0xff for b in frame_data)
            all_same = len(set(frame_data)) == 1
            
            if all_zeros:
                self.logger.info(f"  Pattern: All zeros (silence)")
            elif all_ff:
                self.logger.info(f"  Pattern: All 0xFF (silence/padding)")
            elif all_same:
                self.logger.info(f"  Pattern: All same value ({frame_data[0]:02x})")
            else:
                # Calculate some statistics
                min_val = min(frame_data)
                max_val = max(frame_data)
                avg_val = sum(frame_data) / len(frame_data)
                self.logger.info(f"  Pattern: Mixed data (min={min_val:02x}, max={max_val:02x}, avg={avg_val:.1f})")
        
        self.logger.info("")
    
    def handle_connection(self, call):
        """Handle AudioSocket connection with detailed instrumentation"""
        self.logger.info("=" * 60)
        self.logger.info("INSTRUMENTED ANALYSIS - NEW CONNECTION")
        self.logger.info("=" * 60)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info(f"Connection time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        total_bytes = 0
        frame_sizes = []
        start_time = time.time()
        last_frame_time = start_time
        
        # Frame timing analysis
        frame_intervals = []
        
        try:
            # Run for 3 seconds
            while call.connected and (time.time() - start_time) < 3.0:
                # Read incoming audio
                audio_data = call.read()
                current_time = time.time()
                
                frame_count += 1
                total_bytes += len(audio_data)
                frame_sizes.append(len(audio_data))
                
                # Calculate frame interval
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    frame_intervals.append(interval)
                last_frame_time = current_time
                
                # Analyze frame (log first 10 frames in detail)
                if frame_count <= 10:
                    self.analyze_frame(audio_data, frame_count)
                elif frame_count % 50 == 0:
                    # Log summary every 50 frames
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    avg_interval = sum(frame_intervals[-10:]) / min(10, len(frame_intervals)) if frame_intervals else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, "
                                   f"FPS: {fps:.1f}, Interval: {avg_interval*1000:.1f}ms")
                
                # Small delay to prevent overwhelming
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
        
        # Send hangup after 3 seconds
        self.logger.info("3 seconds elapsed, sending hangup message...")
        try:
            call.hangup()
            self.logger.info("✅ Hangup message sent successfully")
        except Exception as e:
            self.logger.error(f"❌ Error sending hangup: {e}")
        
        # Wait for connection to close
        time.sleep(0.5)
        
        # Comprehensive analysis
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("COMPREHENSIVE ANALYSIS")
        self.logger.info("=" * 60)
        
        # Basic statistics
        self.logger.info(f"Total frames received: {frame_count}")
        self.logger.info(f"Total bytes received: {total_bytes}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            # Frame rate analysis
            avg_fps = frame_count / total_time if total_time > 0 else 0
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Expected FPS: {1/0.02:.1f} (50 FPS for 20ms frames)")
            
            # Frame size analysis
            if frame_sizes:
                avg_size = sum(frame_sizes) / len(frame_sizes)
                min_size = min(frame_sizes)
                max_size = max(frame_sizes)
                self.logger.info(f"Frame sizes: avg={avg_size:.1f}, min={min_size}, max={max_size}")
                
                # Check for consistent frame sizes
                size_variation = max_size - min_size
                if size_variation == 0:
                    self.logger.info("✅ Frame sizes are consistent")
                else:
                    self.logger.warning(f"⚠️  Frame size variation: {size_variation} bytes")
            
            # Frame timing analysis
            if frame_intervals:
                avg_interval = sum(frame_intervals) / len(frame_intervals)
                min_interval = min(frame_intervals)
                max_interval = max(frame_intervals)
                
                self.logger.info(f"Frame intervals: avg={avg_interval*1000:.1f}ms, "
                               f"min={min_interval*1000:.1f}ms, max={max_interval*1000:.1f}ms")
                
                # Check for consistent timing
                expected_interval = 0.02  # 20ms
                timing_variation = abs(avg_interval - expected_interval)
                if timing_variation < 0.005:  # Within 5ms
                    self.logger.info("✅ Frame timing is consistent")
                else:
                    self.logger.warning(f"⚠️  Frame timing variation: {timing_variation*1000:.1f}ms from expected")
            
            # Audio content analysis
            if frame_count > 0:
                # Sample a few frames for content analysis
                sample_frames = min(5, frame_count)
                silence_frames = 0
                audio_frames = 0
                
                for i in range(sample_frames):
                    # Use frame_count - sample_frames + i to get recent frames
                    frame_index = max(0, frame_count - sample_frames + i)
                    # For now, just count frames (we'll analyze content in detail later)
                    audio_frames += 1
                
                self.logger.info(f"Content analysis: {audio_frames} frames sampled")
        
        # Quality assessment
        self.logger.info("")
        self.logger.info("QUALITY ASSESSMENT:")
        if frame_count > 0:
            if avg_fps > 40:
                self.logger.info("✅ Excellent frame rate")
            elif avg_fps > 30:
                self.logger.info("✅ Good frame rate")
            else:
                self.logger.warning("⚠️  Low frame rate - may indicate issues")
            
            if size_variation == 0:
                self.logger.info("✅ Consistent frame sizes")
            else:
                self.logger.warning("⚠️  Inconsistent frame sizes")
        
        self.logger.info("=" * 60)
        self.logger.info("")
    
    def start(self):
        """Start the instrumented server"""
        self.logger.info("Instrumented Server is running...")
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
            self.logger.info("Instrumented Server stopped by user")
            self.logger.info(f"Total connections analyzed: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Instrumented Server")
    print("==================")
    print("This server provides detailed analysis of AudioSocket connections.")
    print("\nFeatures:")
    print("- Accepts AudioSocket connections")
    print("- Logs detailed frame information for 3 seconds")
    print("- Analyzes frame timing and content")
    print("- Provides comprehensive quality assessment")
    print("\nThis will help understand:")
    print("- Frame timing consistency")
    print("- Frame size consistency")
    print("- Audio content patterns")
    print("- Overall connection quality")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = InstrumentedServer()
    server.start()


if __name__ == "__main__":
    main() 