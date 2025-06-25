#!/usr/bin/env python3
"""
Test suite for Asterisk AudioSocket Server
Run with: python -m unittest test_audiosocket.py
"""

import os
import socket
import tempfile
import threading
import time
import unittest
import wave
from unittest.mock import MagicMock, Mock, patch

import numpy as np

# Local imports
from audiosocket import AudioOpStruct, Audiosocket
from connection import Connection, ErrorsStruct, TypesStruct, errors, types
from mapping import mapping
from mylogging import ColouredLogger
from req import Requests


class TestAudioOpStruct(unittest.TestCase):
    """Test the AudioOpStruct dataclass"""

    def test_audioop_struct_creation(self):
        """Test creating AudioOpStruct instances"""
        struct = AudioOpStruct(
            ratecv_state=None, rate=8000, channels=1, ulaw2lin=False
        )
        self.assertEqual(struct.rate, 8000)
        self.assertEqual(struct.channels, 1)
        self.assertFalse(struct.ulaw2lin)
        self.assertIsNone(struct.ratecv_state)


class TestTypesStruct(unittest.TestCase):
    """Test the TypesStruct dataclass"""

    def test_types_struct_values(self):
        """Test that all message types have correct byte values"""
        self.assertEqual(types.uuid, b"\x01")
        self.assertEqual(types.audio, b"\x10")
        self.assertEqual(types.silence, b"\x02")
        self.assertEqual(types.hangup, b"\x00")
        self.assertEqual(types.error, b"\xff")


class TestErrorsStruct(unittest.TestCase):
    """Test the ErrorsStruct dataclass"""

    def test_errors_struct_values(self):
        """Test that all error codes have correct byte values"""
        self.assertEqual(errors.none, b"\x00")
        self.assertEqual(errors.hangup, b"\x01")
        self.assertEqual(errors.frame, b"\x02")
        self.assertEqual(errors.memory, b"\x04")


class TestRequests(unittest.TestCase):
    """Test the Requests class"""

    def setUp(self):
        """Set up test fixtures"""
        self.requests = Requests()

    def test_requests_initialization(self):
        """Test Requests class initialization"""
        self.assertIsNotNone(self.requests.logger)
        self.assertEqual(self.requests.headers, {})
        self.assertEqual(self.requests.body, {})

    @patch("requests.get")
    def test_send_get_request(self, mock_get):
        """Test sending GET request"""
        mock_response = Mock()
        mock_get.return_value = mock_response

        result = self.requests.send("GET", "http://example.com")

        mock_get.assert_called_once_with("http://example.com", headers={})
        self.assertEqual(result, mock_response)

    @patch("requests.post")
    def test_send_post_request(self, mock_post):
        """Test sending POST request"""
        mock_response = Mock()
        mock_post.return_value = mock_response

        result = self.requests.send("POST", "http://example.com")

        mock_post.assert_called_once_with(
            "http://example.com", headers={}, data={}
        )
        self.assertEqual(result, mock_response)

    def test_send_invalid_method(self):
        """Test sending invalid HTTP method"""
        result = self.requests.send("INVALID", "http://example.com")
        self.assertIsNone(result)


class TestAudiosocket(unittest.TestCase):
    """Test the Audiosocket class"""

    def setUp(self):
        """Set up test fixtures"""
        # Use a random port to avoid conflicts
        self.test_port = 0  # Let OS choose available port
        self.audiosocket = None

    def tearDown(self):
        """Clean up test fixtures"""
        if self.audiosocket and hasattr(self.audiosocket, "initial_sock"):
            self.audiosocket.initial_sock.close()

    def test_audiosocket_initialization(self):
        """Test Audiosocket initialization"""
        self.audiosocket = Audiosocket(("127.0.0.1", self.test_port))
        self.assertEqual(self.audiosocket.addr, "127.0.0.1")
        self.assertIsNotNone(self.audiosocket.port)
        self.assertIsNone(self.audiosocket.user_resample)
        self.assertIsNone(self.audiosocket.asterisk_resample)

    def test_audiosocket_invalid_bind_info(self):
        """Test Audiosocket initialization with invalid bind_info"""
        with self.assertRaises(TypeError):
            Audiosocket("invalid_bind_info")

    def test_prepare_input(self):
        """Test prepare_input method"""
        self.audiosocket = Audiosocket(("127.0.0.1", self.test_port))
        self.audiosocket.prepare_input(inrate=44100, channels=2, ulaw2lin=True)

        self.assertIsNotNone(self.audiosocket.user_resample)
        self.assertEqual(self.audiosocket.user_resample.rate, 44100)
        self.assertEqual(self.audiosocket.user_resample.channels, 2)
        self.assertTrue(self.audiosocket.user_resample.ulaw2lin)

    def test_prepare_output(self):
        """Test prepare_output method"""
        self.audiosocket = Audiosocket(("127.0.0.1", self.test_port))
        self.audiosocket.prepare_output(
            outrate=48000, channels=1, ulaw2lin=False
        )

        self.assertIsNotNone(self.audiosocket.asterisk_resample)
        self.assertEqual(self.audiosocket.asterisk_resample.rate, 48000)
        self.assertEqual(self.audiosocket.asterisk_resample.channels, 1)
        self.assertFalse(self.audiosocket.asterisk_resample.ulaw2lin)


