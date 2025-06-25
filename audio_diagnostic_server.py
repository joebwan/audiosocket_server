#!/usr/bin/env python3
"""
Audio Diagnostic Server
Analyzes audio data to identify format, sample rate, and content issues.
"""

import time
import struct
import numpy as np
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class AudioDiagnosticServer:
    """Diagnostic server to analyze audio data and identify issues"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("diagnostic")
        
        self.logger.info(f"Audio Diagnostic Server started on {host}:{port}")
        self.logger.info("This server analyzes audio data to identify issues:")
        self.logger.info("- Audio format analysis")
        self.logger.info("- Sample rate detection")
        self.logger.info("- Audio content analysis")
        self.logger.info("- Echo quality diagnostics")
        self.logger.info("")
        
    def analyze_audio_format(self, audio_data):
        """Analyze the audio format and content"""
        if len(audio_data) == 0:
            return "Empty frame"
        
        # Try to interpret as different formats
        results = {}
        
        # As 16-bit signed integers (most common)
        try:
            if len(audio_data) % 2 == 0:
                samples_16bit = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
                results['16bit_signed'] = {
                    'samples': len(samples_16bit),
                    'min': min(samples_16bit),
                    'max': max(samples_16bit),
                    'mean': np.mean(samples_16bit),
                    'std': np.std(samples_16bit),
                    'rms': np.sqrt(np.mean(np.array(samples_16bit)**2)),
                    'zero_crossings': sum(1 for i in range(1, len(samples_16bit)) if samples_16bit[i-1] * samples_16bit[i] < 0)
                }
        except:
            pass
        
        # As 8-bit unsigned (ULAW-like)
        try:
            samples_8bit = struct.unpack(f'<{len(audio_data)}B', audio_data)
            results['8bit_unsigned'] = {
                'samples': len(samples_8bit),
                'min': min(samples_8bit),
                'max': max(samples_8bit),
                'mean': np.mean(samples_8bit),
                'std': np.std(samples_8bit),
                'rms': np.sqrt(np.mean(np.array(samples_8bit)**2))
            }
        except:
            pass
        
        # As 32-bit floats
        try:
            if len(audio_data) % 4 == 0:
                samples_float = struct.unpack(f'<{len(audio_data)//4}f', audio_data)
                results['32bit_float'] = {
                    'samples': len(samples_float),
                    'min': min(samples_float),
                    'max': max(samples_float),
                    'mean': np.mean(samples_float),
                    'std': np.std(samples_float),
                    'rms': np.sqrt(np.mean(np.array(samples_float)**2))
                }
        except:
            pass
        
        return results
    
    def detect_silence(self, audio_data, threshold=100):
        """Detect if audio frame is silence"""
        if len(audio_data) == 0:
            return True
        
        # Try 16-bit analysis first
        try:
            if len(audio_data) % 2 == 0:
                samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
                rms = np.sqrt(np.mean(np.array(samples)**2))
                return rms < threshold
        except:
            pass
        
        # Fallback to raw bytes
        rms = np.sqrt(np.mean(np.array([b for b in audio_data])**2))
        return rms < threshold
    
    def analyze_audio_content(self, audio_data):
        """Analyze audio content for patterns"""
        if len(audio_data) == 0:
            return "Empty"
        
        # Basic statistics
        byte_values = [b for b in audio_data]
        unique_bytes = len(set(byte_values))
        zero_bytes = byte_values.count(0)
        zero_percent = (zero_bytes / len(byte_values)) * 100
        
        # Pattern analysis
        repeating_pattern = False
        if len(audio_data) >= 4:
            # Check for repeating patterns
            for pattern_len in [2, 4, 8]:
                if len(audio_data) >= pattern_len * 2:
                    pattern = audio_data[:pattern_len]
                    repeats = audio_data.count(pattern)
                    if repeats > 1:
                        repeating_pattern = True
                        break
        
        return {
            'size': len(audio_data),
            'unique_bytes': unique_bytes,
            'zero_bytes': zero_bytes,
            'zero_percent': zero_percent,
            'repeating_pattern': repeating_pattern,
            'is_silence': self.detect_silence(audio_data)
        }
    
    def handle_connection(self, call):
        """Handle connection with detailed audio analysis"""
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
        start_time = time.time()
        
        # Audio analysis tracking
        format_analysis = {}
        silence_frames = 0
        speech_frames = 0
        
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
                
                # Analyze audio content
                content = self.analyze_audio_content(audio_data)
                if content['is_silence']:
                    silence_frames += 1
                else:
                    speech_frames += 1
                
                # Detailed analysis for first 5 frames
                if frame_count <= 5:
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes")
                    self.logger.info(f"  Content: {content}")
                    
                    # Format analysis
                    format_info = self.analyze_audio_format(audio_data)
                    if isinstance(format_info, dict):
                        for fmt, stats in format_info.items():
                            self.logger.info(f"  {fmt}: samples={stats['samples']}, "
                                           f"min={stats['min']}, max={stats['max']}, "
                                           f"mean={stats['mean']:.1f}, rms={stats['rms']:.1f}")
                            if 'zero_crossings' in stats:
                                self.logger.info(f"    zero_crossings={stats['zero_crossings']}")
                    else:
                        self.logger.info(f"  Format: {format_info}")
                    self.logger.info("")
                
                # Echo the audio back
                call.write(audio_data)
                
                # Log every 50 frames
                if frame_count % 50 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    silence_ratio = silence_frames / frame_count if frame_count > 0 else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, "
                                   f"FPS: {fps:.1f}, Silence: {silence_ratio:.1%}")
                
                # Minimal delay
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during diagnostic: {e}")
        
        # Final statistics
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("AUDIO DIAGNOSTIC SUMMARY")
        self.logger.info("=" * 60)
        
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total bytes: {total_bytes}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            avg_fps = frame_count / total_time if total_time > 0 else 0
            avg_frame_size = total_bytes / frame_count if frame_count > 0 else 0
            silence_ratio = silence_frames / frame_count if frame_count > 0 else 0
            
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Average frame size: {avg_frame_size:.1f} bytes")
            self.logger.info(f"Silence frames: {silence_frames} ({silence_ratio:.1%})")
            self.logger.info(f"Speech frames: {speech_frames} ({1-silence_ratio:.1%})")
            self.logger.info(f"Expected FPS: 50.0 (20ms intervals)")
            
            # Check frame rate
            speed_ratio = avg_fps / 50.0 if avg_fps > 0 else 0
            if abs(speed_ratio - 1.0) < 0.1:
                self.logger.info("✅ Frame rate is correct")
            else:
                self.logger.warning(f"⚠️  Frame rate is {speed_ratio:.1f}x expected")
        
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
                # Accept connections
                call = self.audiosocket.listen()
                connection_count += 1
                
                self.logger.info(f"Connection #{connection_count} accepted")
                
                # Handle connection
                self.handle_connection(call)
                
        except KeyboardInterrupt:
            self.logger.info("")
            self.logger.info("Audio Diagnostic Server stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Audio Diagnostic Server")
    print("======================")
    print("This server analyzes audio data to identify format and content issues.")
    print("\nKey features:")
    print("- Audio format analysis (16-bit, 8-bit, 32-bit float)")
    print("- Sample rate and frame rate analysis")
    print("- Silence vs speech detection")
    print("- Audio content pattern analysis")
    print("- Echo quality diagnostics")
    print("\nThis will help identify the source of audio quality issues.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = AudioDiagnosticServer()
    server.start()


if __name__ == "__main__":
    main() 