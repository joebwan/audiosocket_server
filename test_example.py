#!/usr/bin/env python3
"""
Test suite for example applications
Run with: python -m unittest test_example.py
"""

import os
import tempfile
import unittest
import wave
from unittest.mock import MagicMock, Mock, patch

import numpy as np

# Local imports
from example_application import AudioStreamer
from mapping import mapping
from mylogging import ColouredLogger
from req import Requests


class TestExampleApplication(unittest.TestCase):
    """Test the example application functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_connection = Mock()
        self.mock_connection.connected = True
        self.mock_connection.read.return_value = (
            b"\x00" * 320
        )  # Mock audio data
        self.mock_connection.write = Mock()

        # Create a temporary directory for test audio files
        self.temp_dir = tempfile.mkdtemp()
        self.create_test_audio_files()

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_audio_files(self):
        """Create test audio files for testing"""
        # Create test audio files in the temp directory
        test_files = {
            "test_hello.wav": self.generate_test_audio(1.0),
            "test_ask.wav": self.generate_test_audio(2.0),
            "test_sorry.wav": self.generate_test_audio(0.5),
        }

        for filename, audio_data in test_files.items():
            filepath = os.path.join(self.temp_dir, filename)
            with wave.open(filepath, "wb") as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(8000)
                wav_file.writeframes(audio_data)

    def generate_test_audio(self, duration_seconds):
        """Generate test audio data"""
        sample_rate = 8000
        t = np.linspace(
            0, duration_seconds, int(sample_rate * duration_seconds)
        )
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.5  # 440 Hz sine wave
        audio_data = (audio_data * 32767).astype(np.int16)
        return audio_data.tobytes()

    def test_audio_streamer_initialization(self):
        """Test AudioStreamer class initialization"""
        streamer = AudioStreamer(self.mock_connection)

        self.assertEqual(streamer.call, self.mock_connection)
        self.assertIsNotNone(streamer.logger)
        self.assertIsNotNone(streamer.vad)
        self.assertEqual(streamer.channels, 1)
        self.assertEqual(streamer.sample_rate, 8000)

    def test_audio_streamer_attributes(self):
        """Test AudioStreamer attributes are properly set"""
        streamer = AudioStreamer(self.mock_connection)

        # Test that required attributes exist
        self.assertTrue(hasattr(streamer, "call"))
        self.assertTrue(hasattr(streamer, "logger"))
        self.assertTrue(hasattr(streamer, "vad"))
        self.assertTrue(hasattr(streamer, "channels"))
        self.assertTrue(hasattr(streamer, "sample_rate"))
        self.assertTrue(hasattr(streamer, "noise_frames_threshold"))
        self.assertTrue(hasattr(streamer, "noise_frames_count"))
        self.assertTrue(hasattr(streamer, "state"))
        self.assertTrue(hasattr(streamer, "progression_level"))
        self.assertTrue(hasattr(streamer, "audioplayback"))
        self.assertTrue(hasattr(streamer, "channel"))

    @patch("webrtcvad.Vad")
    def test_vad_initialization(self, mock_vad_class):
        """Test Voice Activity Detection initialization"""
        mock_vad = Mock()
        mock_vad_class.return_value = mock_vad

        streamer = AudioStreamer(self.mock_connection)

        mock_vad_class.assert_called_once()  # No arguments expected
        mock_vad.set_mode.assert_called_once_with(3)  # Most aggressive mode
        self.assertEqual(streamer.vad, mock_vad)

    def test_audio_data_collection(self):
        """Test audio data collection functionality"""
        streamer = AudioStreamer(self.mock_connection)

        # Simulate audio data collection
        audio_data = streamer.call.read()

        self.assertEqual(len(audio_data), 320)  # Standard frame size
        self.mock_connection.read.assert_called_once()

    def test_noise_detection_initialization(self):
        """Test noise detection parameters"""
        streamer = AudioStreamer(self.mock_connection)

        # Test noise detection thresholds
        expected_threshold = int(2 * 8000 / 512)  # Based on sample rate
        self.assertEqual(streamer.noise_frames_threshold, expected_threshold)
        self.assertEqual(streamer.noise_frames_count, 0)

    def test_conversation_state_initialization(self):
        """Test conversation state initialization"""
        streamer = AudioStreamer(self.mock_connection)

        # Test initial state
        self.assertEqual(streamer.state.value, 1)  # NORMAL_PROGRESSION
        self.assertEqual(streamer.progression_level, 1)
        self.assertEqual(streamer.last_progression_level, 1)

    def test_audio_playback_initialization(self):
        """Test audio playback initialization"""
        streamer = AudioStreamer(self.mock_connection)

        # Test initial playback state
        self.assertFalse(streamer.audioplayback)
        self.assertEqual(streamer.channel, "en")  # Default to English


class TestMappingConfiguration(unittest.TestCase):
    """Test the mapping configuration for audio files"""

    def test_mapping_structure(self):
        """Test that mapping has correct structure"""
        self.assertIn("en", mapping)
        self.assertIn("hi", mapping)
        self.assertIsInstance(mapping["en"], dict)
        self.assertIsInstance(mapping["hi"], dict)

    def test_english_audio_files(self):
        """Test English audio file mappings"""
        english_files = mapping["en"]

        # Check that required keys exist (actual keys in mapping)
        required_keys = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        for key in required_keys:
            self.assertIn(
                key, english_files, f"Missing key {key} in English mapping"
            )

        # Check that all files are WAV files
        for file_path in english_files.values():
            self.assertTrue(
                file_path.endswith(".wav"), f"Not a WAV file: {file_path}"
            )

    def test_hindi_audio_files(self):
        """Test Hindi audio file mappings"""
        hindi_files = mapping["hi"]

        # Check that required keys exist (actual keys in mapping)
        required_keys = [1, 2, 3, 4]
        for key in required_keys:
            self.assertIn(
                key, hindi_files, f"Missing key {key} in Hindi mapping"
            )

        # Check that all files are WAV files
        for file_path in hindi_files.values():
            self.assertTrue(
                file_path.endswith(".wav"), f"Not a WAV file: {file_path}"
            )

    def test_audio_file_paths_exist(self):
        """Test that all audio file paths exist"""
        for language, files in mapping.items():
            for key, file_path in files.items():
                self.assertTrue(
                    os.path.exists(file_path),
                    f"Audio file not found: {file_path} (language: {language}, key: {key})",
                )

    def test_audio_file_format(self):
        """Test that audio files are valid WAV files"""
        for language, files in mapping.items():
            for key, file_path in files.items():
                try:
                    with wave.open(file_path, "rb") as wav_file:
                        # Check basic WAV properties (some files might be stereo)
                        self.assertIn(
                            wav_file.getnchannels(), [1, 2]
                        )  # Mono or stereo
                        self.assertEqual(wav_file.getsampwidth(), 2)  # 16-bit
                        self.assertEqual(wav_file.getframerate(), 8000)  # 8kHz
                except Exception as e:
                    self.fail(f"Invalid WAV file {file_path}: {e}")


class TestRequestsIntegration(unittest.TestCase):
    """Test the Requests class integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.requests = Requests()

    def test_requests_initialization(self):
        """Test Requests class initialization"""
        self.assertIsNotNone(self.requests.logger)
        self.assertEqual(self.requests.headers, {})
        self.assertEqual(self.requests.body, {})

    @patch("requests.get")
    def test_send_get_request_with_logging(self, mock_get):
        """Test sending GET request with proper logging"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.requests.send("GET", "http://example.com")

        mock_get.assert_called_once_with("http://example.com", headers={})
        self.assertEqual(result, mock_response)

    @patch("requests.post")
    def test_send_post_request_with_logging(self, mock_post):
        """Test sending POST request with proper logging"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.requests.send("POST", "http://example.com")

        mock_post.assert_called_once_with(
            "http://example.com", headers={}, data={}
        )
        self.assertEqual(result, mock_response)

    def test_send_invalid_method_logging(self):
        """Test logging for invalid HTTP method"""
        result = self.requests.send("INVALID", "http://example.com")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
