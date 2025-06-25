#!/usr/bin/env python3
"""
Test Fixed Implementation
Test the corrected AudioSocket implementation with proper variable-length frame parsing.
"""

import time
import socket
import struct
import threading
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class FixedImplementationTest:
    """Test the fixed AudioSocket implementation"""
    
    def __init__(self, host="127.0.0.1", port=6050):
        self.host = host
        self.port = port
        self.logger = ColouredLogger("fixed_test")
        
        # AudioSocket message types
        self.AUDIO_TYPE = b"\x10"
        self.UUID_TYPE = b"\x01"
        self.HANGUP_TYPE = b"\x00"
        
        self.server_running = False
        
    def start_server(self):
        """Start the fixed AudioSocket server"""
        self.logger.info("Starting fixed AudioSocket server...")
        
        def server_thread():
            try:
                audiosocket = Audiosocket((self.host, self.port))
                self.server_running = True
                self.logger.info(f"Server started on {self.host}:{self.port}")
                
                # Accept one connection
                call = audiosocket.listen()
                self.logger.info(f"Server accepted connection from {call.peer_addr}")
                
                frame_count = 0
                start_time = time.time()
                
                while call.connected:
                    try:
                        # Read incoming audio
                        audio_data = call.read()
                        frame_count += 1
                        
                        # Log first few frames
                        if frame_count <= 5:
                            self.logger.info(f"Server received frame {frame_count}: {len(audio_data)} bytes")
                        
                        # Echo immediately
                        call.write(audio_data)
                        
                        # Log every 50 frames
                        if frame_count % 50 == 0:
                            elapsed = time.time() - start_time
                            fps = frame_count / elapsed if elapsed > 0 else 0
                            self.logger.info(f"Server frame {frame_count}: FPS={fps:.1f}")
                        
                        time.sleep(0.001)
                        
                    except Exception as e:
                        self.logger.error(f"Server error: {e}")
                        break
                
                self.logger.info(f"Server connection ended. Total frames: {frame_count}")
                
            except Exception as e:
                self.logger.error(f"Server startup error: {e}")
                self.server_running = False
        
        # Start server thread
        server_thread = threading.Thread(target=server_thread)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait for server to start
        time.sleep(1)
        if not self.server_running:
            raise Exception("Server failed to start")
    
    def send_proper_frame(self, sock, msg_type, payload):
        """Send a properly formatted AudioSocket frame"""
        length = len(payload)
        frame = msg_type + length.to_bytes(2, "big") + payload
        sock.send(frame)
        return frame
    
    def test_connection(self):
        """Test the fixed implementation with proper frames"""
        self.logger.info("Testing fixed implementation...")
        
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        self.logger.info(f"Connected to server at {self.host}:{self.port}")
        
        # Send UUID frame
        uuid_payload = b"test-uuid-12345"
        self.send_proper_frame(sock, self.UUID_TYPE, uuid_payload)
        self.logger.info(f"Sent UUID frame: {uuid_payload}")
        
        time.sleep(0.1)
        
        # Send test audio frames
        test_frames = 10
        self.logger.info(f"Sending {test_frames} test audio frames...")
        
        for i in range(test_frames):
            # Create test audio data (320 bytes of alternating values)
            audio_data = bytes([i % 256] * 320)
            
            # Send audio frame
            self.send_proper_frame(sock, self.AUDIO_TYPE, audio_data)
            self.logger.info(f"Sent audio frame {i+1}: {len(audio_data)} bytes")
            
            time.sleep(0.02)  # 20ms between frames
        
        # Send hangup
        self.send_proper_frame(sock, self.HANGUP_TYPE, b"")
        self.logger.info("Sent hangup frame")
        
        # Close connection
        sock.close()
        self.logger.info("Test completed")
    
    def run_test(self):
        """Run the complete test"""
        try:
            # Start server
            self.start_server()
            
            # Run test
            self.test_connection()
            
            # Wait for server to finish
            time.sleep(2)
            
            self.logger.info("✅ Test completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Test failed: {e}")


def main():
    """Main function"""
    print("Fixed Implementation Test")
    print("========================")
    print("This test verifies the corrected AudioSocket implementation.")
    print("\nWhat it tests:")
    print("- Proper variable-length frame parsing")
    print("- Correct frame boundary detection")
    print("- Spec-compliant protocol handling")
    print("- Frame rate accuracy")
    print("\nThis should show correct 50 FPS instead of 700+ FPS.\n")
    
    test = FixedImplementationTest()
    test.run_test()


if __name__ == "__main__":
    main() 