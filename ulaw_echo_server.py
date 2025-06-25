#!/usr/bin/env python3
"""
ULAW Echo Server
Properly handles ULAW encoded audio from Asterisk.
"""

import time
import audioop
from audiosocket_fixed import Audiosocket
from mylogging import ColouredLogger


class ULAWEchoServer:
    """Echo server that properly handles ULAW encoded audio"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("ulaw_echo")
        
        self.logger.info(f"ULAW Echo Server started on {host}:{port}")
        self.logger.info("This server properly handles ULAW encoded audio:")
        self.logger.info("- Decodes ULAW to PCM for processing")
        self.logger.info("- Re-encodes PCM to ULAW for transmission")
        self.logger.info("- Maintains proper audio format compatibility")
        self.logger.info("")
        
    def ulaw_to_pcm(self, ulaw_data):
        """Convert ULAW encoded data to PCM"""
        try:
            # Convert ULAW to 16-bit PCM
            pcm_data = audioop.ulaw2lin(ulaw_data, 2)  # 2 = 16-bit
            return pcm_data
        except Exception as e:
            self.logger.error(f"ULAW to PCM conversion failed: {e}")
            return ulaw_data  # Return original if conversion fails
    
    def pcm_to_ulaw(self, pcm_data):
        """Convert PCM data to ULAW"""
        try:
            # Convert 16-bit PCM to ULAW
            ulaw_data = audioop.lin2ulaw(pcm_data, 2)  # 2 = 16-bit
            return ulaw_data
        except Exception as e:
            self.logger.error(f"PCM to ULAW conversion failed: {e}")
            return pcm_data  # Return original if conversion fails
    
    def analyze_audio_format(self, audio_data):
        """Quick analysis to detect ULAW vs PCM"""
        if len(audio_data) == 0:
            return "Empty"
        
        # Check if it looks like ULAW (mostly 0xFF values)
        byte_values = [b for b in audio_data]
        unique_bytes = len(set(byte_values))
        ff_count = byte_values.count(0xFF)
        ff_percent = (ff_count / len(byte_values)) * 100
        
        if ff_percent > 80:
            return "ULAW (likely)"
        elif unique_bytes > 50:
            return "PCM (likely)"
        else:
            return "Unknown"
    
    def handle_connection(self, call):
        """Handle connection with ULAW processing"""
        self.logger.info("=" * 50)
        self.logger.info("ULAW ECHO - NEW CONNECTION")
        self.logger.info("=" * 50)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info("")
        
        # Statistics tracking
        frame_count = 0
        total_bytes = 0
        start_time = time.time()
        
        # Audio processing tracking
        ulaw_frames = 0
        pcm_frames = 0
        
        # Format detection
        format_detected = False
        is_ulaw = False
        
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
                
                # Analyze format for first few frames
                if frame_count <= 3:
                    format_type = self.analyze_audio_format(audio_data)
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes - {format_type}")
                    
                    # Detect format based on first few frames
                    if "ULAW" in format_type:
                        is_ulaw = True
                        format_detected = True
                        self.logger.info("  Format detected: ULAW - will process all frames as ULAW")
                    elif "PCM" in format_type:
                        is_ulaw = False
                        format_detected = True
                        self.logger.info("  Format detected: PCM - will process all frames as PCM")
                
                # Process audio based on detected format
                if not format_detected and frame_count <= 3:
                    # Still detecting format
                    format_type = self.analyze_audio_format(audio_data)
                    if "ULAW" in format_type:
                        # Convert ULAW to PCM for processing
                        pcm_data = self.ulaw_to_pcm(audio_data)
                        ulaw_frames += 1
                        
                        # Echo: convert back to ULAW
                        echo_data = self.pcm_to_ulaw(pcm_data)
                        call.write(echo_data)
                        
                        self.logger.info(f"  Processed as ULAW: {len(audio_data)} -> {len(pcm_data)} -> {len(echo_data)} bytes")
                    else:
                        # Assume PCM, echo directly
                        call.write(audio_data)
                        pcm_frames += 1
                        
                        self.logger.info(f"  Processed as PCM: {len(audio_data)} bytes")
                else:
                    # Format detected, process accordingly
                    if is_ulaw:
                        # ULAW processing
                        pcm_data = self.ulaw_to_pcm(audio_data)
                        echo_data = self.pcm_to_ulaw(pcm_data)
                        call.write(echo_data)
                        ulaw_frames += 1
                    else:
                        # PCM processing
                        call.write(audio_data)
                        pcm_frames += 1
                
                # Log every 50 frames
                if frame_count % 50 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    self.logger.info(f"Frame {frame_count}: {len(audio_data)} bytes, FPS: {fps:.1f}")
                    if format_detected:
                        format_name = "ULAW" if is_ulaw else "PCM"
                        self.logger.info(f"  Processing as: {format_name}")
                    self.logger.info(f"  ULAW frames: {ulaw_frames}, PCM frames: {pcm_frames}")
                
                # Minimal delay
                time.sleep(0.001)
                
        except Exception as e:
            self.logger.error(f"Error during ULAW processing: {e}")
        
        # Final statistics
        total_time = time.time() - start_time
        self.logger.info("")
        self.logger.info("=" * 50)
        self.logger.info("ULAW ECHO SUMMARY")
        self.logger.info("=" * 50)
        
        self.logger.info(f"Total frames: {frame_count}")
        self.logger.info(f"Total bytes: {total_bytes}")
        self.logger.info(f"Total time: {total_time:.3f}s")
        
        if frame_count > 0:
            avg_fps = frame_count / total_time if total_time > 0 else 0
            avg_frame_size = total_bytes / frame_count if frame_count > 0 else 0
            
            self.logger.info(f"Average FPS: {avg_fps:.1f}")
            self.logger.info(f"Average frame size: {avg_frame_size:.1f} bytes")
            self.logger.info(f"ULAW frames: {ulaw_frames}")
            self.logger.info(f"PCM frames: {pcm_frames}")
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
        """Start the ULAW echo server"""
        self.logger.info("ULAW Echo Server is running...")
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
            self.logger.info("ULAW Echo Server stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("ULAW Echo Server")
    print("================")
    print("This server properly handles ULAW encoded audio from Asterisk.")
    print("\nKey features:")
    print("- Detects ULAW vs PCM audio format")
    print("- Decodes ULAW to PCM for processing")
    print("- Re-encodes PCM to ULAW for transmission")
    print("- Maintains proper audio format compatibility")
    print("\nThis should fix the higher pitch and static issues.")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = ULAWEchoServer()
    server.start()


if __name__ == "__main__":
    main() 