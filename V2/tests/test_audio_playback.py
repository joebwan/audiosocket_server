"""
Tests for VoiceBot Feature 1: Audio Playback System

This module tests the audio playback functionality, starting with WAV file loading
and validation. All audio must conform to the Asterisk AudioSocket format:
- 16-bit signed linear PCM
- 8kHz sample rate
- Mono channel
- WAV format
"""

import unittest
import tempfile
import os
import wave
import struct
from unittest.mock import patch, mock_open
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audio_playback import WavFileLoader


class TestWavFileLoader(unittest.TestCase):
    """Test WAV file loading and validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loader = WavFileLoader()
        
    def test_loader_initialization(self):
        """Test that WavFileLoader can be initialized."""
        loader = WavFileLoader()
        self.assertIsNotNone(loader)
        
    def test_validate_wav_format_asterisk_compatible(self):
        """Test that WAV file with Asterisk-compatible format is valid."""
        # Create a temporary WAV file with Asterisk-compatible format
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
            
        try:
            # Create WAV file with Asterisk-compatible format
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit (2 bytes)
                wav_file.setframerate(8000)  # 8kHz
                
                # Write some test audio data (1 second of silence)
                audio_data = struct.pack('<8000h', *([0] * 8000))  # 8000 samples of 0
                wav_file.writeframes(audio_data)
            
            # Test validation
            is_valid, error_msg = self.loader.validate_wav_format(temp_filename)
            self.assertTrue(is_valid, f"WAV file should be valid: {error_msg}")
            self.assertIsNone(error_msg)
            
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    def test_validate_wav_format_wrong_sample_rate(self):
        """Test that WAV file with wrong sample rate is rejected."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
            
        try:
            # Create WAV file with wrong sample rate (44.1kHz instead of 8kHz)
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(44100)  # Wrong: 44.1kHz instead of 8kHz
                
                # Write some test audio data
                audio_data = struct.pack('<44100h', *([0] * 44100))
                wav_file.writeframes(audio_data)
            
            # Test validation
            is_valid, error_msg = self.loader.validate_wav_format(temp_filename)
            self.assertFalse(is_valid)
            self.assertIn("sample rate", error_msg.lower())
            self.assertIn("8000", error_msg)
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    def test_validate_wav_format_wrong_channels(self):
        """Test that WAV file with wrong number of channels is rejected."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
            
        try:
            # Create WAV file with stereo (2 channels instead of 1)
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(2)  # Wrong: Stereo instead of mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(8000)  # 8kHz
                
                # Write some test audio data
                audio_data = struct.pack('<16000h', *([0] * 16000))  # 2 channels * 8000 samples
                wav_file.writeframes(audio_data)
            
            # Test validation
            is_valid, error_msg = self.loader.validate_wav_format(temp_filename)
            self.assertFalse(is_valid)
            self.assertIn("channels", error_msg.lower())
            self.assertIn("1", error_msg)
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    def test_validate_wav_format_wrong_sample_width(self):
        """Test that WAV file with wrong sample width is rejected."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
            
        try:
            # Create WAV file with 8-bit instead of 16-bit
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(1)  # Wrong: 8-bit instead of 16-bit
                wav_file.setframerate(8000)  # 8kHz
                
                # Write some test audio data
                audio_data = struct.pack('<8000B', *([0] * 8000))  # 8-bit samples
                wav_file.writeframes(audio_data)
            
            # Test validation
            is_valid, error_msg = self.loader.validate_wav_format(temp_filename)
            self.assertFalse(is_valid)
            self.assertIn("sample width", error_msg.lower())
            self.assertIn("16", error_msg)
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    def test_validate_wav_format_nonexistent_file(self):
        """Test that validation fails for nonexistent file."""
        is_valid, error_msg = self.loader.validate_wav_format("nonexistent_file.wav")
        self.assertFalse(is_valid)
        self.assertIn("file", error_msg.lower())
        
    def test_validate_wav_format_not_wav_file(self):
        """Test that validation fails for non-WAV file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_filename = temp_file.name
            temp_file.write(b"This is not a WAV file")
            
        try:
            is_valid, error_msg = self.loader.validate_wav_format(temp_filename)
            self.assertFalse(is_valid)
            self.assertIn("wav", error_msg.lower())
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    def test_load_wav_file_asterisk_compatible(self):
        """Test loading WAV file with Asterisk-compatible format."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
            
        try:
            # Create WAV file with Asterisk-compatible format
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(8000)  # 8kHz
                
                # Write test audio data (1 second of alternating 1000/-1000)
                audio_data = struct.pack('<8000h', *([1000, -1000] * 4000))
                wav_file.writeframes(audio_data)
            
            # Test loading
            audio_data, sample_rate, channels, sample_width = self.loader.load_wav_file(temp_filename)
            
            # Verify format
            self.assertEqual(sample_rate, 8000)
            self.assertEqual(channels, 1)
            self.assertEqual(sample_width, 2)
            
            # Verify audio data length (8000 samples * 2 bytes per sample)
            self.assertEqual(len(audio_data), 16000)
            
            # Verify some sample values
            samples = struct.unpack('<8000h', audio_data)
            self.assertEqual(samples[0], 1000)
            self.assertEqual(samples[1], -1000)
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
    def test_load_wav_file_invalid_format(self):
        """Test that loading invalid WAV file raises exception."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
            
        try:
            # Create WAV file with wrong format (44.1kHz)
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(44100)  # Wrong sample rate
                
                audio_data = struct.pack('<44100h', *([0] * 44100))
                wav_file.writeframes(audio_data)
            
            # Test loading should raise exception
            with self.assertRaises(ValueError) as context:
                self.loader.load_wav_file(temp_filename)
            
            self.assertIn("Sample rate", str(context.exception))
            
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)


class TestWavAudioStreamer(unittest.TestCase):
    """Test streaming of WAV audio as AudioSocket protocol frames."""
    
    def setUp(self):
        self.loader = WavFileLoader()
        # Create a valid test WAV file (8000 samples, 1 second)
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        self.temp_filename = self.temp_file.name
        with wave.open(self.temp_filename, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            # 8000 samples, alternating 1000/-1000
            audio_data = struct.pack('<8000h', *([1000, -1000] * 4000))
            wav_file.writeframes(audio_data)
    
    def tearDown(self):
        if os.path.exists(self.temp_filename):
            os.unlink(self.temp_filename)
    
    def test_streams_correct_number_of_frames(self):
        """Test that streamer yields correct number of frames for 1s of audio."""
        from audio_playback import WavAudioStreamer
        streamer = WavAudioStreamer(self.temp_filename)
        frames = list(streamer)
        # 8000 samples * 2 bytes = 16000 bytes / 320 bytes per frame = 50 frames
        self.assertEqual(len(frames), 50)
        for frame in frames:
            # Each frame should be 3 (header) + 320 (payload) = 323 bytes
            self.assertEqual(len(frame), 323)
    
    def test_frame_header_and_payload(self):
        """Test that each frame has correct header and payload."""
        from audio_playback import WavAudioStreamer
        streamer = WavAudioStreamer(self.temp_filename)
        for frame in streamer:
            # Header: kind (0x10), length (0x01 0x40 = 320)
            self.assertEqual(frame[0], 0x10)
            self.assertEqual(frame[1], 0x01)
            self.assertEqual(frame[2], 0x40)
            # Payload: 320 bytes
            self.assertEqual(len(frame[3:]), 320)
    
    def test_partial_final_frame(self):
        """Test that partial final frame is padded with zeros if needed."""
        from audio_playback import WavAudioStreamer
        # Create a file with 8001 samples (16002 bytes, so last frame is 2 bytes short)
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_filename = temp_file.name
        try:
            with wave.open(temp_filename, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(8000)
                audio_data = struct.pack('<8001h', *([1000] * 8001))
                wav_file.writeframes(audio_data)
            streamer = WavAudioStreamer(temp_filename)
            frames = list(streamer)
            # 16002 / 320 = 50 frames, but last frame is 2 bytes short
            self.assertEqual(len(frames), 51)
            # Last frame payload should be 2 bytes audio + 318 bytes zero padding
            last_payload = frames[-1][3:]
            self.assertEqual(len(last_payload), 320)
            self.assertEqual(last_payload[:2], struct.pack('<h', 1000))
            self.assertEqual(last_payload[2:], b'\x00' * 318)
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def test_raises_on_invalid_wav(self):
        """Test that streamer raises ValueError on invalid WAV file."""
        from audio_playback import WavAudioStreamer
        with self.assertRaises(ValueError):
            WavAudioStreamer('nonexistent_file.wav')


if __name__ == '__main__':
    unittest.main() 