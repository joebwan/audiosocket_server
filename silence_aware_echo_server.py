#!/usr/bin/env python3
"""
Silence-Aware Echo Server
Properly handles AudioSocket silence frames (0xFF) and audio data.
"""

import time
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class SilenceAwareEchoServer:
    """Echo server that properly handles AudioSocket silence frames"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("silence_echo")
        
        self.logger.info(f"Silence-Aware Echo Server started on {host}:{port}")
        self.logger.info("This server properly handles AudioSocket protocol:")
        self.logger.info("- Detects silence frames (0xFF)")
        self.logger.info("- Echoes silence as silence")
        self.logger.info("- Processes actual audio data normally")
        self.logger.info("")
        
    def is_silence_frame(self, audio_data):
        """Check if frame is a silence frame (all 0xFF)"""
        if len(audio_data) == 0:
            return True
        
        # Check if all bytes are 0xFF (AudioSocket silence indicator)
        return all(b == 0xFF for b in audio_data)
    
    def analyze_frame(self, audio_data):
        """Analyze frame content"""
        if len(audio_data) == 0:
            return "Empty"
        
        if self.is_silence_frame(audio_data):
            return "Silence (0xFF)"
        
        # Analyze actual audio data
        byte_values = [b for b in audio_data]
        unique_bytes = len(set(byte_values))
        zero_bytes = byte_values.count(0)
        zero_percent = (zero_bytes / len(byte_values)) * 100
        
        return {
            'type': 'Audio',
            'size': len(audio_data),
            'unique_bytes': unique_bytes,
            'zero_percent': zero_percent
        }
    
    def handle_connection(self, call):
        """Handle connection with silence awareness"""
        self.logger.info("=" * 50)
        self.logger.info("SILENCE-AWARE ECHO - NEW CONNECTION")
        self.logger.info("=" * 50)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        total_bytes = 0
        start_time = time.time()
        
        # Frame type tracking
        silence_frames = 0
        audio_frames = 0
        
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
                frame_analysis = self.analyze_frame(audio_data)
                
                # Log first 10 frames in detail
                if frame_count <= 10:
                    if isinstance(frame_analysis, dict):
                        self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes - {frame_analysis['type']}")
                        self.logger.info(f"  Unique bytes: {frame_analysis['unique_bytes']}, Zero %: {frame_analysis['zero_percent']:.1f}%")
                    else:
                        self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes - {frame_analysis}")
                
                # Handle frame based on type
                if self.is_silence_frame(audio_data):
                    # Echo silence as silence (all 0xFF)
                    call.write(audio_data)
                    silence_frames += 1
                    
                    if frame_count <= 10:
                        self.logger.info(f"  Echoed as silence")
                else:
                    # Echo actual audio data
                    call.write(audio_data)
                    audio_frames += 1
                    
                    if frame_count <= 10:
                        self.logger.info(f"  Echoed as audio")
                
                # Log every 50 frames
                if frame_count % 50 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    silence_ratio = silence_frames / frame_count if frame_count > 0 else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, FPS: {fps:.1f}")
                    self.logger.info(f"  Silence: {silence_frames} ({silence_ratio:.1%}), Audio: {audio_frames}")
                
                # Minimal delay
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during silence-aware processing: {e}")
        
        # Final statistics
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 50)
        self.logger.info("SILENCE-AWARE ECHO SUMMARY")
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
            self.logger.info(f"Expected FPS: 50.0 (20ms intervals)")
            
            # Check frame rate
            speed_ratio = avg_fps / 50.0 if avg_fps > 0 else 0
            if abs(speed_ratio - 1.0) < 0.1:
                self.logger.info("✅ Frame rate is correct")
            else:
                self.logger.warning(f"⚠️  Frame rate is {speed_ratio:.1f}x expected")
        
        self.logger.info("=" * 50)
        self.logger.info("")
    
    def start(self):
        """Start the silence-aware echo server"""
        self.logger.info("Silence-Aware Echo Server is running...")
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
            self.logger.info("Silence-Aware Echo Server stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Silence-Aware Echo Server")
    print("=========================")
    print("This server properly handles AudioSocket silence frames.")
    print("\nKey features:")
    print("- Detects silence frames (0xFF) from Asterisk")
    print("- Echoes silence as silence")
    print("- Processes actual audio data normally")
    print("- No audio format conversion")
    print("\nThis should fix the higher pitch and static issues.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = SilenceAwareEchoServer()
    server.start()


if __name__ == "__main__":
    main() 