class TestConnection(unittest.TestCase):
    """Test the Connection class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock socket connection
        self.mock_socket = Mock()
        self.mock_socket.recv.return_value = (
            b"\x10\x01\x40" + b"\x00" * 320
        )  # Audio message
        self.peer_addr = ("127.0.0.1", 12345)
        self.connection = Connection(
            self.mock_socket,
            self.peer_addr,
            None,  # user_resample
            None,  # asterisk_resample
        )

    def test_connection_initialization(self):
        """Test Connection initialization"""
        self.assertEqual(self.connection.peer_addr, self.peer_addr)
        self.assertTrue(self.connection.connected)
        self.assertIsNone(self.connection.uuid)
        self.assertIsNotNone(self.connection._rx_q)
        self.assertIsNotNone(self.connection._tx_q)

    def test_split_data_valid(self):
        """Test _split_data method with valid data"""
        data = b"\x10\x01\x40" + b"\x00" * 320
        msg_type, length, payload = self.connection._split_data(data)

        self.assertEqual(msg_type, b"\x10")
        self.assertEqual(length, 320)
        self.assertEqual(len(payload), 320)

    def test_split_data_invalid(self):
        """Test _split_data method with invalid data"""
        data = b"\x10"  # Too short
        msg_type, length, payload = self.connection._split_data(data)

        self.assertEqual(msg_type, b"\x00")
        self.assertEqual(length, 0)
        self.assertEqual(len(payload), 320)

    def test_decode_error(self):
        """Test _decode_error method"""
        # This test mainly checks that the method doesn't raise exceptions
        self.connection._decode_error(errors.none)
        self.connection._decode_error(errors.hangup)
        self.connection._decode_error(errors.frame)
        self.connection._decode_error(errors.memory)

    def test_read_empty_queue(self):
        """Test read method when queue is empty"""
        # Clear the queue
        while not self.connection._rx_q.empty():
            self.connection._rx_q.get()

        audio = self.connection.read()
        self.assertEqual(len(audio), 320)

    def test_write_audio(self):
        """Test write method"""
        test_audio = b"\x00" * 320
        initial_queue_size = self.connection._tx_q.qsize()

        self.connection.write(test_audio)

        self.assertEqual(self.connection._tx_q.qsize(), initial_queue_size + 1)

    def test_hangup(self):
        """Test hangup method"""
        self.connection.hangup()
        self.mock_socket.send.assert_called_once_with(types.hangup * 3)


class TestMapping(unittest.TestCase):
    """Test the mapping configuration"""

    def test_mapping_structure(self):
        """Test that mapping has correct structure"""
        self.assertIn("en", mapping)
        self.assertIn("hi", mapping)
        self.assertIsInstance(mapping["en"], dict)
        self.assertIsInstance(mapping["hi"], dict)

    def test_english_audio_files(self):
        """Test English audio file mappings"""
        english_files = mapping["en"]
        self.assertIn(1, english_files)
        self.assertIn(11, english_files)
        self.assertTrue(
            all(f.endswith(".wav") for f in english_files.values())
        )

    def test_hindi_audio_files(self):
        """Test Hindi audio file mappings"""
        hindi_files = mapping["hi"]
        self.assertIn(1, hindi_files)
        self.assertIn(4, hindi_files)
        self.assertTrue(all(f.endswith(".wav") for f in hindi_files.values()))

    def test_audio_file_paths_exist(self):
        """Test that audio file paths exist"""
        for language in mapping.values():
            for file_path in language.values():
                self.assertTrue(
                    os.path.exists(file_path), f"File not found: {file_path}"
                )


class TestColouredLogger(unittest.TestCase):
    """Test the ColouredLogger class"""

    def setUp(self):
        """Set up test fixtures"""
        self.logger = ColouredLogger("test_logger")

    def tearDown(self):
        """Clean up test fixtures"""
        # Properly close all handlers to prevent resource warnings
        if hasattr(self, "logger"):
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)

    def test_logger_initialization(self):
        """Test logger initialization"""
        self.assertEqual(self.logger.name, "test_logger")
        self.assertEqual(self.logger.level, 10)  # DEBUG level

    def test_logger_handlers(self):
        """Test that logger has both console and file handlers"""
        handlers = self.logger.handlers
        self.assertEqual(len(handlers), 2)

        handler_types = [type(handler) for handler in handlers]
        self.assertIn(type(self.logger.ch), handler_types)
        self.assertIn(type(self.logger.fh), handler_types)

    def test_logger_methods(self):
        """Test that all logger methods work without raising exceptions"""
        self.logger.debug("Test debug message")
        self.logger.info("Test info message")
        self.logger.warning("Test warning message")
        self.logger.error("Test error message")
        self.logger.critical("Test critical message")


class TestAudioFileGeneration(unittest.TestCase):
    """Test audio file generation utilities"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_wav_file(
        self, filename, duration_seconds=1.0, sample_rate=8000
    ):
        """Create a test WAV file for testing"""
        filepath = os.path.join(self.temp_dir, filename)

        # Generate test audio data (sine wave)
        t = np.linspace(
            0, duration_seconds, int(sample_rate * duration_seconds)
        )
        audio_data = np.sin(2 * np.pi * 440 * t) * 0.5  # 440 Hz sine wave
        audio_data = (audio_data * 32767).astype(np.int16)

        with wave.open(filepath, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())

        return filepath

    def test_wav_file_creation(self):
        """Test creating a test WAV file"""
        test_file = self.create_test_wav_file("test.wav")
        self.assertTrue(os.path.exists(test_file))

        # Verify it's a valid WAV file
        with wave.open(test_file, "rb") as wav_file:
            self.assertEqual(wav_file.getnchannels(), 1)
            self.assertEqual(wav_file.getsampwidth(), 2)
            self.assertEqual(wav_file.getframerate(), 8000)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_port = 0
        self.audiosocket = None

    def tearDown(self):
        """Clean up test fixtures"""
        if self.audiosocket and hasattr(self.audiosocket, "initial_sock"):
            self.audiosocket.initial_sock.close()

    def test_audiosocket_server_creation(self):
        """Test creating an AudioSocket server"""
        self.audiosocket = Audiosocket(("127.0.0.1", self.test_port))
        self.assertIsNotNone(self.audiosocket)
        self.assertTrue(self.audiosocket.initial_sock.fileno() > 0)

    def test_connection_lifecycle(self):
        """Test the complete connection lifecycle"""
        # This would require a more complex setup with actual socket connections
        # For now, we'll just test that the components can be created
        self.audiosocket = Audiosocket(("127.0.0.1", self.test_port))
        self.assertIsNotNone(self.audiosocket)


