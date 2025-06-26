#!/usr/bin/env python3
"""
PCM Echo Server
Properly handles 16-bit PCM (SLIN) audio from Asterisk.
"""

import time
import struct
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class PCMEchoServer:
    """Echo server that properly handles 16-bit PCM audio"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("pcm_echo")
        
        self.logger.info(f"PCM Echo Server started on {host}:{port}")
        self.logger.info("This server handles 16-bit PCM (SLIN) audio:")
        self.logger.info("- Expects 16-bit signed linear PCM")
        self.logger.info("- 8kHz sample rate")
        self.logger.info("- Mono channel")
        self.logger.info("- 160 bytes per frame (80 samples)")
        self.logger.info("")
        
    def analyze_pcm_frame(self, audio_data):
        """Analyze 16-bit PCM frame"""
        if len(audio_data) == 0:
            return "Empty"
        
        if len(audio_data) % 2 != 0:
            return f"Invalid size: {len(audio_data)} bytes (not even)"
        
        try:
            # Unpack as 16-bit signed integers (little-endian)
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            
            # Basic statistics
            min_val = min(samples)
            max_val = max(samples)
            mean_val = sum(samples) / len(samples)
            
            # Calculate RMS
            rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
            
            # Zero crossing rate
            zero_crossings = sum(1 for i in range(1, len(samples)) if samples[i-1] * samples[i] < 0)
            
            # Check for clipping
            clipping = abs(max_val) > 32000 or abs(min_val) > 32000
            
            # Check for silence
            is_silence = rms < 100
            
            return {
                'format': '16-bit PCM',
                'samples': len(samples),
                'min': min_val,
                'max': max_val,
                'mean': mean_val,
                'rms': rms,
                'zero_crossings': zero_crossings,
                'clipping': clipping,
                'is_silence': is_silence
            }
        except Exception as e:
            return f"Error analyzing PCM: {e}"
    
    def detect_silence(self, audio_data, threshold=100):
        """Detect if PCM frame is silence"""
        if len(audio_data) == 0:
            return True
        
        if len(audio_data) % 2 != 0:
            return True
        
        try:
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
            return rms < threshold
        except:
            return True
    
    def handle_connection(self, call):
        """Handle connection with PCM processing"""
        self.logger.info("=" * 50)
        self.logger.info("PCM ECHO - NEW CONNECTION")
        self.logger.info("=" * 50)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        total_bytes = 0
        start_time = time.time()
        
        # Audio tracking
        silence_frames = 0
        audio_frames = 0
        clipping_frames = 0
        
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
                analysis = self.analyze_pcm_frame(audio_data)
                
                # Track frame types
                if isinstance(analysis, dict):
                    if analysis['is_silence']:
                        silence_frames += 1
                    else:
                        audio_frames += 1
                    
                    if analysis['clipping']:
                        clipping_frames += 1
                
                # Log first 10 frames in detail
                if frame_count <= 10:
                    if isinstance(analysis, dict):
                        self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes")
                        self.logger.info(f"  PCM: {analysis['samples']} samples, "
                                       f"range=[{analysis['min']}, {analysis['max']}], "
                                       f"rms={analysis['rms']:.1f}")
                        self.logger.info(f"  Zero crossings: {analysis['zero_crossings']}, "
                                       f"Silence: {analysis['is_silence']}, "
                                       f"Clipping: {analysis['clipping']}")
                    else:
                        self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes - {analysis}")
                    self.logger.info("")
                
                # Echo the PCM frame directly (no conversion needed)
                call.write(audio_data)
                
                # Log every 50 frames
                if frame_count % 50 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    silence_ratio = silence_frames / frame_count if frame_count > 0 else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, FPS: {fps:.1f}")
                    self.logger.info(f"  Silence: {silence_frames} ({silence_ratio:.1%}), "
                                   f"Audio: {audio_frames}, Clipping: {clipping_frames}")
                
                # Minimal delay
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during PCM processing: {e}")
        
        # Final statistics
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 50)
        self.logger.info("PCM ECHO SUMMARY")
        self.logger.info("=" * 50)
        
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
            self.logger.info(f"Audio frames: {audio_frames} ({1-silence_ratio:.1%})")
            self.logger.info(f"Clipping frames: {clipping_frames}")
            self.logger.info(f"Expected FPS: 50.0 (20ms intervals)")
            
            # Check frame rate
            speed_ratio = avg_fps / 50.0 if avg_fps > 0 else 0
            if abs(speed_ratio - 1.0) < 0.1:
                self.logger.info("✅ Frame rate is correct")
            else:
                self.logger.warning(f"⚠️  Frame rate is {speed_ratio:.1f}x expected")
            
            # Check frame size
            if abs(avg_frame_size - 160.0) < 1.0:
                self.logger.info("✅ Frame size is correct (160 bytes = 80 samples × 2 bytes)")
            else:
                self.logger.warning(f"⚠️  Unexpected frame size: {avg_frame_size:.1f} bytes")
        
        self.logger.info("=" * 50)
        self.logger.info("")
    
    def start(self):
        """Start the PCM echo server"""
        self.logger.info("PCM Echo Server is running...")
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
            self.logger.info("PCM Echo Server stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("PCM Echo Server")
    print("==============")
    print("This server properly handles 16-bit PCM (SLIN) audio from Asterisk.")
    print("\nKey features:")
    print("- Expects 16-bit signed linear PCM")
    print("- 8kHz sample rate, mono channel")
    print("- 160 bytes per frame (80 samples)")
    print("- No audio format conversion")
    print("\nThis should fix the higher pitch and static issues.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = PCMEchoServer()
    server.start()


if __name__ == "__main__":
    main() 