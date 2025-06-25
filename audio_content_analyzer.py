#!/usr/bin/env python3
"""
Audio Content Analyzer
Analyzes the actual audio data in frames to identify content issues.
"""

import time
import numpy as np
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class AudioContentAnalyzer:
    """Analyzer for audio content issues"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("audio_content")
        
        self.logger.info(f"Audio Content Analyzer started on {host}:{port}")
        self.logger.info("This will analyze the actual audio data in frames")
        self.logger.info("")
        
    def analyze_audio_content(self, audio_data, frame_num):
        """Analyze the actual audio content in detail"""
        if len(audio_data) == 0:
            return
        
        # Convert to numpy array for analysis
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Basic statistics
        min_val = np.min(audio_array)
        max_val = np.max(audio_array)
        mean_val = np.mean(audio_array)
        std_val = np.std(audio_array)
        
        # Check for common patterns
        all_zeros = np.all(audio_array == 0)
        all_same = np.all(audio_array == audio_array[0])
        all_ff = np.all(audio_array == -1)  # 0xFFFF in signed int16
        
        # Check for random noise (high variance)
        is_noise = std_val > 1000
        
        # Check for speech-like patterns
        zero_crossings = np.sum(np.diff(np.sign(audio_array)) != 0)
        zero_crossing_rate = zero_crossings / len(audio_array)
        
        # Energy calculation
        energy = np.sum(audio_array.astype(np.float32) ** 2)
        
        # Check for clipping
        is_clipping = abs(max_val) > 32000 or abs(min_val) > 32000
        
        # Show first 16 samples in detail
        first_16 = audio_array[:16]
        first_16_hex = [f"{x:04x}" for x in first_16]
        
        self.logger.info(f"Frame {frame_num} Content Analysis:")
        self.logger.info(f"  Size: {len(audio_data)} bytes ({len(audio_array)} samples)")
        self.logger.info(f"  First 16 samples: {first_16_hex}")
        self.logger.info(f"  Range: [{min_val}, {max_val}]")
        self.logger.info(f"  Mean: {mean_val:.1f}, Std: {std_val:.1f}")
        self.logger.info(f"  Energy: {energy:.0f}")
        self.logger.info(f"  Zero crossings: {zero_crossings} ({zero_crossing_rate:.3f} rate)")
        
        # Pattern analysis
        if all_zeros:
            self.logger.info(f"  Pattern: 🔇 All zeros (silence)")
        elif all_same:
            self.logger.info(f"  Pattern: 🔇 All same value ({audio_array[0]})")
        elif all_ff:
            self.logger.info(f"  Pattern: 🔇 All 0xFFFF (silence)")
        elif is_noise:
            self.logger.info(f"  Pattern: 🔊 High variance (noise/static)")
        elif zero_crossing_rate > 0.1:
            self.logger.info(f"  Pattern: 🔊 Speech-like (high zero-crossing rate)")
        else:
            self.logger.info(f"  Pattern: 🔇 Low variance (likely silence)")
        
        if is_clipping:
            self.logger.info(f"  Status: ⚠️  Clipping detected")
        
        # Check for potential encoding issues
        if std_val > 0 and std_val < 100:
            self.logger.info(f"  Note: Low variance - might be encoded audio")
        
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
            'zero_crossing_rate': zero_crossing_rate,
            'is_noise': is_noise,
            'is_clipping': is_clipping,
            'all_zeros': all_zeros,
            'all_same': all_same,
            'all_ff': all_ff,
            'first_16_hex': first_16_hex
        }
    
    def handle_connection(self, call):
        """Handle connection with detailed audio content analysis"""
        self.logger.info("=" * 70)
        self.logger.info("AUDIO CONTENT ANALYSIS - NEW CONNECTION")
        self.logger.info("=" * 70)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        content_analyses = []
        start_time = time.time()
        
        try:
            # Run for 5 seconds to gather data
            while call.connected and (time.time() - start_time) < 5.0:
                # Read incoming audio
                audio_data = call.read()
                
                # Skip empty frames
                if len(audio_data) == 0:
                    time.sleep(0.001)
                    continue
                
                frame_count += 1
                
                # Analyze first 20 frames in detail
                if frame_count <= 20:
                    analysis = self.analyze_audio_content(audio_data, frame_count)
                    if analysis:
                        content_analyses.append(analysis)
                
                # Echo immediately
                call.write(audio_data)
                
                # Log every 50 frames
                if frame_count % 50 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, FPS: {fps:.1f}")
                
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
        
        # Send hangup
        self.logger.info("5 seconds elapsed, sending hangup...")
        try:
            call.hangup()
            self.logger.info("✅ Hangup sent")
        except Exception as e:
            self.logger.error(f"❌ Error sending hangup: {e}")
        
        time.sleep(0.5)
        
        # Comprehensive analysis
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info("AUDIO CONTENT ANALYSIS SUMMARY")
        self.logger.info("=" * 70)
        
        self.logger.info(f"Total frames analyzed: {frame_count}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if content_analyses:
            # Pattern analysis
            silence_frames = sum(1 for a in content_analyses if a['all_zeros'] or a['all_same'] or a['all_ff'])
            noise_frames = sum(1 for a in content_analyses if a['is_noise'])
            speech_frames = sum(1 for a in content_analyses if a['zero_crossing_rate'] > 0.1 and not a['all_zeros'])
            
            self.logger.info(f"Content pattern analysis:")
            self.logger.info(f"  Silence frames: {silence_frames}/{len(content_analyses)}")
            self.logger.info(f"  Noise/static frames: {noise_frames}/{len(content_analyses)}")
            self.logger.info(f"  Speech-like frames: {speech_frames}/{len(content_analyses)}")
            
            # Energy analysis
            if speech_frames > 0:
                speech_energies = [a['energy'] for a in content_analyses if a['zero_crossing_rate'] > 0.1 and not a['all_zeros']]
                avg_speech_energy = sum(speech_energies) / len(speech_energies) if speech_energies else 0
                self.logger.info(f"  Average speech energy: {avg_speech_energy:.0f}")
            
            # Variance analysis
            variances = [a['std'] for a in content_analyses]
            avg_variance = sum(variances) / len(variances) if variances else 0
            self.logger.info(f"  Average variance: {avg_variance:.1f}")
            
            # Check for encoding issues
            low_variance_frames = sum(1 for a in content_analyses if 0 < a['std'] < 100)
            if low_variance_frames > 0:
                self.logger.warning(f"  ⚠️  {low_variance_frames} frames have low variance - possible encoding issue")
            
            # Show sample patterns
            self.logger.info(f"Sample patterns from first few frames:")
            for i, analysis in enumerate(content_analyses[:5]):
                pattern_desc = "silence" if analysis['all_zeros'] else "noise" if analysis['is_noise'] else "speech"
                self.logger.info(f"  Frame {i+1}: {pattern_desc} (std={analysis['std']:.1f})")
        
        # Recommendations
        self.logger.info("")
        self.logger.info("RECOMMENDATIONS:")
        if noise_frames > silence_frames:
            self.logger.info("  🔧 High noise detected - check Asterisk audio configuration")
            self.logger.info("  🔧 Verify codec settings (PCM vs ULAW)")
            self.logger.info("  🔧 Check sample rate configuration")
        elif silence_frames > speech_frames:
            self.logger.info("  🔧 Mostly silence detected - check microphone/input")
        else:
            self.logger.info("  ✅ Audio content looks normal")
        
        self.logger.info("=" * 70)
        self.logger.info("")
    
    def start(self):
        """Start the content analyzer"""
        self.logger.info("Audio Content Analyzer is running...")
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
            self.logger.info("Audio Content Analyzer stopped by user")
            self.logger.info(f"Total connections analyzed: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Audio Content Analyzer")
    print("====================")
    print("This analyzer examines the actual audio data in frames.")
    print("\nWhat it will show:")
    print("- Audio sample values and patterns")
    print("- Variance and energy analysis")
    print("- Speech vs noise vs silence detection")
    print("- Potential encoding issues")
    print("\nThis will help identify why we're getting static instead of clean audio.\n")
    
    analyzer = AudioContentAnalyzer()
    analyzer.start()


if __name__ == "__main__":
    main() 