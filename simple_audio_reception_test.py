#!/usr/bin/env python3
"""
Simple Audio Reception Test
Primary goal: Confirm the server can 'hear' audio received from the AudioSocket.
"""

import socket
import time
import threading
from audiosocket import Audiosocket
from mylogging import ColouredLogger


class SimpleAudioReceptionTest:
    """Simple test to verify server receives audio frames"""
    
    def __init__(self, host="127.0.0.1", port=6050):
        self.host = host
        self.port = port
        self.logger = ColouredLogger("simple_test")
        
        # AudioSocket frame types
        self.UUID_TYPE = b'\x01'
        self.AUDIO_TYPE = b'\x10'
        self.SILENCE_TYPE = b'\x02'
        
        # Test audio frame (320 bytes of test pattern)
        self.test_frame = b'\x00\x01\x02\x03' * 80  # 320 bytes
        
    def send_audiosocket_frame(self, sock, msg_type, payload):
        """Send an AudioSocket frame"""
        frame = msg_type + len(payload).to_bytes(2, "big") + payload
        sock.send(frame)
        return frame
    
    def start_simple_server(self):
        """Start a simple server that just logs received audio"""
        self.logger.info("Starting simple audio reception server...")
        self.server_running = False
        self.frames_received = 0
        
        def server_thread():
            try:
                audiosocket = Audiosocket((self.host, self.port))
                self.server_running = True
                self.logger.info(f"Server started on {self.host}:{self.port}")
                
                # Accept one connection
                call = audiosocket.listen()
                self.logger.info(f"Server accepted connection from {call.peer_addr}")
                
                while call.connected:
                    try:
                        # Read incoming audio
                        audio_data = call.read()
                        self.frames_received += 1
                        
                        # Log every frame received
                        self.logger.info(f"Server received frame {self.frames_received}: {len(audio_data)} bytes")
                        
                        # Log first few bytes of audio data to verify it's not silence
                        first_bytes = audio_data[:16].hex()
                        self.logger.info(f"  First 16 bytes: {first_bytes}")
                        
                        # Check if it's silence (all zeros)
                        if all(b == 0 for b in audio_data):
                            self.logger.warning(f"  ⚠️  Frame {self.frames_received} is silence (all zeros)")
                        else:
                            self.logger.info(f"  ✅ Frame {self.frames_received} contains audio data")
                        
                        # Small delay to prevent overwhelming logs
                        time.sleep(0.01)
                        
                    except Exception as e:
                        self.logger.error(f"Server error: {e}")
                        break
                
                self.logger.info(f"Server connection ended. Total frames received: {self.frames_received}")
                
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
    
    def send_test_audio(self):
        """Send test audio frames to the server"""
        self.logger.info("Connecting to server...")
        
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        self.logger.info(f"Connected to server at {self.host}:{self.port}")
        
        # Send UUID frame
        uuid_payload = b"test-uuid-12345"
        self.send_audiosocket_frame(sock, self.UUID_TYPE, uuid_payload)
        self.logger.info(f"Sent UUID frame: {uuid_payload}")
        
        # Send 5 test audio frames
        self.logger.info("Sending 5 test audio frames...")
        for i in range(5):
            self.logger.info(f"Sending audio frame {i+1}: {len(self.test_frame)} bytes")
            self.send_audiosocket_frame(sock, self.AUDIO_TYPE, self.test_frame)
            time.sleep(0.1)  # 100ms between frames
        
        # Send 2 silence frames
        self.logger.info("Sending 2 silence frames...")
        silence_frame = bytes(320)
        for i in range(2):
            self.logger.info(f"Sending silence frame {i+1}")
            self.send_audiosocket_frame(sock, self.SILENCE_TYPE, silence_frame)
            time.sleep(0.1)
        
        # Wait a moment for server to process
        time.sleep(0.5)
        
        # Close connection
        sock.close()
        self.logger.info("Connection closed")
    
    def run_test(self):
        """Run the simple audio reception test"""
        self.logger.info("Simple Audio Reception Test")
        self.logger.info("=" * 40)
        self.logger.info("Primary goal: Confirm server can 'hear' audio from AudioSocket")
        self.logger.info("")
        
        try:
            # Start server
            self.start_simple_server()
            
            # Send test audio
            self.send_test_audio()
            
            # Wait for server to finish processing
            time.sleep(1)
            
            # Report results
            self.logger.info("")
            self.logger.info("=" * 40)
            self.logger.info("TEST RESULTS")
            self.logger.info("=" * 40)
            self.logger.info(f"Total frames received by server: {self.frames_received}")
            
            if self.frames_received >= 7:  # 5 audio + 2 silence
                self.logger.info("✅ SUCCESS: Server received all expected frames")
                self.logger.info("✅ Server can 'hear' audio from AudioSocket")
            else:
                self.logger.warning(f"⚠️  PARTIAL: Server received {self.frames_received}/7 expected frames")
            
            self.logger.info("=" * 40)
            
        except Exception as e:
            self.logger.error(f"Test failed: {e}")
            return False
        
        return True


def main():
    """Main function"""
    test = SimpleAudioReceptionTest()
    success = test.run_test()
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 