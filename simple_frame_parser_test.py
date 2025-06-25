#!/usr/bin/env python3
"""
Simple Frame Parser Test
Simulates the AudioSocket frame parsing to understand the 14x speed issue.
"""

import time
from audiosocket import Audiosocket
from mylogging import ColouredLogger


class SimpleFrameParserTest:
    """Test frame parsing logic"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("parser_test")
        
        self.logger.info(f"Simple Frame Parser Test started on {host}:{port}")
        self.logger.info("This will analyze the frame parsing logic step by step")
        self.logger.info("")
        
    def parse_frame_manually(self, raw_data, frame_num):
        """Manually parse a frame to understand the logic"""
        self.logger.info(f"Manual Frame {frame_num} Parsing:")
        self.logger.info(f"  Raw data length: {len(raw_data)} bytes")
        
        if len(raw_data) < 3:
            self.logger.warning(f"  ⚠️  Data too short for frame header")
            return
        
        # Extract frame header
        frame_type = raw_data[0]
        frame_length = (raw_data[1] << 8) | raw_data[2]
        
        self.logger.info(f"  Parsed header: type=0x{frame_type:02x}, length={frame_length}")
        
        # Check if this looks valid
        if frame_type in [0x01, 0x10, 0x11, 0x12]:
            self.logger.info(f"  ✅ Valid frame type")
        else:
            self.logger.warning(f"  ⚠️  Unknown frame type")
        
        if 0 < frame_length <= 65535:
            self.logger.info(f"  ✅ Reasonable frame length")
        else:
            self.logger.warning(f"  ⚠️  Suspicious frame length")
        
        # Check payload
        expected_payload_size = len(raw_data) - 3
        if frame_length == expected_payload_size:
            self.logger.info(f"  ✅ Payload size matches ({frame_length} bytes)")
        else:
            self.logger.warning(f"  ⚠️  Payload size mismatch: expected {frame_length}, got {expected_payload_size}")
        
        # Show payload preview
        if len(raw_data) > 3:
            payload = raw_data[3:3+min(16, frame_length)]
            self.logger.info(f"  Payload preview: {payload.hex()}")
            
            # Check if payload looks like audio
            if frame_length == 160:  # Expected audio frame
                self.logger.info(f"  ✅ Expected audio frame size")
            else:
                self.logger.warning(f"  ⚠️  Unexpected frame size for audio")
        
        self.logger.info("")
    
    def handle_connection(self, call):
        """Handle connection with manual frame parsing"""
        self.logger.info("=" * 60)
        self.logger.info("SIMPLE FRAME PARSER TEST - NEW CONNECTION")
        self.logger.info("=" * 60)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Track parsing statistics
        frame_count = 0
        total_bytes = 0
        start_time = time.time()
        last_frame_time = start_time
        
        # Frame timing analysis
        frame_intervals = []
        
        try:
            # Run for 2 seconds
            while call.connected and (time.time() - start_time) < 2.0:
                # Read raw data if possible
                try:
                    if hasattr(call, 'socket'):
                        raw_data = call.socket.recv(1024)
                        if raw_data:
                            frame_count += 1
                            total_bytes += len(raw_data)
                            current_time = time.time()
                            
                            # Calculate interval
                            if frame_count > 1:
                                interval = current_time - last_frame_time
                                frame_intervals.append(interval)
                            last_frame_time = current_time
                            
                            # Manual parsing for first few frames
                            if frame_count <= 5:
                                self.parse_frame_manually(raw_data, frame_count)
                            elif frame_count % 100 == 0:
                                # Log summary
                                elapsed = current_time - start_time
                                fps = frame_count / elapsed if elapsed > 0 else 0
                                self.logger.info(f"Frame {frame_count}: {len(raw_data)} bytes, FPS: {fps:.1f}")
                    
                    # Also read processed audio
                    audio_data = call.read()
                    if audio_data and frame_count <= 10:
                        self.logger.info(f"Processed audio frame: {len(audio_data)} bytes")
                        self.logger.info(f"  First 16 bytes: {audio_data[:16].hex()}")
                        self.logger.info("")
                    
                except Exception as e:
                    self.logger.error(f"Error reading data: {e}")
                    break
                
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
        
        # Send hangup
        self.logger.info("2 seconds elapsed, sending hangup...")
        try:
            call.hangup()
            self.logger.info("✅ Hangup sent")
        except Exception as e:
            self.logger.error(f"❌ Error sending hangup: {e}")
        
        time.sleep(0.5)
        
        # Analysis summary
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("PARSING ANALYSIS SUMMARY")
        self.logger.info("=" * 60)
        
        self.logger.info(f"Raw frames received: {frame_count}")
        self.logger.info(f"Total bytes: {total_bytes}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            avg_fps = frame_count / total_time if total_time > 0 else 0
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Expected FPS: 50.0 (20ms intervals)")
            
            # Frame timing analysis
            if frame_intervals:
                avg_interval = sum(frame_intervals) / len(frame_intervals)
                min_interval = min(frame_intervals)
                max_interval = max(frame_intervals)
                
                self.logger.info(f"Frame intervals: avg={avg_interval*1000:.1f}ms, "
                               f"min={min_interval*1000:.1f}ms, max={max_interval*1000:.1f}ms")
                
                # Check for expected timing
                expected_interval = 0.02  # 20ms
                timing_variation = abs(avg_interval - expected_interval)
                
                if timing_variation < 0.005:
                    self.logger.info("✅ Frame timing is correct")
                else:
                    self.logger.warning(f"⚠️  Frame timing is {timing_variation*1000:.1f}ms off from expected")
            
            # Speed ratio analysis
            speed_ratio = avg_fps / 50.0 if avg_fps > 0 else 0
            self.logger.info(f"Speed ratio: {speed_ratio:.1f}x (expected: 1.0x)")
            
            if speed_ratio > 10:
                self.logger.error(f"❌ CRITICAL: Frames are {speed_ratio:.1f}x too fast!")
                self.logger.error("This indicates severe frame parsing issues")
            elif speed_ratio > 2:
                self.logger.warning(f"⚠️  Frames are {speed_ratio:.1f}x too fast")
            elif speed_ratio < 0.5:
                self.logger.warning(f"⚠️  Frames are {1/speed_ratio:.1f}x too slow")
            else:
                self.logger.info("✅ Frame timing is within acceptable range")
        
        self.logger.info("=" * 60)
        self.logger.info("")
    
    def start(self):
        """Start the parser test"""
        self.logger.info("Simple Frame Parser Test is running...")
        self.logger.info("Waiting for AudioSocket connections...")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("")
        
        connection_count = 0
        
        try:
            while True:
                call = self.audiosocket.listen()
                connection_count += 1
                
                self.logger.info(f"Connection #{connection_count} accepted")
                self.handle_connection(call)
                
        except KeyboardInterrupt:
            self.logger.info("")
            self.logger.info("Simple Frame Parser Test stopped by user")
            self.logger.info(f"Total connections analyzed: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Simple Frame Parser Test")
    print("========================")
    print("This test analyzes the frame parsing logic to understand the 14x speed issue.")
    print("\nWhat it will show:")
    print("- Raw frame parsing step by step")
    print("- Frame header analysis")
    print("- Timing calculations")
    print("- Speed ratio analysis")
    print("\nThis will help identify why frames are being processed too fast.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    test = SimpleFrameParserTest()
    test.start()


if __name__ == "__main__":
    main() 