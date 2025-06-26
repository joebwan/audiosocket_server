"""
VoiceBot Feature 1: Audio Playback System

This module provides audio playback functionality for the AudioSocket server.
All audio must conform to the Asterisk AudioSocket format:
- 16-bit signed linear PCM
- 8kHz sample rate
- Mono channel
- WAV format
"""

import os
import wave
import struct
from typing import Tuple, Optional


class WavFileLoader:
    """Load and validate WAV files for AudioSocket playback."""
    
    # Asterisk AudioSocket format requirements
    REQUIRED_SAMPLE_RATE = 8000
    REQUIRED_CHANNELS = 1
    REQUIRED_SAMPLE_WIDTH = 2  # 16-bit
    
    def __init__(self):
        """Initialize the WAV file loader."""
        pass
    
    def validate_wav_format(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a WAV file conforms to Asterisk AudioSocket format.
        
        Args:
            filename: Path to the WAV file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not os.path.exists(filename):
                return False, f"File does not exist: {filename}"
            
            # Try to open as WAV file
            with wave.open(filename, 'rb') as wav_file:
                # Check sample rate
                if wav_file.getframerate() != self.REQUIRED_SAMPLE_RATE:
                    return False, f"Sample rate must be {self.REQUIRED_SAMPLE_RATE} Hz, got {wav_file.getframerate()} Hz"
                
                # Check number of channels
                if wav_file.getnchannels() != self.REQUIRED_CHANNELS:
                    return False, f"Must be {self.REQUIRED_CHANNELS} channel (mono), got {wav_file.getnchannels()} channels"
                
                # Check sample width
                if wav_file.getsampwidth() != self.REQUIRED_SAMPLE_WIDTH:
                    return False, f"Sample width must be {self.REQUIRED_SAMPLE_WIDTH} bytes (16-bit), got {wav_file.getsampwidth()} bytes"
                
                return True, None
                
        except wave.Error:
            return False, "File is not a valid WAV file"
        except Exception as e:
            return False, f"Error validating WAV file: {str(e)}"
    
    def load_wav_file(self, filename: str) -> Tuple[bytes, int, int, int]:
        """
        Load a WAV file and return its audio data and format information.
        
        Args:
            filename: Path to the WAV file to load
            
        Returns:
            Tuple of (audio_data, sample_rate, channels, sample_width)
            
        Raises:
            ValueError: If the WAV file doesn't conform to Asterisk format
        """
        # Validate format first
        is_valid, error_msg = self.validate_wav_format(filename)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Load the WAV file
        with wave.open(filename, 'rb') as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            
            # Read all audio data
            audio_data = wav_file.readframes(wav_file.getnframes())
            
            return audio_data, sample_rate, channels, sample_width 


class WavAudioStreamer:
    """
    Streams audio from a validated WAV file as AudioSocket protocol frames.
    Each frame: 3-byte header + 320-byte payload (zero-padded if needed).
    """
    FRAME_SIZE = 320  # bytes per frame (160 samples * 2 bytes)
    KIND = 0x10

    def __init__(self, filename: str):
        loader = WavFileLoader()
        is_valid, error_msg = loader.validate_wav_format(filename)
        if not is_valid:
            raise ValueError(error_msg)
        self.filename = filename
        with wave.open(filename, 'rb') as wav_file:
            self.audio_data = wav_file.readframes(wav_file.getnframes())
        self.offset = 0
        self.total_len = len(self.audio_data)

    def __iter__(self):
        return self

    def __next__(self):
        if self.offset >= self.total_len:
            raise StopIteration
        # Get up to FRAME_SIZE bytes
        chunk = self.audio_data[self.offset:self.offset + self.FRAME_SIZE]
        self.offset += self.FRAME_SIZE
        # Pad if needed
        if len(chunk) < self.FRAME_SIZE:
            chunk += b'\x00' * (self.FRAME_SIZE - len(chunk))
        # Header: kind (0x10), length (big-endian 320)
        header = bytes([self.KIND, 0x01, 0x40])
        return header + chunk

    def __len__(self):
        # Number of frames (including partial final frame)
        n = (self.total_len + self.FRAME_SIZE - 1) // self.FRAME_SIZE
        return n

    def __call__(self):
        # For compatibility: allow calling to get an iterator
        return iter(self)

    def __next_frame__(self):
        # For compatibility with some test runners
        return self.__next__()

    def __bool__(self):
        return self.total_len > 0 