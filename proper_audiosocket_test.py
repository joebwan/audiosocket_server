#!/usr/bin/env python3
"""
Proper AudioSocket Test
Tests the echo server using the correct AudioSocket binary protocol.
"""

import time
import numpy as np
import socket
import struct
import threading
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class ProperAudioSocketTest:
    """Proper AudioSocket test using binary protocol"""
    
    def __init__(self, host="127.0.0.1", port=6050):
        self.host = host
        self.port = port
        
        # Audio configuration
        self.sample_rate = 8000
        self.channels = 1
        self.frame_duration = 0.02  # 20ms
        self.frame_size = int(self.sample_rate * self.channels * 2 * self.frame_duration)  # 320 bytes
        
        self.logger = ColouredLogger("proper_test")
        self.logger.info(f"Proper AudioSocket test initialized")
        self.logger.info(f"Audio config: {self.sample_rate}Hz, {self.channels} channel(s), 16-bit PCM")
        self.logger.info(f"Frame size: {self.frame_size} bytes ({self.frame_duration*1000:.0f}ms)")
        
        # AudioSocket message types
        self.AUDIO_TYPE = b"\x10"  # Audio frame
        self.UUID_TYPE = b"\x01"   # UUID frame
        self.SILENCE_TYPE = b"\x02"  # Silence frame
        self.HANGUP_TYPE = b"\x00"  # Hangup frame
        self.ERROR_TYPE = b"\xff"   # Error frame
        
        # Test data
        self.original_audio = []
        self.echo_audio = []
        self.server_running = False
        
    def generate_test_audio(self, frequency=1000, duration=2.0, volume=0.3):
        """Generate test audio (1kHz sine wave)"""
        self.logger.info(f"Generating {duration}s test audio at {frequency}Hz...")
        
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, endpoint=False)
        audio = np.sin(2 * np.pi * frequency * t) * volume
        audio = (audio * 32767).astype(np.int16)
        
        # Split into frames
        frames = []
        samples_per_frame = int(self.sample_rate * self.frame_duration)
        
        for i in range(0, len(audio), samples_per_frame):
            frame = audio[i:i + samples_per_frame]
            if len(frame) == samples_per_frame:  # Only complete frames
                frames.append(frame.tobytes())
        
        self.logger.info(f"Generated {len(frames)} frames of test audio")
        return frames
    
    def send_audiosocket_frame(self, sock, msg_type, payload):
        """Send a proper AudioSocket frame"""
        # Format: [1 byte type][2 bytes length][payload]
        length = len(payload)
        frame = msg_type + length.to_bytes(2, "big") + payload
        sock.send(frame)
        return frame
    
    def start_server(self):
        """Start the echo server in a separate thread"""
        self.logger.info("Starting echo server...")
        
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
                            self.logger.info(f"Server frame {frame_count}: {len(audio_data)} bytes, FPS: {fps:.1f}")
                        
                        # Small delay
                        time.sleep(0.001)
                        
                    except Exception as e:
                        self.logger.error(f"Server error: {e}")
                        break
                
                self.logger.info(f"Server connection ended. Total frames: {frame_count}")
                
            except Exception as e:
                self.logger.error(f"Server startup error: {e}")
                self.server_running = False
        
        # Start server thread
        server_thread = Thread(target=server_thread)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait for server to start
        time.sleep(1)
        if not self.server_running:
            raise Exception("Server failed to start")
    
    def connect_and_send_audio(self, test_frames):
        """Connect to server and send test audio using proper AudioSocket protocol"""
        self.logger.info("Connecting to server...")
        
        # Create AudioSocket connection (like a real client would)
        from audiosocket import Audiosocket
        
        # Create a client connection to the server
        # Note: This is a bit of a hack since Audiosocket is designed for servers
        # In a real scenario, the client would be Asterisk, not another Python client
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        self.logger.info(f"Connected to server at {self.host}:{self.port}")
        
        # Send UUID frame (optional, but Asterisk might send this)
        uuid_payload = b"test-uuid-12345"
        self.send_audiosocket_frame(sock, self.UUID_TYPE, uuid_payload)
        self.logger.info(f"Sent UUID frame: {uuid_payload}")

        # Add a small delay to allow server to be ready
        time.sleep(self.frame_duration)

        # Send test audio frames
        self.logger.info(f"Sending {len(test_frames)} test frames...")
        start_time = time.time()
        
        for i, frame in enumerate(test_frames):
            self.logger.debug(f"Sending audio frame {i+1}")
            # Send audio frame
            audio_frame = self.send_audiosocket_frame(sock, self.AUDIO_TYPE, frame)
            
            # Store original audio
            self.original_audio.append(frame)
            
            # Log first few frames
            if i < 5:
                self.logger.info(f"Sent audio frame {i+1}: {len(frame)} bytes")
            
            # Frame timing (20ms)
            time.sleep(self.frame_duration)
        
        send_time = time.time() - start_time
        self.logger.info(f"Sent {len(test_frames)} frames in {send_time:.2f}s")
        
        # Send silence for 1 second to trigger echo
        self.logger.info("Sending 1 second of silence...")
        silence_payload = bytes(320)  # 320 bytes of silence
        
        for i in range(50):  # 50 frames = 1 second
            self.send_audiosocket_frame(sock, self.SILENCE_TYPE, silence_payload)
            time.sleep(self.frame_duration)
        
        self.logger.info("Silence sent")
        
        # Receive echo using proper AudioSocket protocol
        self.logger.info("Receiving echo...")
        echo_start_time = time.time()
        echo_frames = 0
        
        # Set socket timeout
        sock.settimeout(5.0)  # 5 second timeout
        
        try:
            while True:
                # Receive frame header (3 bytes: type + length)
                header = sock.recv(3)
                if not header or len(header) < 3:
                    break
                
                msg_type = header[:1]
                frame_length = int.from_bytes(header[1:3], "big")
                
                # Receive frame payload
                payload = b''
                while len(payload) < frame_length:
                    chunk = sock.recv(frame_length - len(payload))
                    if not chunk:
                        break
                    payload += chunk
                
                if len(payload) == frame_length:
                    # Check if this is an audio frame
                    if msg_type == self.AUDIO_TYPE:
                        self.echo_audio.append(payload)
                        echo_frames += 1
                        
                        # Log first few frames
                        if echo_frames <= 5:
                            self.logger.info(f"Received echo frame {echo_frames}: {len(payload)} bytes")
                        
                        # Log every 50 frames
                        if echo_frames % 50 == 0:
                            elapsed = time.time() - echo_start_time
                            fps = echo_frames / elapsed if elapsed > 0 else 0
                            self.logger.info(f"Echo frame {echo_frames}: {len(payload)} bytes, FPS: {fps:.1f}")
                    else:
                        self.logger.info(f"Received non-audio frame: type={msg_type!r}, length={frame_length}")
                else:
                    self.logger.warning(f"Incomplete frame received: {len(payload)}/{frame_length} bytes")
                    break
                    
        except socket.timeout:
            self.logger.info("Echo reception timeout")
        except Exception as e:
            self.logger.error(f"Echo reception error: {e}")
        
        echo_time = time.time() - echo_start_time
        self.logger.info(f"Received {echo_frames} echo frames in {echo_time:.2f}s")
        
        # Close connection
        sock.close()
        self.logger.info("Connection closed")
    
    def compare_audio(self):
        """Compare original audio with echo"""
        self.logger.info("\n" + "="*60)
        self.logger.info("AUDIO COMPARISON RESULTS")
        self.logger.info("="*60)
        
        original_frames = len(self.original_audio)
        echo_frames = len(self.echo_audio)
        
        self.logger.info(f"Original frames: {original_frames}")
        self.logger.info(f"Echo frames: {echo_frames}")
        
        if original_frames == 0:
            self.logger.error("❌ No original audio frames!")
            return False
        
        if echo_frames == 0:
            self.logger.error("❌ No echo frames received!")
            return False
        
        # Compare frame counts
        if echo_frames >= original_frames:
            self.logger.info(f"✅ Echo has sufficient frames ({echo_frames} >= {original_frames})")
        else:
            self.logger.warning(f"⚠️  Echo has fewer frames ({echo_frames} < {original_frames})")
        
        # Compare first few frames byte-for-byte and log hex
        compare_frames = min(5, original_frames, echo_frames)
        exact_matches = 0
        
        for i in range(compare_frames):
            sent = self.original_audio[i]
            echoed = self.echo_audio[i]
            if sent == echoed:
                exact_matches += 1
                self.logger.info(f"✅ Frame {i+1}: Exact match")
            else:
                self.logger.warning(f"⚠️  Frame {i+1}: Different")
                self.logger.info(f"  Sent  : {sent[:32].hex()} ...")
                self.logger.info(f"  Echoed: {echoed[:32].hex()} ...")
        
        if exact_matches == compare_frames:
            self.logger.info(f"✅ All {compare_frames} compared frames match exactly!")
        else:
            self.logger.warning(f"⚠️  Only {exact_matches}/{compare_frames} frames match exactly")
        
        # Calculate frame sizes
        original_sizes = [len(frame) for frame in self.original_audio]
        echo_sizes = [len(frame) for frame in self.echo_audio]
        
        avg_original_size = sum(original_sizes) / len(original_sizes) if original_sizes else 0
        avg_echo_size = sum(echo_sizes) / len(echo_sizes) if echo_sizes else 0
        
        self.logger.info(f"Average original frame size: {avg_original_size:.1f} bytes")
        self.logger.info(f"Average echo frame size: {avg_echo_size:.1f} bytes")
        
        if abs(avg_original_size - avg_echo_size) < 1:
            self.logger.info("✅ Frame sizes match")
        else:
            self.logger.warning(f"⚠️  Frame size mismatch: {avg_original_size:.1f} vs {avg_echo_size:.1f}")
        
        # Overall assessment
        if echo_frames >= original_frames and exact_matches == compare_frames:
            self.logger.info("🎉 TEST PASSED: Echo is working correctly!")
            return True
        elif echo_frames > 0:
            self.logger.info("⚠️  TEST PARTIAL: Echo received but with issues")
            return False
        else:
            self.logger.error("❌ TEST FAILED: No echo received")
            return False
    
    def run_test(self):
        """Run the complete test"""
        self.logger.info("Starting proper AudioSocket test...")
        
        try:
            # Generate test audio
            test_frames = self.generate_test_audio()
            
            # Start server
            self.start_server()
            
            # Connect and send audio
            self.connect_and_send_audio(test_frames)
            
            # Compare results
            success = self.compare_audio()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Test failed: {e}")
            return False


def main():
    """Main function"""
    print("Proper AudioSocket Test")
    print("======================")
    print("This test uses the correct AudioSocket binary protocol.")
    print("\nTest sequence:")
    print("1. Generate 2s test audio (1kHz sine wave)")
    print("2. Start echo server")
    print("3. Connect and send UUID frame")
    print("4. Send audio frames using binary protocol")
    print("5. Send silence frames")
    print("6. Receive and verify echo")
    print("\nThis matches what Asterisk actually sends.\n")
    
    test = ProperAudioSocketTest()
    success = test.run_test()
    
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed - check logs for details")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 