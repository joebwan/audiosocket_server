#!/usr/bin/env python3
"""
Buffered 8kHz Echo Server
Uses proper audio buffering to eliminate delays while maintaining smooth audio.
"""

import time
import collections
from threading import Thread, Lock

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class AudioBuffer:
    """Thread-safe audio buffer for smooth playback"""
    
    def __init__(self, max_size=10):
        self.buffer = collections.deque(maxlen=max_size)
        self.lock = Lock()
        self.max_size = max_size
        
    def add(self, audio_data):
        """Add audio data to buffer"""
        with self.lock:
            if len(self.buffer) < self.max_size:
                self.buffer.append(audio_data)
                return True
            return False
    
    def get(self):
        """Get audio data from buffer"""
        with self.lock:
            if self.buffer:
                return self.buffer.popleft()
            return None
    
    def size(self):
        """Get current buffer size"""
        with self.lock:
            return len(self.buffer)
    
    def clear(self):
        """Clear buffer"""
        with self.lock:
            self.buffer.clear()


class Buffered8kHzEchoServer:
    """8kHz buffered echo server"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Configure for 8kHz telephony standard
        self.sample_rate = 8000
        self.channels = 1  # Mono
        self.frame_duration = 0.02  # 20ms frames
        
        # Calculate frame size for 8kHz, mono, 16-bit PCM
        self.frame_size = int(self.sample_rate * self.channels * 2 * self.frame_duration)
        
        self.logger = ColouredLogger("buffered_8khz")
        self.logger.info(f"Buffered 8kHz echo server started on {host}:{port}")
        self.logger.info(f"Audio config: {self.sample_rate}Hz, {self.channels} channel(s), 16-bit PCM")
        self.logger.info(f"Frame size: {self.frame_size} bytes ({self.frame_duration*1000:.0f}ms)")
        self.logger.info(f"Buffer size: 10 frames ({self.frame_duration*10*1000:.0f}ms)")
        
        # Audio buffer for smooth playback
        self.audio_buffer = AudioBuffer(max_size=10)
        
    def handle_connection(self, call):
        """Handle connection with buffered echo"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting buffered echo...")
        
        frame_count = 0
        start_time = time.time()
        last_frame_time = start_time
        
        # Performance tracking
        frame_intervals = []
        buffer_underruns = 0
        buffer_overruns = 0
        
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
                
                # Add to buffer
                if not self.audio_buffer.add(audio_data):
                    buffer_overruns += 1
                    if buffer_overruns % 10 == 0:
                        self.logger.warning(f"Buffer overrun {buffer_overruns} times")
                
                # Get from buffer and echo
                buffered_audio = self.audio_buffer.get()
                if buffered_audio:
                    call.write(buffered_audio)
                else:
                    buffer_underruns += 1
                    if buffer_underruns % 10 == 0:
                        self.logger.warning(f"Buffer underrun {buffer_underruns} times")
                    # Echo current frame if buffer is empty
                    call.write(audio_data)
                
                # Log performance every 100 frames
                if frame_count % 100 == 0:
                    buffer_size = self.audio_buffer.size()
                    avg_interval = sum(frame_intervals[-50:]) / min(50, len(frame_intervals)) if frame_intervals else 0
                    fps = 1 / avg_interval if avg_interval > 0 else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, "
                                   f"Buffer: {buffer_size}/{self.audio_buffer.max_size}, "
                                   f"FPS: {fps:.1f}, "
                                   f"Interval: {avg_interval*1000:.1f}ms")
                
                # Small delay to prevent overwhelming
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error: {e}")
                break
        
        # Performance summary
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        
        self.logger.info("\n" + "="*60)
        self.logger.info("BUFFERED ECHO PERFORMANCE SUMMARY")
        self.logger.info("="*60)
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total time: {total_time:.1f}s")
        self.logger.info(f"Average FPS: {avg_fps:.1f}")
        self.logger.info(f"Expected FPS: {1/self.frame_duration:.1f}")
        self.logger.info(f"Buffer underruns: {buffer_underruns}")
        self.logger.info(f"Buffer overruns: {buffer_overruns}")
        
        if frame_intervals:
            avg_interval = sum(frame_intervals) / len(frame_intervals)
            min_interval = min(frame_intervals)
            max_interval = max(frame_intervals)
            
            self.logger.info(f"Average frame interval: {avg_interval*1000:.1f}ms")
            self.logger.info(f"Min frame interval: {min_interval*1000:.1f}ms")
            self.logger.info(f"Max frame interval: {max_interval*1000:.1f}ms")
        
        # Quality assessment
        if avg_fps > 40 and buffer_underruns < 10:
            self.logger.info("✅ Excellent performance - smooth audio with minimal delay")
        elif avg_fps > 30 and buffer_underruns < 50:
            self.logger.info("✅ Good performance - acceptable audio quality")
        else:
            self.logger.info("⚠️  Performance issues - may have audio problems")
        
        self.logger.info("="*60)
        
        # Clear buffer
        self.audio_buffer.clear()
    
    def start(self):
        """Start the buffered echo server"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Buffered echo server stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Buffered 8kHz Echo Server")
    print("=========================")
    print("This server uses audio buffering to eliminate delays.")
    print("\nFeatures:")
    print("- 8kHz mono 16-bit PCM (telephony standard)")
    print("- 10-frame audio buffer (200ms)")
    print("- Non-blocking reads (prevents choppy audio)")
    print("- Performance monitoring")
    print("- Automatic buffer management")
    print("\nThis should provide smooth echo with minimal delay.\n")
    
    server = Buffered8kHzEchoServer()
    server.start()


if __name__ == "__main__":
    main() 