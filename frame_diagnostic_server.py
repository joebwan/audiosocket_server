#!/usr/bin/env python3
"""
Frame Diagnostic Server
Analyzes frame alignment and corruption issues from Asterisk AudioSocket connections.
"""

import time
import struct
from audiosocket import Audiosocket
from mylogging import ColouredLogger


class FrameDiagnosticServer:
    """Server that diagnoses frame alignment and corruption issues"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("frame_diagnostic")
        
        self.logger.info(f"Frame Diagnostic Server started on {host}:{port}")
        self.logger.info("This server will analyze frame alignment and corruption issues")
        self.logger.info("")
        
    def analyze_frame_data(self, data, frame_num):
        """Analyze frame data for corruption and alignment issues"""
        self.logger.info(f"Frame {frame_num} Analysis:")
        self.logger.info(f"  Raw data length: {len(data)} bytes")
        self.logger.info(f"  First 20 bytes: {data[:20].hex()}")
        
        if len(data) >= 3:
            # Try to parse as frame header
            msg_type = data[:1]
            length_bytes = data[1:3]
            length = int.from_bytes(length_bytes, "big")
            
            self.logger.info(f"  Parsed header - Type: {msg_type.hex()}, Length: {length}")
            
            # Check for common corruption patterns
            if msg_type == b'\xff':
                self.logger.warning(f"  ⚠️  Frame type corruption detected (0xff instead of expected type)")
            
            if length == 65535:
                self.logger.warning(f"  ⚠️  Frame length corruption detected (65535)")
            
            if length == 0:
                self.logger.warning(f"  ⚠️  Frame length corruption detected (0)")
            
            # Check if length matches actual data
            expected_payload = data[3:]
            if len(expected_payload) != length:
                self.logger.warning(f"  ⚠️  Length mismatch: header says {length}, actual payload is {len(expected_payload)}")
            
            # Analyze payload pattern
            if len(expected_payload) > 0:
                first_bytes = expected_payload[:16].hex()
                self.logger.info(f"  Payload start: {first_bytes}")
                
                # Check for silence pattern
                if all(b == 0xff for b in expected_payload[:10]):
                    self.logger.info(f"  📝 Pattern: All 0xFF (likely silence or padding)")
                elif all(b == 0x00 for b in expected_payload[:10]):
                    self.logger.info(f"  📝 Pattern: All 0x00 (likely silence)")
                else:
                    self.logger.info(f"  📝 Pattern: Mixed data (likely audio)")
        
        self.logger.info("")
    
    def handle_connection(self, call):
        """Handle AudioSocket connection with detailed frame analysis"""
        self.logger.info("=" * 60)
        self.logger.info("FRAME DIAGNOSTIC - NEW CONNECTION")
        self.logger.info("=" * 60)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info(f"Connection time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("")
        
        frame_count = 0
        start_time = time.time()
        
        try:
            while call.connected:
                # Read incoming audio
                audio_data = call.read()
                frame_count += 1
                
                # Analyze frame data
                self.analyze_frame_data(audio_data, frame_count)
                
                # Log every 10th frame to avoid overwhelming output
                if frame_count % 10 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Progress: {frame_count} frames, {fps:.1f} FPS")
                    self.logger.info("")
                
                # Stop after 50 frames to avoid overwhelming output
                if frame_count >= 50:
                    self.logger.info("Stopping analysis after 50 frames...")
                    break
                
                # Small delay
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
        
        # Send hangup
        self.logger.info("Sending hangup message...")
        try:
            call.hangup()
            self.logger.info("✅ Hangup message sent successfully")
        except Exception as e:
            self.logger.error(f"❌ Error sending hangup: {e}")
        
        # Final summary
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("FRAME DIAGNOSTIC SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total frames analyzed: {frame_count}")
        self.logger.info(f"Total time: {total_time:.2f}s")
        self.logger.info(f"Average FPS: {frame_count/total_time:.1f}")
        self.logger.info("=" * 60)
        self.logger.info("")
    
    def start(self):
        """Start the frame diagnostic server"""
        self.logger.info("Frame Diagnostic Server is running...")
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
            self.logger.info("Frame Diagnostic Server stopped by user")
            self.logger.info(f"Total connections analyzed: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Frame Diagnostic Server")
    print("======================")
    print("This server analyzes frame alignment and corruption issues.")
    print("\nFeatures:")
    print("- Detailed frame-by-frame analysis")
    print("- Corruption pattern detection")
    print("- Frame alignment verification")
    print("- Protocol compliance checking")
    print("\nThis will help identify:")
    print("- Frame header corruption")
    print("- Length field mismatches")
    print("- Data alignment issues")
    print("- Protocol violations")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = FrameDiagnosticServer()
    server.start()


if __name__ == "__main__":
    main() 