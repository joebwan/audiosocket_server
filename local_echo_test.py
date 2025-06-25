#!/usr/bin/env python3
"""
Local Echo Test
Tests the echo server locally by starting server, connecting as client,
sending audio, and verifying the echo response.
"""

import time
import numpy as np
import socket
import struct
import threading
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class LocalEchoTest:
    """Local echo test"""
    
    def __init__(self, host="127.0.0.1", port=6050):
        self.host = host
        self.port = port
        
        # Audio configuration
        self.sample_rate = 8000
        self.channels = 1
        self.frame_duration = 0.02  # 20ms
        self.frame_size = int(self.sample_rate * self.channels * 2 * self.frame_duration)  # 320 bytes
        
        self.logger = ColouredLogger("local_test")
        self.logger.info(f"Local echo test initialized")
        self.logger.info(f"Audio config: {self.sample_rate}Hz, {self.channels} channel(s), 16-bit PCM")
        self.logger.info(f"Frame size: {self.frame_size} bytes ({self.frame_duration*1000:.0f}ms)")
        
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
        """Connect to server and send test audio"""
        self.logger.info("Connecting to server...")
        
        # Create socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        self.logger.info(f"Connected to server at {self.host}:{self.port}")
        
        # Send AudioSocket headers
        self.logger.info("Sending AudioSocket headers...")
        
        # Format: "AudioSocket\n"
        sock.send(b"AudioSocket\n")
        
        # Format: "Sample-Rate: 8000\n"
        sock.send(f"Sample-Rate: {self.sample_rate}\n".encode())
        
        # Format: "Channels: 1\n"
        sock.send(f"Channels: {self.channels}\n".encode())
        
        # Format: "Format: signed-integer\n"
        sock.send(b"Format: signed-integer\n")
        
        # Format: "Bits: 16\n"
        sock.send(b"Bits: 16\n")
        
        # Format: "\n" (end of headers)
        sock.send(b"\n")
        
        self.logger.info("Headers sent successfully")
        
        # Send test audio frames
        self.logger.info(f"Sending {len(test_frames)} test frames...")
        start_time = time.time()
        
        for i, frame in enumerate(test_frames):
            # Send frame length
            sock.send(struct.pack(">I", len(frame)))
            
            # Send frame data
            sock.send(frame)
            
            # Store original audio
            self.original_audio.append(frame)
            
            # Log first few frames
            if i < 5:
                self.logger.info(f"Sent frame {i+1}: {len(frame)} bytes")
            
            # Frame timing (20ms)
            time.sleep(self.frame_duration)
        
        send_time = time.time() - start_time
        self.logger.info(f"Sent {len(test_frames)} frames in {send_time:.2f}s")
        
        # Send silence for 1 second to trigger echo
        self.logger.info("Sending 1 second of silence...")
        silence_frame = b'\x00' * self.frame_size
        
        for i in range(50):  # 50 frames = 1 second
            sock.send(struct.pack(">I", len(silence_frame)))
            sock.send(silence_frame)
            time.sleep(self.frame_duration)
        
        self.logger.info("Silence sent")
        
        # Receive echo
        self.logger.info("Receiving echo...")
        echo_start_time = time.time()
        echo_frames = 0
        
        # Set socket timeout
        sock.settimeout(5.0)  # 5 second timeout
        
        try:
            while True:
                # Receive frame length
                length_data = sock.recv(4)
                if not length_data:
                    break
                
                frame_length = struct.unpack(">I", length_data)[0]
                
                # Receive frame data
                frame_data = b''
                while len(frame_data) < frame_length:
                    chunk = sock.recv(frame_length - len(frame_data))
                    if not chunk:
                        break
                    frame_data += chunk
                
                if len(frame_data) == frame_length:
                    self.echo_audio.append(frame_data)
                    echo_frames += 1
                    
                    # Log first few frames
                    if echo_frames <= 5:
                        self.logger.info(f"Received echo frame {echo_frames}: {len(frame_data)} bytes")
                    
                    # Log every 50 frames
                    if echo_frames % 50 == 0:
                        elapsed = time.time() - echo_start_time
                        fps = echo_frames / elapsed if elapsed > 0 else 0
                        self.logger.info(f"Echo frame {echo_frames}: {len(frame_data)} bytes, FPS: {fps:.1f}")
                else:
                    self.logger.warning(f"Incomplete frame received: {len(frame_data)}/{frame_length} bytes")
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
        
        # Compare first few frames byte-for-byte
        compare_frames = min(5, original_frames, echo_frames)
        exact_matches = 0
        
        for i in range(compare_frames):
            if self.original_audio[i] == self.echo_audio[i]:
                exact_matches += 1
                self.logger.info(f"✅ Frame {i+1}: Exact match")
            else:
                self.logger.warning(f"⚠️  Frame {i+1}: Different")
        
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
        self.logger.info("Starting local echo test...")
        
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
    print("Local Echo Test")
    print("==============")
    print("This test starts a server, connects to itself, sends audio,")
    print("and verifies the echo response.")
    print("\nTest sequence:")
    print("1. Generate 2s test audio (1kHz sine wave)")
    print("2. Start echo server")
    print("3. Connect to server and send headers")
    print("4. Send test audio frames")
    print("5. Send 1s silence")
    print("6. Receive and verify echo")
    print("\nThis will help debug the audio path.\n")
    
    test = LocalEchoTest()
    success = test.run_test()
    
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed - check logs for details")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main()) 