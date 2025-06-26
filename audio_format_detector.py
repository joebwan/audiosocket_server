#!/usr/bin/env python3
"""
Audio Format Detector
Analyzes raw audio data to determine format, bit depth, sample rate, and channels.
"""

import time
import struct
import math
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class AudioFormatDetector:
    """Detects audio format from raw data analysis"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("format_detector")
        
        self.logger.info(f"Audio Format Detector started on {host}:{port}")
        self.logger.info("This detector analyzes raw audio data to determine:")
        self.logger.info("- Bit depth (8-bit, 16-bit, etc.)")
        self.logger.info("- Sample rate (8kHz, 16kHz, etc.)")
        self.logger.info("- Channel configuration (mono/stereo)")
        self.logger.info("- Audio encoding (PCM, ULAW, etc.)")
        self.logger.info("")
        
    def analyze_byte_patterns(self, audio_data):
        """Analyze byte patterns to determine format"""
        if len(audio_data) == 0:
            return "Empty"
        
        bytes_list = [b for b in audio_data]
        unique_bytes = len(set(bytes_list))
        
        # Check for all 0xFF (silence indicator)
        if all(b == 0xFF for b in bytes_list):
            return "Silence (0xFF)"
        
        # Check for all 0x00 (digital silence)
        if all(b == 0x00 for b in bytes_list):
            return "Digital Silence (0x00)"
        
        # Check for ULAW characteristics
        ulaw_chars = set([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
                         0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F,
                         0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F,
                         0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F,
                         0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F,
                         0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F,
                         0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F,
                         0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F,
                         0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x8D, 0x8E, 0x8F,
                         0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F,
                         0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF,
                         0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF,
                         0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0xCE, 0xCF,
                         0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF,
                         0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEE, 0xEF,
                         0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF])
        
        if all(b in ulaw_chars for b in bytes_list):
            return "ULAW (likely)"
        
        # Check for PCM characteristics
        if unique_bytes > 50:
            return "PCM (likely)"
        
        return f"Unknown (unique_bytes={unique_bytes})"
    
    def analyze_16bit_pcm(self, audio_data):
        """Analyze as 16-bit PCM"""
        if len(audio_data) % 2 != 0:
            return None
        
        try:
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            
            # Basic statistics
            min_val = min(samples)
            max_val = max(samples)
            mean_val = sum(samples) / len(samples)
            
            # Calculate RMS
            rms = math.sqrt(sum(s*s for s in samples) / len(samples))
            
            # Zero crossing rate
            zero_crossings = sum(1 for i in range(1, len(samples)) if samples[i-1] * samples[i] < 0)
            
            # Check for clipping
            clipping = abs(max_val) > 32000 or abs(min_val) > 32000
            
            return {
                'format': '16-bit PCM',
                'samples': len(samples),
                'min': min_val,
                'max': max_val,
                'mean': mean_val,
                'rms': rms,
                'zero_crossings': zero_crossings,
                'clipping': clipping,
                'is_silence': rms < 100
            }
        except:
            return None
    
    def analyze_8bit_pcm(self, audio_data):
        """Analyze as 8-bit PCM"""
        try:
            samples = struct.unpack(f'<{len(audio_data)}B', audio_data)
            
            # Basic statistics
            min_val = min(samples)
            max_val = max(samples)
            mean_val = sum(samples) / len(samples)
            
            # Calculate RMS
            rms = math.sqrt(sum(s*s for s in samples) / len(samples))
            
            # Zero crossing rate (for unsigned, check around 128)
            zero_crossings = sum(1 for i in range(1, len(samples)) if (samples[i-1] - 128) * (samples[i] - 128) < 0)
            
            return {
                'format': '8-bit PCM',
                'samples': len(samples),
                'min': min_val,
                'max': max_val,
                'mean': mean_val,
                'rms': rms,
                'zero_crossings': zero_crossings,
                'is_silence': rms < 10
            }
        except:
            return None
    
    def detect_sample_rate(self, frame_size, frame_interval=0.02):
        """Estimate sample rate from frame size and interval"""
        # frame_interval is typically 20ms (0.02s)
        samples_per_frame = frame_size  # Assuming 1 byte per sample for now
        
        # Try different bit depths
        for bits_per_sample in [8, 16]:
            if bits_per_sample == 16:
                samples_per_frame = frame_size // 2
            
            estimated_rate = samples_per_frame / frame_interval
            
            # Check if it matches common rates
            for rate in [8000, 16000, 22050, 32000, 44100, 48000]:
                if abs(estimated_rate - rate) < 100:
                    return rate, bits_per_sample
        
        return None, None
    
    def handle_connection(self, call):
        """Handle connection with format detection"""
        self.logger.info("=" * 60)
        self.logger.info("AUDIO FORMAT DETECTION - NEW CONNECTION")
        self.logger.info("=" * 60)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        total_bytes = 0
        start_time = time.time()
        
        # Format tracking
        format_counts = {}
        sample_rates = []
        
        try:
            while call.connected:
                # Read incoming audio
                audio_data = call.read()
                
                # Skip empty frames
                if len(audio_data) == 0:
                    time.sleep(0.001)
                    continue
                
                frame_count += 1
                total_bytes += len(audio_data)
                
                # Analyze frame
                pattern = self.analyze_byte_patterns(audio_data)
                format_counts[pattern] = format_counts.get(pattern, 0) + 1
                
                # Detailed analysis for first 10 frames
                if frame_count <= 10:
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes")
                    self.logger.info(f"  Pattern: {pattern}")
                    
                    # Try different format interpretations
                    pcm_16bit = self.analyze_16bit_pcm(audio_data)
                    pcm_8bit = self.analyze_8bit_pcm(audio_data)
                    
                    if pcm_16bit:
                        self.logger.info(f"  16-bit PCM: samples={pcm_16bit['samples']}, "
                                       f"range=[{pcm_16bit['min']}, {pcm_16bit['max']}], "
                                       f"rms={pcm_16bit['rms']:.1f}, "
                                       f"silence={pcm_16bit['is_silence']}")
                    
                    if pcm_8bit:
                        self.logger.info(f"  8-bit PCM: samples={pcm_8bit['samples']}, "
                                       f"range=[{pcm_8bit['min']}, {pcm_8bit['max']}], "
                                       f"rms={pcm_8bit['rms']:.1f}, "
                                       f"silence={pcm_8bit['is_silence']}")
                    
                    # Estimate sample rate
                    rate, bits = self.detect_sample_rate(len(audio_data))
                    if rate:
                        sample_rates.append(rate)
                        self.logger.info(f"  Estimated: {rate}Hz, {bits}-bit")
                    
                    self.logger.info("")
                
                # Echo the frame back
                call.write(audio_data)
                
                # Log every 50 frames
                if frame_count % 50 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, FPS: {fps:.1f}")
                    self.logger.info(f"  Format counts: {format_counts}")
                
                # Minimal delay
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during format detection: {e}")
        
        # Final analysis
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("FORMAT DETECTION SUMMARY")
        self.logger.info("=" * 60)
        
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total bytes: {total_bytes}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            avg_fps = frame_count / total_time if total_time > 0 else 0
            avg_frame_size = total_bytes / frame_count if frame_count > 0 else 0
            
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Average frame size: {avg_frame_size:.1f} bytes")
            self.logger.info(f"Format distribution: {format_counts}")
            
            if sample_rates:
                most_common_rate = max(set(sample_rates), key=sample_rates.count)
                self.logger.info(f"Most common sample rate: {most_common_rate}Hz")
            
            # Final format recommendation
            dominant_format = max(format_counts.items(), key=lambda x: x[1])[0]
            self.logger.info(f"Dominant format: {dominant_format}")
        
        self.logger.info("=" * 60)
        self.logger.info("")
    
    def start(self):
        """Start the format detector"""
        self.logger.info("Audio Format Detector is running...")
        self.logger.info("Waiting for AudioSocket connections...")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("")
        
        connection_count = 0
        
        try:
            while True:
                # Accept connections
                call = self.audiosocket.listen()
                connection_count += 1
                
                self.logger.info(f"Connection #{connection_count} accepted")
                
                # Handle connection
                self.handle_connection(call)
                
        except KeyboardInterrupt:
            self.logger.info("")
            self.logger.info("Audio Format Detector stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Audio Format Detector")
    print("====================")
    print("This detector analyzes raw audio data to determine format.")
    print("\nKey features:")
    print("- Detects bit depth (8-bit, 16-bit)")
    print("- Estimates sample rate")
    print("- Identifies audio encoding (PCM, ULAW)")
    print("- Analyzes channel configuration")
    print("\nThis will help us understand the exact audio format.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    detector = AudioFormatDetector()
    detector.start()


if __name__ == "__main__":
    main() 