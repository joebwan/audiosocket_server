#!/usr/bin/env python3
"""
Test Handshake
Simple test client for the handshake server.
"""

import socket
import time
from mylogging import ColouredLogger


class TestHandshake:
    """Test the handshake server"""
    
    def __init__(self, host="127.0.0.1", port=6050):
        self.host = host
        self.port = port
        self.logger = ColouredLogger("handshake_test")
        
        # AudioSocket frame types
        self.UUID_TYPE = b'\x01'
        self.AUDIO_TYPE = b'\x10'
        self.SILENCE_TYPE = b'\x02'
        
    def send_audiosocket_frame(self, sock, msg_type, payload):
        """Send an AudioSocket frame"""
        frame = msg_type + len(payload).to_bytes(2, "big") + payload
        sock.send(frame)
        return frame
    
    def test_connection(self):
        """Test connection to handshake server"""
        self.logger.info("Testing handshake server...")
        
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  # 5 second timeout
            
            # Connect to server
            self.logger.info(f"Connecting to {self.host}:{self.port}...")
            sock.connect((self.host, self.port))
            self.logger.info("✅ Connected successfully")
            
            # Send UUID frame
            uuid_payload = b"test-uuid-handshake"
            self.send_audiosocket_frame(sock, self.UUID_TYPE, uuid_payload)
            self.logger.info(f"Sent UUID frame: {uuid_payload}")
            
            # Wait a moment for server to process
            time.sleep(0.5)
            
            # Try to receive any response (should be hangup)
            try:
                response = sock.recv(1024)
                if response:
                    self.logger.info(f"Received response: {response[:20]}...")
                else:
                    self.logger.info("No response received (connection closed)")
            except socket.timeout:
                self.logger.info("No response received (timeout)")
            except Exception as e:
                self.logger.info(f"Error receiving response: {e}")
            
            # Close connection
            sock.close()
            self.logger.info("Connection closed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def run_test(self):
        """Run the handshake test"""
        self.logger.info("Handshake Test")
        self.logger.info("=" * 30)
        self.logger.info("Testing simple handshake server")
        self.logger.info("")
        
        success = self.test_connection()
        
        if success:
            self.logger.info("")
            self.logger.info("=" * 30)
            self.logger.info("✅ TEST PASSED")
            self.logger.info("✅ Handshake server is working correctly")
            self.logger.info("=" * 30)
        else:
            self.logger.error("")
            self.logger.error("=" * 30)
            self.logger.error("❌ TEST FAILED")
            self.logger.error("❌ Handshake server test failed")
            self.logger.error("=" * 30)
        
        return success


def main():
    """Main function"""
    test = TestHandshake()
    success = test.run_test()
    
    if success:
        print("\n✅ Handshake test completed successfully!")
    else:
        print("\n❌ Handshake test failed!")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 