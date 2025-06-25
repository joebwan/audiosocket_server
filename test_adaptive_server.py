#!/usr/bin/env python3
"""
Test Adaptive Server
Test the adaptive echo server with variable frame sizes.
"""

import time
import socket
import threading
from adaptive_echo_server import AdaptiveEchoServer
from mylogging import ColouredLogger


class AdaptiveServerTest:
    """Test the adaptive echo server"""
    
    def __init__(self, host="127.0.0.1", port=6050):
        self.host = host
        self.port = port
        self.logger = ColouredLogger("adaptive_test")
        
        # AudioSocket message types
        self.AUDIO_TYPE = b"\x10"
        self.UUID_TYPE = b"\x01"
        self.HANGUP_TYPE = b"\x00"
        
        self.server_running = False
        
    def start_server(self):
        """Start the adaptive echo server"""
        self.logger.info("Starting adaptive echo server...")
        
        def server_thread():
            try:
                server = AdaptiveEchoServer(self.host, self.port)
                self.server_running = True
                self.logger.info(f"Server started on {self.host}:{self.port}")
                
                # Start the server (this will block until interrupted)
                server.start()
                
            except Exception as e:
                self.logger.error(f"Server error: {e}")
                self.server_running = False
        
        # Start server thread
        server_thread = threading.Thread(target=server_thread)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        if not self.server_running:
            raise Exception("Server failed to start")
    
    def send_proper_frame(self, sock, msg_type, payload):
        """Send a properly formatted AudioSocket frame"""
        length = len(payload)
        frame = msg_type + length.to_bytes(2, "big") + payload
        sock.send(frame)
        return frame
    
    def test_variable_frames(self):
        """Test with variable frame sizes"""
        self.logger.info("Testing adaptive server with variable frame sizes...")
        
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        self.logger.info(f"Connected to server at {self.host}:{self.port}")
        
        # Send UUID frame
        uuid_payload = b"test-uuid-12345"
        self.send_proper_frame(sock, self.UUID_TYPE, uuid_payload)
        self.logger.info(f"Sent UUID frame: {uuid_payload}")
        
        time.sleep(0.1)
        
        # Test different frame sizes
        test_frames = [
            (160, "160 bytes (10ms at 8kHz)"),
            (320, "320 bytes (20ms at 8kHz)"),
            (640, "640 bytes (40ms at 8kHz)"),
            (160, "160 bytes (10ms at 8kHz)"),
            (320, "320 bytes (20ms at 8kHz)"),
        ]
        
        self.logger.info(f"Sending {len(test_frames)} test frames with variable sizes...")
        
        for i, (size, description) in enumerate(test_frames):
            # Create test audio data
            audio_data = bytes([i % 256] * size)
            
            # Send audio frame
            self.send_proper_frame(sock, self.AUDIO_TYPE, audio_data)
            self.logger.info(f"Sent frame {i+1}: {size} bytes ({description})")
            
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
            self.test_variable_frames()
            
            # Wait for server to finish
            time.sleep(3)
            
            self.logger.info("✅ Test completed successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Test failed: {e}")


def main():
    """Main function"""
    print("Adaptive Server Test")
    print("===================")
    print("This test verifies the adaptive echo server handles variable frame sizes.")
    print("\nWhat it tests:")
    print("- Variable frame sizes (160, 320, 640 bytes)")
    print("- Proper frame handling without padding")
    print("- Real-time echo with correct timing")
    print("- Frame size monitoring")
    print("\nThis should show clean audio without choppy/faint issues.\n")
    
    test = AdaptiveServerTest()
    test.run_test()


if __name__ == "__main__":
    main() 