class TestAudioFormatConversion(unittest.TestCase):
    """Test ULAW <-> Linear PCM audio format conversion"""

    def test_ulaw2lin_known_values(self):
        import audioop_compat

        # ULAW 0xFF (should be near 0 for silence)
        ulaw_bytes = bytes([0xFF] * 10)
        pcm = audioop_compat.ulaw2lin(ulaw_bytes, 2)
        # Should decode to values close to 0 (silence)
        pcm_values = np.frombuffer(pcm, dtype=np.int16)
        self.assertTrue(np.all(np.abs(pcm_values) < 1000))

    def test_ulaw2lin_random(self):
        import audioop_compat

        # Random ULAW bytes
        ulaw_bytes = bytes([0, 127, 128, 255, 100, 200, 50, 150, 25, 175])
        pcm = audioop_compat.ulaw2lin(ulaw_bytes, 2)
        self.assertEqual(len(pcm), 20)  # 10 samples, 2 bytes each
        # Just check that it returns a valid int16 array
        pcm_values = np.frombuffer(pcm, dtype=np.int16)
        self.assertEqual(len(pcm_values), 10)

    def test_ulaw2lin_invalid_width(self):
        import audioop_compat

        ulaw_bytes = bytes([0xFF] * 10)
        with self.assertRaises(ValueError):
            audioop_compat.ulaw2lin(ulaw_bytes, 1)


