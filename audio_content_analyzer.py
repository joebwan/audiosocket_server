#!/usr/bin/env python3
"""
Audio Content Analyzer
Analyzes actual audio content to verify Asterisk is sending real audio, not just silence.
"""

import time
import numpy as np
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class AudioContentAnalyzer:
    """Analyzes actual audio content to detect speech vs silence"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Don't set audio format - use defaults
        self.logger = ColouredLogger("audio_content_analyzer")
        self.logger.info(f"Audio content analyzer started on {host}:{port}")
        self.logger.info("This tool analyzes actual audio content to detect speech vs silence")
        
        # Audio analysis tracking
        self.silence_frames = 0
        self.speech_frames = 0
        self.total_frames = 0
        self.audio_levels = []
        
    def analyze_audio_content(self, audio_data):
        """Analyze audio content to detect speech vs silence"""
        if len(audio_data) == 0:
            return "Empty frame"
        
        try:
            # Convert to numpy array for analysis
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            if len(samples) == 0:
                return "No samples"
            
            # Calculate audio statistics
            min_val = np.min(samples)
            max_val = np.max(samples)
            mean_val = np.mean(samples)
            std_val = np.std(samples)
            rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
            
            # Store audio level for tracking
            self.audio_levels.append(rms)
            if len(self.audio_levels) > 100:  # Keep last 100 frames
                self.audio_levels.pop(0)
            
            # Determine if this is speech or silence
            # Speech typically has higher RMS and standard deviation
            if rms > 100 and std_val > 50:
                self.speech_frames += 1
                return "SPEECH"
            elif rms < 10 and std_val < 5:
                self.silence_frames += 1
                return "SILENCE"
            else:
                return "LOW_LEVEL_AUDIO"
                
        except Exception as e:
            self.logger.error(f"Error analyzing audio content: {e}")
            return "ERROR"
    
    def get_audio_summary(self):
        """Get summary of audio content analysis"""
        if self.total_frames == 0:
            return "No frames analyzed"
        
        speech_percent = (self.speech_frames / self.total_frames) * 100
        silence_percent = (self.silence_frames / self.total_frames) * 100
        
        avg_level = np.mean(self.audio_levels) if self.audio_levels else 0
        max_level = np.max(self.audio_levels) if self.audio_levels else 0
        
        return {
            'total_frames': self.total_frames,
            'speech_frames': self.speech_frames,
            'silence_frames': self.silence_frames,
            'speech_percent': speech_percent,
            'silence_percent': silence_percent,
            'avg_audio_level': avg_level,
            'max_audio_level': max_level
        }
    
    def handle_connection(self, call):
        """Handle connection with detailed audio content analysis"""
        self.logger.info(f"New connection from {call.peer_addr}")
        self.logger.info("Starting audio content analysis...")
        self.logger.info("SPEAK INTO THE PHONE to test audio detection!")
        
        frame_count = 0
        start_time = time.time()
        last_log_time = start_time
        
        # Reset counters
        self.silence_frames = 0
        self.speech_frames = 0
        self.total_frames = 0
        self.audio_levels = []
        
        while call.connected:
            try:
                # Read audio data
                audio_data = call.read()
                frame_size = len(audio_data)
                
                frame_count += 1
                self.total_frames += 1
                
                # Analyze audio content
                content_type = self.analyze_audio_content(audio_data)
                
                # Echo back to maintain connection
                call.write(audio_data)
                
                # Log every 10 frames with content analysis
                if frame_count % 10 == 0:
                    summary = self.get_audio_summary()
                    self.logger.info(f"Frame {frame_count}: {frame_size} bytes, "
                                   f"Content: {content_type}, "
                                   f"Speech: {summary['speech_frames']}, "
                                   f"Silence: {summary['silence_frames']}")
                
                # Log detailed statistics every 5 seconds
                current_time = time.time()
                if current_time - last_log_time >= 5:
                    summary = self.get_audio_summary()
                    self.logger.info("\n" + "="*50)
                    self.logger.info("AUDIO CONTENT SUMMARY")
                    self.logger.info("="*50)
                    self.logger.info(f"Total frames: {summary['total_frames']}")
                    self.logger.info(f"Speech frames: {summary['speech_frames']} ({summary['speech_percent']:.1f}%)")
                    self.logger.info(f"Silence frames: {summary['silence_frames']} ({summary['silence_percent']:.1f}%)")
                    self.logger.info(f"Average audio level: {summary['avg_audio_level']:.1f}")
                    self.logger.info(f"Maximum audio level: {summary['max_audio_level']:.1f}")
                    
                    if summary['speech_frames'] == 0:
                        self.logger.info("⚠️  NO SPEECH DETECTED - Try speaking louder!")
                    elif summary['speech_percent'] > 10:
                        self.logger.info("✅ SPEECH DETECTED - Audio is working!")
                    else:
                        self.logger.info("🔍 LOW SPEECH LEVEL - Try speaking more")
                    
                    self.logger.info("="*50)
                    last_log_time = current_time
                
                # Add small delay
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error in analysis loop: {e}")
                break
        
        # Final summary
        self.logger.info("\n" + "="*60)
        self.logger.info("FINAL AUDIO CONTENT ANALYSIS")
        self.logger.info("="*60)
        
        summary = self.get_audio_summary()
        self.logger.info(f"Total frames analyzed: {summary['total_frames']}")
        self.logger.info(f"Speech frames: {summary['speech_frames']} ({summary['speech_percent']:.1f}%)")
        self.logger.info(f"Silence frames: {summary['silence_frames']} ({summary['silence_percent']:.1f}%)")
        self.logger.info(f"Average audio level: {summary['avg_audio_level']:.1f}")
        self.logger.info(f"Maximum audio level: {summary['max_audio_level']:.1f}")
        
        if summary['speech_frames'] == 0:
            self.logger.info("❌ NO SPEECH DETECTED - Asterisk may not be sending audio")
            self.logger.info("   Check Asterisk configuration and audio routing")
        elif summary['speech_percent'] > 20:
            self.logger.info("✅ GOOD SPEECH DETECTION - Audio is working properly")
        else:
            self.logger.info("⚠️  LOW SPEECH DETECTION - Audio may be too quiet")
        
        self.logger.info("="*60)
        
        # Continue normal echo operation
        self.logger.info("Switching to normal echo mode...")
        while call.connected:
            try:
                audio_data = call.read()
                call.write(audio_data)
                time.sleep(0.001)
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the audio content analyzer"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.logger.info("Analyzer stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Audio Content Analyzer")
    print("=====================")
    print("This tool analyzes actual audio content to verify Asterisk is sending real audio.")
    print("\nWhat it does:")
    print("- Detects speech vs silence")
    print("- Measures audio levels")
    print("- Tracks speech percentage")
    print("- Verifies audio is not just zeros")
    print("\nInstructions:")
    print("1. Connect your Asterisk AudioSocket")
    print("2. Make a call")
    print("3. SPEAK INTO THE PHONE")
    print("4. Watch for speech detection")
    print("\nThis will tell you if Asterisk is actually sending audio or just silence.\n")
    
    analyzer = AudioContentAnalyzer()
    analyzer.start()


if __name__ == "__main__":
    main() 