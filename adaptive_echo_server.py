#!/usr/bin/env python3
"""
Adaptive Echo Server
Automatically detects and adapts to different audio formats from Asterisk.
"""

import time
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class AdaptiveEchoServer:
    """Echo server that adapts to different audio formats"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Start with 8kHz mono as default
        self.audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
        self.audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)
        
        self.logger = ColouredLogger("adaptive_echo")
        self.logger.info(f"Adaptive echo server started on {host}:{port}")
        
        # Frame size detection
        self.detected_frame_size = None
        self.frame_size_samples = []
        
    def detect_frame_size(self, frame_size):
        """Detect the consistent frame size being used"""
        self.frame_size_samples.append(frame_size)
        
        # Use the most common frame size after 10 samples
        if len(self.frame_size_samples) >= 10:
            from collections import Counter
            counter = Counter(self.frame_size_samples)
            most_common = counter.most_common(1)[0]
            
            if most_common[1] >= 8:  # At least 8 out of 10 frames are the same size
                self.detected_frame_size = most_common[0]
                self.logger.info(f"Detected frame size: {self.detected_frame_size} bytes")
                
                # Analyze what this frame size means
                self.analyze_frame_size(self.detected_frame_size)
                return True
        
        return False
    
    def analyze_frame_size(self, frame_size):
        """Analyze what the frame size tells us about the audio format"""
        self.logger.info(f"Analyzing frame size: {frame_size} bytes")
        
        # Common configurations
        configs = {
            160: "8kHz, mono, 16-bit PCM, 10ms frames",
            320: "8kHz, mono, 16-bit PCM, 20ms frames (standard)",
            640: "8kHz, mono, 16-bit PCM, 40ms frames OR 16kHz, mono, 16-bit PCM, 20ms frames",
            1280: "8kHz, stereo, 16-bit PCM, 40ms frames OR 16kHz, mono, 16-bit PCM, 40ms frames",
            320: "8kHz, mono, ULAW, 20ms frames",
            640: "8kHz, mono, ULAW, 40ms frames",
        }
        
        if frame_size in configs:
            self.logger.info(f"Likely configuration: {configs[frame_size]}")
        else:
            self.logger.info(f"Unknown frame size: {frame_size} bytes")
            self.logger.info("This may indicate a custom or unusual audio configuration")
    
    def handle_connection(self, call):
        """Handle connection with adaptive frame size detection"""
        self.logger.info(f"New connection from {call.peer_addr}")
        
        frame_count = 0
        start_time = time.time()
        last_log_time = start_time
        
        # Reset frame size detection for new connection
        self.detected_frame_size = None
        self.frame_size_samples = []
        
        while call.connected:
            try:
                # Read audio data
                audio_data = call.read()
                frame_size = len(audio_data)
                
                frame_count += 1
                
                # Detect frame size during first 10 frames
                if frame_count <= 10:
                    if self.detect_frame_size(frame_size):
                        self.logger.info("Frame size detection complete")
                
                # Log unexpected frame sizes after detection
                if self.detected_frame_size and frame_size != self.detected_frame_size:
                    self.logger.warning(f"Frame size mismatch: expected {self.detected_frame_size}, got {frame_size}")
                
                # Echo audio back
                call.write(audio_data)
                
                # Log statistics every 5 seconds
                current_time = time.time()
                if current_time - last_log_time >= 5:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed
                    self.logger.info(f"Frames: {frame_count}, FPS: {fps:.1f}, "
                                   f"Frame size: {frame_size}, Elapsed: {elapsed:.1f}s")
                    last_log_time = current_time
                
                # Add small delay to prevent overwhelming the system
                time.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the adaptive echo server"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Server stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Adaptive Echo Server")
    print("====================")
    print("This server automatically detects and adapts to different audio formats.")
    print("It will work with various Asterisk configurations without manual setup.")
    print("\nFeatures:")
    print("- Automatic frame size detection")
    print("- Audio format analysis")
    print("- Real-time statistics")
    print("- Robust error handling")
    print("\nConnect your Asterisk AudioSocket and make a call to test.\n")
    
    server = AdaptiveEchoServer()
    server.start()


if __name__ == "__main__":
    main() 
