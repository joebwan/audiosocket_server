#!/usr/bin/env python3
"""
Simple Smooth Echo Server
Echoes audio directly without buffering to eliminate choppy audio.
"""

import time
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class SimpleSmoothEchoServer:
    """Simple smooth echo server"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Configure for 8kHz telephony standard
        self.sample_rate = 8000
        self.channels = 1  # Mono
        self.frame_duration = 0.02  # 20ms frames
        
        # Calculate frame size for 8kHz, mono, 16-bit PCM
        self.frame_size = int(self.sample_rate * self.channels * 2 * self.frame_duration)
        
        self.logger = ColouredLogger("simple_echo")
        self.logger.info(f"Simple smooth echo server started on {host}:{port}")
        self.logger.info(f"Audio config: {self.sample_rate}Hz, {self.channels} channel(s), 16-bit PCM")
        self.logger.info(f"Frame size: {self.frame_size} bytes ({self.frame_duration*1000:.0f}ms)")
        
    def handle_connection(self, call):
        """Handle connection with simple echo"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting simple echo...")
        
        frame_count = 0
        start_time = time.time()
        last_frame_time = start_time
        
        # Performance tracking
        frame_intervals = []
        
        while call.connected:
            try:
                # Read incoming audio (non-blocking)
                audio_data = call.read()
                current_time = time.time()
                
                frame_count += 1
                
                # Track frame timing
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    frame_intervals.append(interval)
                    
                    # Log slow frames
                    if interval > 0.05:
                        self.logger.warning(f"Slow frame {frame_count}: {interval*1000:.1f}ms")
                last_frame_time = current_time
                
                # Echo immediately
                call.write(audio_data)
                
                # Log performance every 100 frames
                if frame_count % 100 == 0:
                    avg_interval = sum(frame_intervals[-50:]) / min(50, len(frame_intervals)) if frame_intervals else 0
                    fps = 1 / avg_interval if avg_interval > 0 else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, "
                                   f"FPS: {fps:.1f}, "
                                   f"Interval: {avg_interval*1000:.1f}ms")
                
                # No artificial delay - let it run as fast as possible
                
            except Exception as e:
                self.logger.error(f"Error: {e}")
                break
        
        # Performance summary
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        
        self.logger.info("\n" + "="*50)
        self.logger.info("SIMPLE ECHO PERFORMANCE SUMMARY")
        self.logger.info("="*50)
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total time: {total_time:.1f}s")
        self.logger.info(f"Average FPS: {avg_fps:.1f}")
        self.logger.info(f"Expected FPS: {1/self.frame_duration:.1f}")
        
        if frame_intervals:
            avg_interval = sum(frame_intervals) / len(frame_intervals)
            min_interval = min(frame_intervals)
            max_interval = max(frame_intervals)
            
            self.logger.info(f"Average frame interval: {avg_interval*1000:.1f}ms")
            self.logger.info(f"Min frame interval: {min_interval*1000:.1f}ms")
            self.logger.info(f"Max frame interval: {max_interval*1000:.1f}ms")
        
        # Quality assessment
        if avg_fps > 40:
            self.logger.info("✅ Excellent performance - smooth echo")
        elif avg_fps > 30:
            self.logger.info("✅ Good performance - acceptable echo")
        else:
            self.logger.info("⚠️  Performance issues - may have choppy echo")
        
        self.logger.info("="*50)
    
    def start(self):
        """Start the simple echo server"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Simple echo server stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Simple Smooth Echo Server")
    print("========================")
    print("This server echoes audio directly without buffering.")
    print("\nFeatures:")
    print("- 8kHz mono 16-bit PCM (telephony standard)")
    print("- Direct echo (no buffering)")
    print("- Non-blocking reads")
    print("- Performance monitoring")
    print("\nThis should provide smooth echo with minimal delay.\n")
    
    server = SimpleSmoothEchoServer()
    server.start()


if __name__ == "__main__":
    main() 