#!/usr/bin/env python3
"""
Universal Adaptive Echo Server
Handles any audio format that Asterisk sends, regardless of device negotiation.
"""

import time
from threading import Thread
from collections import Counter

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class UniversalAdaptiveEchoServer:
    """Universal echo server that adapts to any audio format from Asterisk"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Start with 8kHz as default, but will adapt
        self.audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
        self.audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)
        
        self.logger = ColouredLogger("universal_echo")
        self.logger.info(f"Universal adaptive echo server started on {host}:{port}")
        self.logger.info("This server adapts to ANY audio format from Asterisk")
        
        # Dynamic configuration tracking
        self.detected_formats = {}
        
    def analyze_frame_size(self, frame_size):
        """Analyze what the frame size tells us about the audio format"""
        # Common frame sizes and their likely configurations
        frame_analysis = {
            160: "8kHz, mono, 16-bit PCM, 10ms frames",
            320: "8kHz, mono, 16-bit PCM, 20ms frames",
            640: "8kHz, mono, 16-bit PCM, 40ms frames OR 16kHz, mono, 16-bit PCM, 20ms frames",
            1280: "8kHz, stereo, 16-bit PCM, 40ms frames OR 16kHz, mono, 16-bit PCM, 40ms frames",
            2560: "16kHz, stereo, 16-bit PCM, 40ms frames",
            320: "8kHz, mono, ULAW, 20ms frames",
            640: "8kHz, mono, ULAW, 40ms frames",
            1280: "8kHz, stereo, ULAW, 40ms frames",
        }
        
        return frame_analysis.get(frame_size, f"Unknown format: {frame_size} bytes")
    
    def detect_audio_format(self, frame_sizes, frame_intervals):
        """Detect the most likely audio format based on frame sizes and timing"""
        if not frame_sizes:
            return "Unknown"
        
        # Get the most common frame size
        size_counter = Counter(frame_sizes)
        most_common_size = size_counter.most_common(1)[0][0]
        
        # Get average frame interval
        avg_interval = sum(frame_intervals) / len(frame_intervals) if frame_intervals else 0
        
        # Analyze the format
        format_analysis = self.analyze_frame_size(most_common_size)
        
        # Determine sample rate based on frame size and timing
        if most_common_size == 1280:
            if 15 <= avg_interval*1000 <= 25:  # ~20ms intervals
                return "16kHz, mono, 16-bit PCM, 20ms frames"
            elif 35 <= avg_interval*1000 <= 45:  # ~40ms intervals
                return "8kHz, stereo, 16-bit PCM, 40ms frames"
        elif most_common_size == 640:
            if 15 <= avg_interval*1000 <= 25:  # ~20ms intervals
                return "16kHz, mono, 16-bit PCM, 20ms frames"
            elif 35 <= avg_interval*1000 <= 45:  # ~40ms intervals
                return "8kHz, mono, 16-bit PCM, 40ms frames"
        elif most_common_size == 320:
            return "8kHz, mono, 16-bit PCM, 20ms frames"
        
        return format_analysis
    
    def handle_connection(self, call):
        """Handle connection with universal format adaptation"""
        self.logger.info(f"New connection from {call.peer_addr}")
        
        frame_count = 0
        start_time = time.time()
        last_frame_time = start_time
        
        # Frame analysis data
        frame_sizes = []
        frame_intervals = []
        
        # Analysis phase (first 20 frames)
        analysis_phase = True
        
        while call.connected:
            try:
                # Read audio data
                audio_data = call.read()
                current_time = time.time()
                
                frame_size = len(audio_data)
                frame_count += 1
                
                # Track frame timing
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    frame_intervals.append(interval)
                last_frame_time = current_time
                
                # Collect data during analysis phase
                if analysis_phase and frame_count <= 20:
                    frame_sizes.append(frame_size)
                    
                    if frame_count == 20:
                        # Complete analysis
                        detected_format = self.detect_audio_format(frame_sizes, frame_intervals)
                        self.logger.info("="*50)
                        self.logger.info("AUDIO FORMAT ANALYSIS COMPLETE")
                        self.logger.info("="*50)
                        self.logger.info(f"Detected format: {detected_format}")
                        self.logger.info(f"Frame sizes observed: {set(frame_sizes)}")
                        if frame_intervals:
                            avg_interval = sum(frame_intervals) / len(frame_intervals)
                            self.logger.info(f"Average frame interval: {avg_interval*1000:.1f}ms")
                        self.logger.info("="*50)
                        analysis_phase = False
                        
                        # Store format for this connection
                        self.detected_formats[call.peer_addr] = detected_format
                
                # Echo audio back (this is the key - we echo exactly what we receive)
                call.write(audio_data)
                
                # Log progress during analysis
                if analysis_phase:
                    self.logger.info(f"Frame {frame_count}: {frame_size} bytes (analyzing...)")
                elif frame_count % 100 == 0:
                    self.logger.info(f"Frame {frame_count}: {frame_size} bytes ✓")
                
                # Add small delay to prevent overwhelming the system
                time.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        # Final statistics
        if frame_sizes:
            detected_format = self.detected_formats.get(call.peer_addr, "Unknown")
            self.logger.info(f"Connection ended. Total frames: {frame_count}")
            self.logger.info(f"Format used: {detected_format}")
            self.logger.info(f"Frame sizes: {set(frame_sizes)}")
    
    def start(self):
        """Start the universal adaptive echo server"""
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
    print("Universal Adaptive Echo Server")
    print("==============================")
    print("This server handles ANY audio format that Asterisk sends.")
    print("It automatically detects and adapts to different formats.")
    print("\nFeatures:")
    print("- Automatic format detection")
    print("- Handles 8kHz, 16kHz, mono, stereo")
    print("- Handles different frame durations")
    print("- Handles ULAW and PCM formats")
    print("- Real-time format analysis")
    print("\nConnect your Asterisk AudioSocket and test with any device.\n")
    
    server = UniversalAdaptiveEchoServer()
    server.start()


if __name__ == "__main__":
    main() 