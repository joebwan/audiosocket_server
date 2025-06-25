#!/usr/bin/env python3
"""
Frame Alignment Diagnostic Server
Analyzes raw byte patterns and identifying where frame boundaries are being corrupted.
"""

import time
from audiosocket import Audiosocket
from mylogging import ColouredLogger


class FrameAlignmentDiagnostic:
    """Diagnostic server for frame alignment issues"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("frame_align")
        
        self.logger.info(f"Frame Alignment Diagnostic started on {host}:{port}")
        self.logger.info("This server will analyze raw frame alignment issues")
        self.logger.info("")
        
    def analyze_raw_data(self, raw_data, frame_num):
        """Analyze raw data for frame alignment patterns"""
        self.logger.info(f"Raw Frame {frame_num} Analysis:")
        self.logger.info(f"  Total length: {len(raw_data)} bytes")
        
        # Show first 64 bytes in hex with byte positions
        hex_display = ""
        ascii_display = ""
        for i in range(min(64, len(raw_data))):
            if i % 16 == 0:
                if hex_display:
                    self.logger.info(f"  {i-16:02d}: {hex_display} | {ascii_display}")
                hex_display = ""
                ascii_display = ""
            
            hex_display += f"{raw_data[i]:02x} "
            ascii_display += chr(raw_data[i]) if 32 <= raw_data[i] <= 126 else "."
        
        if hex_display:
            self.logger.info(f"  {len(raw_data)//16*16:02d}: {hex_display} | {ascii_display}")
        
        # Analyze potential frame headers
        self.logger.info("  Frame Header Analysis:")
        for i in range(len(raw_data) - 2):
            # Look for potential frame type + length combinations
            frame_type = raw_data[i]
            frame_length = (raw_data[i+1] << 8) | raw_data[i+2]
            
            # Check if this looks like a valid frame header
            if frame_type in [0x01, 0x10, 0x11, 0x12]:  # Known frame types
                if 0 < frame_length <= 65535:  # Reasonable length
                    payload_start = i + 3
                    payload_end = payload_start + frame_length
                    
                    if payload_end <= len(raw_data):
                        self.logger.info(f"    Potential header at byte {i}: "
                                       f"type=0x{frame_type:02x}, length={frame_length}")
                        self.logger.info(f"      Payload: {raw_data[payload_start:payload_end][:16].hex()}")
                        
                        # Check if payload looks like audio data
                        if frame_length == 160:  # Expected audio frame size
                            self.logger.info(f"      ✅ Valid audio frame size")
                        else:
                            self.logger.warning(f"      ⚠️  Unexpected frame size")
        
        self.logger.info("")
    
    def handle_connection(self, call):
        """Handle connection with frame alignment analysis"""
        self.logger.info("=" * 80)
        self.logger.info("FRAME ALIGNMENT DIAGNOSTIC - NEW CONNECTION")
        self.logger.info("=" * 80)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Track raw data
        raw_data_buffer = b""
        frame_count = 0
        start_time = time.time()
        
        try:
            # Run for 2 seconds to capture alignment issues
            while call.connected and (time.time() - start_time) < 2.0:
                # Get raw data from the connection
                try:
                    # Read raw socket data if available
                    if hasattr(call, 'socket'):
                        raw_data = call.socket.recv(1024)
                        if raw_data:
                            raw_data_buffer += raw_data
                            frame_count += 1
                            
                            # Analyze raw data
                            if frame_count <= 5:  # Analyze first 5 raw chunks
                                self.analyze_raw_data(raw_data, frame_count)
                            
                            # Check for frame alignment patterns
                            if len(raw_data_buffer) >= 100:
                                self.analyze_buffer_patterns(raw_data_buffer)
                                raw_data_buffer = b""  # Reset buffer
                    
                    # Also read processed audio data
                    audio_data = call.read()
                    if audio_data and frame_count <= 10:
                        self.logger.info(f"Processed Frame {frame_count}: {len(audio_data)} bytes")
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
        
        # Summary
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("FRAME ALIGNMENT SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Raw data chunks analyzed: {frame_count}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        self.logger.info("")
        
        if raw_data_buffer:
            self.logger.info("Final buffer analysis:")
            self.analyze_buffer_patterns(raw_data_buffer)
        
        self.logger.info("=" * 80)
        self.logger.info("")
    
    def analyze_buffer_patterns(self, buffer_data):
        """Analyze patterns in a buffer of raw data"""
        self.logger.info("Buffer Pattern Analysis:")
        self.logger.info(f"  Buffer size: {len(buffer_data)} bytes")
        
        # Look for repeating patterns
        if len(buffer_data) >= 32:
            # Check for common patterns
            first_32 = buffer_data[:32]
            self.logger.info(f"  First 32 bytes: {first_32.hex()}")
            
            # Look for frame type patterns
            frame_types = []
            for i in range(len(buffer_data) - 2):
                frame_type = buffer_data[i]
                if frame_type in [0x01, 0x10, 0x11, 0x12, 0xff, 0xfe, 0xfd]:
                    frame_types.append((i, frame_type))
            
            if frame_types:
                self.logger.info(f"  Found {len(frame_types)} potential frame types:")
                for pos, ftype in frame_types[:10]:  # Show first 10
                    self.logger.info(f"    Byte {pos}: 0x{ftype:02x}")
                
                # Check for alignment patterns
                if len(frame_types) > 1:
                    intervals = []
                    for i in range(1, len(frame_types)):
                        interval = frame_types[i][0] - frame_types[i-1][0]
                        intervals.append(interval)
                    
                    if intervals:
                        avg_interval = sum(intervals) / len(intervals)
                        self.logger.info(f"  Average interval between frame types: {avg_interval:.1f} bytes")
                        
                        # Check if this matches expected frame size
                        expected_interval = 323  # 1 byte type + 2 bytes length + 320 bytes payload
                        if abs(avg_interval - expected_interval) < 10:
                            self.logger.info(f"  ✅ Interval matches expected frame size")
                        else:
                            self.logger.warning(f"  ⚠️  Interval doesn't match expected frame size")
        
        self.logger.info("")
    
    def start(self):
        """Start the diagnostic server"""
        self.logger.info("Frame Alignment Diagnostic is running...")
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
            self.logger.info("Frame Alignment Diagnostic stopped by user")
            self.logger.info(f"Total connections analyzed: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Frame Alignment Diagnostic Server")
    print("=================================")
    print("This server analyzes raw AudioSocket data to identify frame alignment issues.")
    print("\nWhat it will detect:")
    print("- Frame boundary corruption")
    print("- Misaligned frame headers")
    print("- Protocol violations")
    print("- Raw data patterns")
    print("\nThis will help understand why frames are being processed 14x too fast.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    diagnostic = FrameAlignmentDiagnostic()
    diagnostic.start()


if __name__ == "__main__":
    main() 