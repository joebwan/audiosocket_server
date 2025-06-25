#!/usr/bin/env python3
"""
Audio Diagnostic Server
Analyzes audio processing issues and provides detailed diagnostics.
"""

import time
import numpy as np
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class AudioDiagnosticServer:
    """Server with detailed audio processing diagnostics"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("audio_diag")
        
        self.logger.info(f"Audio Diagnostic Server started on {host}:{port}")
        self.logger.info("This server will analyze audio processing issues")
        self.logger.info("")
        
    def analyze_audio_frame(self, audio_data, frame_num):
        """Analyze audio frame content and characteristics"""
        if len(audio_data) == 0:
            return
        
        # Convert to numpy array for analysis
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Basic statistics
        min_val = np.min(audio_array)
        max_val = np.max(audio_array)
        mean_val = np.mean(audio_array)
        std_val = np.std(audio_array)
        
        # Check for silence
        is_silence = std_val < 100  # Low variance indicates silence
        
        # Check for clipping
        is_clipping = abs(max_val) > 32000 or abs(min_val) > 32000
        
        # Energy calculation
        energy = np.sum(audio_array.astype(np.float32) ** 2)
        
        # Zero crossing rate (speech activity indicator)
        zero_crossings = np.sum(np.diff(np.sign(audio_array)) != 0)
        
        self.logger.info(f"Frame {frame_num} Audio Analysis:")
        self.logger.info(f"  Size: {len(audio_data)} bytes ({len(audio_array)} samples)")
        self.logger.info(f"  Range: [{min_val}, {max_val}]")
        self.logger.info(f"  Mean: {mean_val:.1f}, Std: {std_val:.1f}")
        self.logger.info(f"  Energy: {energy:.0f}")
        self.logger.info(f"  Zero crossings: {zero_crossings}")
        
        if is_silence:
            self.logger.info(f"  Status: 🔇 Silence")
        elif is_clipping:
            self.logger.info(f"  Status: ⚠️  Clipping detected")
        else:
            self.logger.info(f"  Status: 🔊 Audio detected")
        
        self.logger.info("")
        
        return {
            'size': len(audio_data),
            'samples': len(audio_array),
            'min': min_val,
            'max': max_val,
            'mean': mean_val,
            'std': std_val,
            'energy': energy,
            'zero_crossings': zero_crossings,
            'is_silence': is_silence,
            'is_clipping': is_clipping
        }
    
    def handle_connection(self, call):
        """Handle connection with detailed audio diagnostics"""
        self.logger.info("=" * 60)
        self.logger.info("AUDIO DIAGNOSTIC - NEW CONNECTION")
        self.logger.info("=" * 60)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        total_bytes = 0
        frame_sizes = []
        audio_analyses = []
        start_time = time.time()
        last_frame_time = start_time
        
        # Frame timing analysis
        frame_intervals = []
        
        try:
            # Run for 10 seconds to gather data
            while call.connected and (time.time() - start_time) < 10.0:
                # Read incoming audio
                audio_data = call.read()
                current_time = time.time()
                
                frame_count += 1
                total_bytes += len(audio_data)
                frame_sizes.append(len(audio_data))
                
                # Calculate frame interval
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    frame_intervals.append(interval)
                last_frame_time = current_time
                
                # Analyze first 10 frames in detail
                if frame_count <= 10:
                    analysis = self.analyze_audio_frame(audio_data, frame_count)
                    if analysis:
                        audio_analyses.append(analysis)
                
                # Echo immediately (simple pass-through)
                call.write(audio_data)
                
                # Log every 50 frames
                if frame_count % 50 == 0:
                    elapsed = current_time - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    avg_interval = sum(frame_intervals[-10:]) / min(10, len(frame_intervals)) if frame_intervals else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, "
                                   f"FPS: {fps:.1f}, Interval: {avg_interval*1000:.1f}ms")
                
                # Small delay
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
        
        # Send hangup
        self.logger.info("10 seconds elapsed, sending hangup...")
        try:
            call.hangup()
            self.logger.info("✅ Hangup sent")
        except Exception as e:
            self.logger.error(f"❌ Error sending hangup: {e}")
        
        time.sleep(0.5)
        
        # Comprehensive analysis
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("AUDIO PROCESSING ANALYSIS")
        self.logger.info("=" * 60)
        
        # Basic statistics
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total bytes: {total_bytes}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            # Frame rate analysis
            avg_fps = frame_count / total_time if total_time > 0 else 0
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Expected FPS: 50.0 (20ms intervals)")
            
            # Frame size analysis
            if frame_sizes:
                avg_size = sum(frame_sizes) / len(frame_sizes)
                min_size = min(frame_sizes)
                max_size = max(frame_sizes)
                size_variation = max_size - min_size
                
                self.logger.info(f"Frame sizes: avg={avg_size:.1f}, min={min_size}, max={max_size}")
                
                if size_variation == 0:
                    self.logger.info("✅ Frame sizes are consistent")
                else:
                    self.logger.warning(f"⚠️  Frame size variation: {size_variation} bytes")
                
                # Check for expected frame size
                if avg_size == 320:
                    self.logger.info("✅ Frame size matches expected 320 bytes (20ms at 8kHz)")
                elif avg_size == 160:
                    self.logger.info("⚠️  Frame size is 160 bytes (10ms at 8kHz) - shorter than expected")
                else:
                    self.logger.warning(f"⚠️  Unexpected frame size: {avg_size} bytes")
            
            # Frame timing analysis
            if frame_intervals:
                avg_interval = sum(frame_intervals) / len(frame_intervals)
                min_interval = min(frame_intervals)
                max_interval = max(frame_intervals)
                
                self.logger.info(f"Frame intervals: avg={avg_interval*1000:.1f}ms, "
                               f"min={min_interval*1000:.1f}ms, max={max_interval*1000:.1f}ms")
                
                # Check for consistent timing
                expected_interval = 0.02  # 20ms
                timing_variation = abs(avg_interval - expected_interval)
                if timing_variation < 0.005:
                    self.logger.info("✅ Frame timing is consistent")
                else:
                    self.logger.warning(f"⚠️  Frame timing variation: {timing_variation*1000:.1f}ms from expected")
            
            # Audio content analysis
            if audio_analyses:
                silence_frames = sum(1 for a in audio_analyses if a['is_silence'])
                audio_frames = len(audio_analyses) - silence_frames
                clipping_frames = sum(1 for a in audio_analyses if a['is_clipping'])
                
                self.logger.info(f"Audio content analysis:")
                self.logger.info(f"  Silence frames: {silence_frames}/{len(audio_analyses)}")
                self.logger.info(f"  Audio frames: {audio_frames}/{len(audio_analyses)}")
                self.logger.info(f"  Clipping frames: {clipping_frames}/{len(audio_analyses)}")
                
                if audio_frames > 0:
                    avg_energy = sum(a['energy'] for a in audio_analyses if not a['is_silence']) / audio_frames
                    self.logger.info(f"  Average audio energy: {avg_energy:.0f}")
        
        # Quality assessment
        self.logger.info("")
        self.logger.info("QUALITY ASSESSMENT:")
        if frame_count > 0:
            if avg_fps > 45 and avg_fps < 55:
                self.logger.info("✅ Frame rate is correct")
            else:
                self.logger.warning(f"⚠️  Frame rate is {avg_fps:.1f} FPS (expected ~50)")
            
            if size_variation == 0:
                self.logger.info("✅ Frame sizes are consistent")
            else:
                self.logger.warning("⚠️  Frame sizes are inconsistent")
            
            if timing_variation < 0.005:
                self.logger.info("✅ Frame timing is consistent")
            else:
                self.logger.warning("⚠️  Frame timing is inconsistent")
        
        self.logger.info("=" * 60)
        self.logger.info("")
    
    def start(self):
        """Start the diagnostic server"""
        self.logger.info("Audio Diagnostic Server is running...")
        self.logger.info("Waiting for AudioSocket connections...")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("")
        
        connection_count = 0
        
        try:
            while True:
                call = self.audiosocket.listen()
                connection_count += 1
                
                self.logger.info(f"Connection #{connection_count} accepted")
                self.handle_connection(call)
                
        except KeyboardInterrupt:
            self.logger.info("")
            self.logger.info("Audio Diagnostic Server stopped by user")
            self.logger.info(f"Total connections analyzed: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Audio Diagnostic Server")
    print("======================")
    print("This server analyzes audio processing issues.")
    print("\nWhat it will show:")
    print("- Frame size analysis")
    print("- Audio content analysis")
    print("- Timing consistency")
    print("- Audio quality metrics")
    print("\nThis will help identify why audio is choppy/faint.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = AudioDiagnosticServer()
    server.start()


if __name__ == "__main__":
    main() 