#!/usr/bin/env python3
"""
Format Mismatch Diagnostic
Identifies exact audio format mismatches causing choppy audio and delays.
"""

import time
import numpy as np
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class FormatMismatchDiagnostic:
    """Diagnoses audio format mismatches"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Don't set audio format - use defaults
        self.logger = ColouredLogger("format_diagnostic")
        self.logger.info(f"Format mismatch diagnostic started on {host}:{port}")
        
        # Track frame sizes and timing
        self.incoming_frame_sizes = []
        self.outgoing_frame_sizes = []
        self.frame_timings = []
        
    def generate_adaptive_tone(self, target_frame_size):
        """Generate a tone that matches the target frame size"""
        # Calculate samples needed for the target frame size
        # Assuming 16-bit PCM (2 bytes per sample)
        samples_needed = target_frame_size // 2
        
        # Generate a simple sine wave
        frequency = 1000  # 1kHz
        sample_rate = 8000  # 8kHz (we'll adjust if needed)
        
        # Calculate duration based on samples needed
        duration = samples_needed / sample_rate
        
        # Generate the tone
        t = np.linspace(0, duration, samples_needed, endpoint=False)
        tone = np.sin(2 * np.pi * frequency * t) * 0.3  # Lower volume
        tone = (tone * 32767).astype(np.int16)
        
        return tone.tobytes()
    
    def handle_connection(self, call):
        """Handle connection with format mismatch diagnosis"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting format mismatch diagnosis...")
        
        frame_count = 0
        start_time = time.time()
        last_frame_time = start_time
        
        # Phase 1: Analyze incoming format
        analysis_phase = True
        analysis_frames = 50
        
        while call.connected and analysis_phase:
            try:
                # Read incoming audio
                audio_data = call.read()
                current_time = time.time()
                
                frame_size = len(audio_data)
                self.incoming_frame_sizes.append(frame_size)
                
                frame_count += 1
                
                # Track timing
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    self.frame_timings.append(interval)
                last_frame_time = current_time
                
                # Echo back to maintain connection
                call.write(audio_data)
                
                # Log frame info
                if frame_count % 10 == 0:
                    self.logger.info(f"Frame {frame_count}: {frame_size} bytes")
                
                # Complete analysis phase
                if frame_count >= analysis_frames:
                    analysis_phase = False
                    self.logger.info("Analysis phase complete")
                
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error in analysis phase: {e}")
                break
        
        # Analyze incoming format
        if self.incoming_frame_sizes:
            unique_sizes = set(self.incoming_frame_sizes)
            most_common_size = max(set(self.incoming_frame_sizes), key=self.incoming_frame_sizes.count)
            
            self.logger.info("\n" + "="*50)
            self.logger.info("INCOMING AUDIO FORMAT ANALYSIS")
            self.logger.info("="*50)
            self.logger.info(f"Frame sizes observed: {unique_sizes}")
            self.logger.info(f"Most common frame size: {most_common_size} bytes")
            
            if self.frame_timings:
                avg_interval = sum(self.frame_timings) / len(self.frame_timings)
                self.logger.info(f"Average frame interval: {avg_interval*1000:.1f}ms")
            
            # Determine likely format
            if most_common_size == 320:
                self.logger.info("Likely format: 8kHz, mono, 16-bit PCM, 20ms frames")
            elif most_common_size == 640:
                self.logger.info("Likely format: 16kHz, mono, 16-bit PCM, 20ms frames")
            elif most_common_size == 1280:
                self.logger.info("Likely format: 8kHz, stereo, 16-bit PCM, 40ms frames")
            else:
                self.logger.info(f"Unknown format: {most_common_size} bytes")
            
            self.logger.info("="*50)
        
        # Phase 2: Test adaptive tone generation
        self.logger.info("\nStarting adaptive tone test...")
        self.logger.info("You should hear tones that match the detected format")
        
        tone_phase = 0
        tone_start_time = time.time()
        
        while call.connected:
            try:
                # Read incoming audio
                audio_data = call.read()
                frame_size = len(audio_data)
                
                frame_count += 1
                current_time = time.time()
                
                # Generate adaptive tone
                if tone_phase < 4:
                    elapsed = current_time - tone_start_time
                    
                    if elapsed >= 3:  # Switch tone every 3 seconds
                        tone_phase += 1
                        tone_start_time = current_time
                        self.logger.info(f"Switching to tone phase {tone_phase}")
                    
                    # Generate tone matching the detected frame size
                    tone_data = self.generate_adaptive_tone(frame_size)
                    self.outgoing_frame_sizes.append(len(tone_data))
                    
                    # Send the tone
                    call.write(tone_data)
                    
                    # Log every 25 frames
                    if frame_count % 25 == 0:
                        self.logger.info(f"Frame {frame_count}: Sending {len(tone_data)} byte tone")
                
                # Phase 3: Echo mode
                else:
                    # Echo the incoming audio
                    call.write(audio_data)
                    
                    # Log every 50 frames
                    if frame_count % 50 == 0:
                        self.logger.info(f"Frame {frame_count}: Echo mode - {frame_size} bytes")
                
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error in tone phase: {e}")
                break
        
        # Final analysis
        self.logger.info("\n" + "="*60)
        self.logger.info("FORMAT MISMATCH DIAGNOSIS COMPLETE")
        self.logger.info("="*60)
        
        if self.incoming_frame_sizes and self.outgoing_frame_sizes:
            avg_incoming = sum(self.incoming_frame_sizes) / len(self.incoming_frame_sizes)
            avg_outgoing = sum(self.outgoing_frame_sizes) / len(self.outgoing_frame_sizes)
            
            self.logger.info(f"Average incoming frame size: {avg_incoming:.1f} bytes")
            self.logger.info(f"Average outgoing frame size: {avg_outgoing:.1f} bytes")
            
            if abs(avg_incoming - avg_outgoing) < 10:
                self.logger.info("✅ Frame sizes match - format should be compatible")
            else:
                self.logger.info("⚠️  Frame size mismatch - this may cause issues")
        
        if self.frame_timings:
            avg_interval = sum(self.frame_timings) / len(self.frame_timings)
            self.logger.info(f"Average frame interval: {avg_interval*1000:.1f}ms")
            
            if avg_interval > 0.05:
                self.logger.info("⚠️  Slow frame timing - may cause delays")
            else:
                self.logger.info("✅ Good frame timing")
        
        self.logger.info("="*60)
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the format mismatch diagnostic"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Diagnostic stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Format Mismatch Diagnostic")
    print("==========================")
    print("This tool identifies exact audio format mismatches.")
    print("\nWhat it does:")
    print("1. Analyzes incoming audio format")
    print("2. Generates tones matching the detected format")
    print("3. Tests echo with proper frame sizes")
    print("4. Identifies timing and format issues")
    print("\nThis should eliminate choppy tones and delays.\n")
    
    diagnostic = FormatMismatchDiagnostic()
    diagnostic.start()


if __name__ == "__main__":
    main() 