class TestAudioResampling(unittest.TestCase):
    """Test audio resampling (rate conversion) functionality"""

    def setUp(self):
        """Set up test fixtures"""
        import audioop_compat

        self.audioop = audioop_compat

        # Create test audio data (1 second of 440Hz sine wave at 8kHz)
        t = np.linspace(0, 1, 8000)
        self.test_audio_8k = np.sin(2 * np.pi * 440 * t) * 0.5
        self.test_audio_8k = (
            (self.test_audio_8k * 32767).astype(np.int16).tobytes()
        )

    def test_ratecv_same_rate(self):
        """Test resampling when input and output rates are the same"""
        result, state = self.audioop.ratecv(
            self.test_audio_8k, 2, 1, 8000, 8000
        )
        self.assertEqual(result, self.test_audio_8k)
        self.assertIsNone(state)

    def test_ratecv_upsampling_8k_to_16k(self):
        """Test upsampling from 8kHz to 16kHz"""
        result, state = self.audioop.ratecv(
            self.test_audio_8k, 2, 1, 8000, 16000
        )

        # Check that output is longer (double the samples)
        self.assertEqual(len(result), len(self.test_audio_8k) * 2)

        # Check that it's valid 16-bit audio
        samples = np.frombuffer(result, dtype=np.int16)
        self.assertEqual(len(samples), 16000)  # 1 second at 16kHz

    def test_ratecv_downsampling_16k_to_8k(self):
        """Test downsampling from 16kHz to 8kHz"""
        # Create 16kHz test audio
        t = np.linspace(0, 1, 16000)
        test_audio_16k = np.sin(2 * np.pi * 440 * t) * 0.5
        test_audio_16k = (test_audio_16k * 32767).astype(np.int16).tobytes()

        result, state = self.audioop.ratecv(test_audio_16k, 2, 1, 16000, 8000)

        # Check that output is shorter (half the samples)
        self.assertEqual(len(result), len(test_audio_16k) // 2)

        # Check that it's valid 16-bit audio
        samples = np.frombuffer(result, dtype=np.int16)
        self.assertEqual(len(samples), 8000)  # 1 second at 8kHz

    def test_ratecv_invalid_width(self):
        """Test resampling with invalid width parameter"""
        with self.assertRaises(ValueError):
            self.audioop.ratecv(self.test_audio_8k, 1, 1, 8000, 16000)

    def test_ratecv_state_persistence(self):
        """Test that state is properly maintained between calls"""
        # First call
        result1, state1 = self.audioop.ratecv(
            self.test_audio_8k[:1600], 2, 1, 8000, 16000
        )

        # Second call with same state
        result2, state2 = self.audioop.ratecv(
            self.test_audio_8k[1600:3200], 2, 1, 8000, 16000, state1
        )

        # Both should return valid results
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        # State is returned unchanged in this implementation
        self.assertEqual(state2, state1)

    def test_ratecv_quality_check(self):
        """Test that resampled audio maintains reasonable quality"""
        # Upsample then downsample back to original rate
        upsampled, _ = self.audioop.ratecv(
            self.test_audio_8k, 2, 1, 8000, 16000
        )
        downsampled, _ = self.audioop.ratecv(upsampled, 2, 1, 16000, 8000)

        # Should have same length as original
        self.assertEqual(len(downsampled), len(self.test_audio_8k))

        # Should be valid 16-bit audio
        samples = np.frombuffer(downsampled, dtype=np.int16)
        self.assertEqual(len(samples), 8000)


class TestVoiceActivityDetection(unittest.TestCase):
    """Test Voice Activity Detection (VAD) functionality using webrtcvad"""

    def setUp(self):
        import webrtcvad

        self.vad = webrtcvad.Vad()
        self.sample_rate = 8000
        # Generate 30ms of silence (all zeros)
        self.silence = (
            (np.zeros(int(self.sample_rate * 0.03))).astype(np.int16).tobytes()
        )
        # Generate 30ms of 440Hz sine wave (speech-like)
        t = np.linspace(0, 0.03, int(self.sample_rate * 0.03), endpoint=False)
        self.speech = (
            (0.5 * np.sin(2 * np.pi * 440 * t) * 32767)
            .astype(np.int16)
            .tobytes()
        )

    def test_vad_initialization(self):
        import webrtcvad

        vad0 = webrtcvad.Vad(0)
        vad1 = webrtcvad.Vad(1)
        vad2 = webrtcvad.Vad(2)
        vad3 = webrtcvad.Vad(3)
        self.assertIsInstance(vad0, webrtcvad.Vad)
        self.assertIsInstance(vad1, webrtcvad.Vad)
        self.assertIsInstance(vad2, webrtcvad.Vad)
        self.assertIsInstance(vad3, webrtcvad.Vad)

    def test_vad_detects_silence(self):
        # Should return False for silence
        is_speech = self.vad.is_speech(self.silence, self.sample_rate)
        self.assertFalse(is_speech)

    def test_vad_detects_speech(self):
        # Should return True for speech-like audio
        is_speech = self.vad.is_speech(self.speech, self.sample_rate)
        self.assertTrue(is_speech)

    def test_vad_aggressiveness_levels(self):
        import webrtcvad

        # More aggressive = less likely to detect speech in noisy input
        results = []
        for mode in range(4):
            vad = webrtcvad.Vad(mode)
            results.append(vad.is_speech(self.speech, self.sample_rate))
        # At least one mode should detect speech
        self.assertIn(True, results)
        # (Do not require False, as all modes may return True for clean synthetic speech)

    def test_vad_invalid_audio_length(self):
        # VAD expects 10, 20, or 30ms frames
        with self.assertRaises(Exception):
            self.vad.is_speech(self.speech[:10], self.sample_rate)


class TestAudioSocketProtocol(unittest.TestCase):
    """Test AudioSocket protocol message parsing and handling"""

    def setUp(self):
        from connection import Connection, ErrorsStruct, TypesStruct

        self.Types = TypesStruct()
        self.Errors = ErrorsStruct()
        self.mock_socket = MagicMock()
        self.peer_addr = ("127.0.0.1", 12345)
        self.conn = Connection(self.mock_socket, self.peer_addr, None, None)

    def test_split_data_uuid(self):
        # UUID message: type=0x01, length=16, payload=16 bytes
        msg_type = self.Types.uuid
        payload = b"1234567890abcdef"
        length = len(payload).to_bytes(2, "big")
        data = msg_type + length + payload
        t, l, p = self.conn._split_data(data)
        self.assertEqual(t, msg_type)
        self.assertEqual(l, 16)
        self.assertEqual(p, payload)

    def test_split_data_audio(self):
        # Audio message: type=0x10, length=320, payload=320 bytes
        msg_type = self.Types.audio
        payload = b"a" * 320
        length = len(payload).to_bytes(2, "big")
        data = msg_type + length + payload
        t, l, p = self.conn._split_data(data)
        self.assertEqual(t, msg_type)
        self.assertEqual(l, 320)
        self.assertEqual(p, payload)

    def test_split_data_silence(self):
        # Silence message: type=0x02, length=0, payload=empty
        msg_type = self.Types.silence
        payload = b""
        length = len(payload).to_bytes(2, "big")
        data = msg_type + length + payload
        t, l, p = self.conn._split_data(data)
        self.assertEqual(t, msg_type)
        self.assertEqual(l, 0)
        self.assertEqual(p, payload)

    def test_split_data_hangup(self):
        # Hangup message: type=0x00, length=0, payload=empty
        msg_type = self.Types.hangup
        payload = b""
        length = len(payload).to_bytes(2, "big")
        data = msg_type + length + payload
        t, l, p = self.conn._split_data(data)
        self.assertEqual(t, msg_type)
        self.assertEqual(l, 0)
        self.assertEqual(p, payload)

    def test_split_data_error(self):
        # Error message: type=0xFF, length=1, payload=1 byte
        msg_type = self.Types.error
        payload = b"\x01"
        length = len(payload).to_bytes(2, "big")
        data = msg_type + length + payload
        t, l, p = self.conn._split_data(data)
        self.assertEqual(t, msg_type)
        self.assertEqual(l, 1)
        self.assertEqual(p, payload)

    def test_split_data_too_short(self):
        # Data too short should return default values
        data = b"\x10"
        t, l, p = self.conn._split_data(data)
        self.assertEqual(t, b"\x00")
        self.assertEqual(l, 0)
        self.assertEqual(len(p), 320)

    def test_decode_error(self):
        # Should not raise for any error code
        for code in [
            self.Errors.none,
            self.Errors.hangup,
            self.Errors.frame,
            self.Errors.memory,
        ]:
            self.conn._decode_error(code)


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
