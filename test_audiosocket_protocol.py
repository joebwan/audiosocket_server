#!/usr/bin/env python3
"""
Unit tests for AudioSocket Protocol Implementation

This test suite covers the complete AudioSocket protocol implementation including:
- Frame creation and parsing
- Protocol configuration
- Error handling
- Connection management
- Server functionality

Run with: python -m unittest test_audiosocket_protocol.py -v
"""

import logging
import socket
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

# Local imports
from audiosocket_protocol import (
    AudioSocketConfig,
    AudioSocketConnection,
    AudioSocketFrame,
    AudioSocketProtocol,
    ErrorCode,
    FrameType,
)
from audiosocket_server import AudioSocketServer, EchoServer, VoiceBotServer


class TestFrameType(unittest.TestCase):
    """Test FrameType enum values"""

    def test_frame_type_values(self):
        """Test that frame types have correct values"""
        self.assertEqual(FrameType.HANGUP, 0x00)
        self.assertEqual(FrameType.UUID, 0x01)
        self.assertEqual(FrameType.SILENCE, 0x02)
        self.assertEqual(FrameType.DTMF, 0x03)
        self.assertEqual(FrameType.AUDIO, 0x10)
        self.assertEqual(FrameType.ERROR, 0xFF)

    def test_frame_type_names(self):
        """Test frame type names"""
        self.assertEqual(FrameType.HANGUP.name, "HANGUP")
        self.assertEqual(FrameType.UUID.name, "UUID")
        self.assertEqual(FrameType.SILENCE.name, "SILENCE")
        self.assertEqual(FrameType.DTMF.name, "DTMF")
        self.assertEqual(FrameType.AUDIO.name, "AUDIO")
        self.assertEqual(FrameType.ERROR.name, "ERROR")


class TestErrorCode(unittest.TestCase):
    """Test ErrorCode enum values"""

    def test_error_code_values(self):
        """Test that error codes have correct values"""
        self.assertEqual(ErrorCode.NONE, 0x00)
        self.assertEqual(ErrorCode.HANGUP, 0x01)
        self.assertEqual(ErrorCode.FRAME, 0x02)
        self.assertEqual(ErrorCode.MEMORY, 0x04)

    def test_error_code_names(self):
        """Test error code names"""
        self.assertEqual(ErrorCode.NONE.name, "NONE")
        self.assertEqual(ErrorCode.HANGUP.name, "HANGUP")
        self.assertEqual(ErrorCode.FRAME.name, "FRAME")
        self.assertEqual(ErrorCode.MEMORY.name, "MEMORY")


class TestAudioSocketConfig(unittest.TestCase):
    """Test AudioSocketConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        config = AudioSocketConfig()
        self.assertEqual(config.sample_rate, 8000)
        self.assertEqual(config.channels, 1)
        self.assertEqual(config.bit_depth, 16)
        self.assertEqual(config.frame_duration_ms, 20)
        self.assertTrue(config.ulaw2lin)

    def test_custom_config(self):
        """Test custom configuration values"""
        config = AudioSocketConfig(
            sample_rate=16000,
            channels=2,
            bit_depth=24,
            frame_duration_ms=10,
            ulaw2lin=False,
        )
        self.assertEqual(config.sample_rate, 16000)
        self.assertEqual(config.channels, 2)
        self.assertEqual(config.bit_depth, 24)
        self.assertEqual(config.frame_duration_ms, 10)
        self.assertFalse(config.ulaw2lin)

    def test_frame_size_calculation(self):
        """Test frame size calculation"""
        config = AudioSocketConfig()
        expected_size = 8000 * 20 // 1000 * 1 * 16 // 8  # 320 bytes
        self.assertEqual(config.frame_size, expected_size)

        # Test with different parameters
        config = AudioSocketConfig(
            sample_rate=16000, channels=2, frame_duration_ms=10
        )
        expected_size = 16000 * 10 // 1000 * 2 * 16 // 8  # 640 bytes
        self.assertEqual(config.frame_size, expected_size)

    def test_frame_interval_calculation(self):
        """Test frame interval calculation"""
        config = AudioSocketConfig()
        self.assertEqual(config.frame_interval, 0.02)  # 20ms

        config = AudioSocketConfig(frame_duration_ms=10)
        self.assertEqual(config.frame_interval, 0.01)  # 10ms

    def test_frames_per_second_calculation(self):
        """Test frames per second calculation"""
        config = AudioSocketConfig()
        self.assertEqual(config.frames_per_second, 50)  # 1000ms / 20ms

        config = AudioSocketConfig(frame_duration_ms=10)
        self.assertEqual(config.frames_per_second, 100)  # 1000ms / 10ms


class TestAudioSocketFrame(unittest.TestCase):
    """Test AudioSocketFrame class"""

    def test_frame_creation(self):
        """Test frame creation"""
        payload = b"test data"
        frame = AudioSocketFrame(FrameType.AUDIO, payload)
        self.assertEqual(frame.frame_type, FrameType.AUDIO)
        self.assertEqual(frame.payload, payload)
        self.assertEqual(frame.length, len(payload))

    def test_frame_to_bytes(self):
        """Test frame serialization"""
        payload = b"test"
        frame = AudioSocketFrame(FrameType.UUID, payload)
        frame_bytes = frame.to_bytes()

        # Check header: type (1 byte) + length (2 bytes) + payload
        expected = struct.pack(">B H", FrameType.UUID, 4) + payload
        self.assertEqual(frame_bytes, expected)

    def test_frame_from_bytes(self):
        """Test frame deserialization"""
        payload = b"test data"
        original_frame = AudioSocketFrame(FrameType.AUDIO, payload)
        frame_bytes = original_frame.to_bytes()

        parsed_frame = AudioSocketFrame.from_bytes(frame_bytes)
        self.assertEqual(parsed_frame.frame_type, original_frame.frame_type)
        self.assertEqual(parsed_frame.payload, original_frame.payload)
        self.assertEqual(parsed_frame.length, original_frame.length)

    def test_frame_from_bytes_invalid(self):
        """Test frame deserialization with invalid data"""
        # Too short
        with self.assertRaises(ValueError):
            AudioSocketFrame.from_bytes(b"\x10")

        # Incomplete payload
        with self.assertRaises(ValueError):
            AudioSocketFrame.from_bytes(
                b"\x10\x00\x05test"
            )  # Length=5 but only 4 bytes

    def test_frame_string_representation(self):
        """Test frame string representation"""
        frame = AudioSocketFrame(FrameType.AUDIO, b"test")
        frame_str = str(frame)
        self.assertIn("AudioSocketFrame", frame_str)
        self.assertIn("AUDIO", frame_str)
        self.assertIn("4", frame_str)  # length


class TestAudioSocketProtocol(unittest.TestCase):
    """Test AudioSocketProtocol class"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = AudioSocketConfig()
        self.protocol = AudioSocketProtocol(self.config)

    def test_protocol_initialization(self):
        """Test protocol initialization"""
        self.assertFalse(self.protocol.connected)
        self.assertIsNone(self.protocol.uuid)
        self.assertIsNone(self.protocol.peer_addr)
        self.assertEqual(self.protocol.frame_count, 0)
        self.assertEqual(self.protocol.bytes_received, 0)
        self.assertEqual(self.protocol.bytes_sent, 0)
        self.assertEqual(self.protocol.error_count, 0)
        self.assertIsNone(self.protocol.last_error)

    def test_create_frame(self):
        """Test frame creation"""
        payload = b"test"
        frame = self.protocol.create_frame(FrameType.AUDIO, payload)
        self.assertEqual(frame.frame_type, FrameType.AUDIO)
        self.assertEqual(frame.payload, payload)

    def test_create_audio_frame(self):
        """Test audio frame creation with validation"""
        # Valid audio data
        audio_data = b"\x00" * self.config.frame_size
        frame = self.protocol.create_audio_frame(audio_data)
        self.assertEqual(frame.frame_type, FrameType.AUDIO)
        self.assertEqual(frame.payload, audio_data)

        # Audio data too short (should pad)
        short_audio = b"\x00" * 100
        frame = self.protocol.create_audio_frame(short_audio)
        self.assertEqual(len(frame.payload), self.config.frame_size)

        # Audio data too long (should truncate)
        long_audio = b"\x00" * 1000
        frame = self.protocol.create_audio_frame(long_audio)
        self.assertEqual(len(frame.payload), self.config.frame_size)

    def test_create_uuid_frame(self):
        """Test UUID frame creation"""
        uuid = "1234567890abcdef1234567890abcdef"
        frame = self.protocol.create_uuid_frame(uuid)
        self.assertEqual(frame.frame_type, FrameType.UUID)
        self.assertEqual(len(frame.payload), 16)

        # Invalid UUID
        with self.assertRaises(ValueError):
            self.protocol.create_uuid_frame("invalid")

    def test_create_hangup_frame(self):
        """Test hangup frame creation"""
        frame = self.protocol.create_hangup_frame()
        self.assertEqual(frame.frame_type, FrameType.HANGUP)
        self.assertEqual(frame.payload, b"")

    def test_create_silence_frame(self):
        """Test silence frame creation"""
        frame = self.protocol.create_silence_frame()
        self.assertEqual(frame.frame_type, FrameType.SILENCE)
        self.assertEqual(frame.payload, b"")

    def test_create_error_frame(self):
        """Test error frame creation"""
        frame = self.protocol.create_error_frame(ErrorCode.HANGUP)
        self.assertEqual(frame.frame_type, FrameType.ERROR)
        self.assertEqual(frame.payload, bytes([ErrorCode.HANGUP]))

    def test_create_dtmf_frame(self):
        """Test DTMF frame creation"""
        # Valid DTMF digits
        for digit in "0123456789*#ABCD":
            frame = self.protocol.create_dtmf_frame(digit)
            self.assertEqual(frame.frame_type, FrameType.DTMF)
            self.assertEqual(frame.payload, digit.encode("ascii"))

        # Invalid DTMF digit
        with self.assertRaises(ValueError):
            self.protocol.create_dtmf_frame("X")

        with self.assertRaises(ValueError):
            self.protocol.create_dtmf_frame("12")

    def test_parse_frame(self):
        """Test frame parsing"""
        payload = b"test"
        original_frame = self.protocol.create_frame(FrameType.AUDIO, payload)
        frame_bytes = original_frame.to_bytes()

        parsed_frame = self.protocol.parse_frame(frame_bytes)
        self.assertEqual(parsed_frame.frame_type, original_frame.frame_type)
        self.assertEqual(parsed_frame.payload, original_frame.payload)
        self.assertEqual(self.protocol.frame_count, 1)
        self.assertGreater(self.protocol.bytes_received, 0)

    def test_handle_audio_frame(self):
        """Test audio frame handling"""
        audio_data = b"\x00" * self.config.frame_size
        frame = self.protocol.create_audio_frame(audio_data)

        response = self.protocol.handle_frame(frame)
        self.assertIsNotNone(response)
        self.assertEqual(response.frame_type, FrameType.AUDIO)
        self.assertEqual(response.payload, audio_data)

    def test_handle_uuid_frame(self):
        """Test UUID frame handling"""
        uuid_bytes = b"1234567890abcdef"
        frame = self.protocol.create_frame(FrameType.UUID, uuid_bytes)

        response = self.protocol.handle_frame(frame)
        self.assertIsNone(response)  # UUID frames don't generate responses
        self.assertEqual(self.protocol.uuid, uuid_bytes.hex())

    def test_handle_dtmf_frame(self):
        """Test DTMF frame handling"""
        frame = self.protocol.create_dtmf_frame("1")

        response = self.protocol.handle_frame(frame)
        self.assertIsNone(
            response
        )  # DTMF frames don't generate responses by default

    def test_handle_error_frame(self):
        """Test error frame handling"""
        frame = self.protocol.create_error_frame(ErrorCode.HANGUP)

        response = self.protocol.handle_frame(frame)
        self.assertIsNone(response)  # Error frames don't generate responses
        self.assertEqual(self.protocol.last_error, ErrorCode.HANGUP)

    def test_handle_hangup_frame(self):
        """Test hangup frame handling"""
        self.protocol.connected = True
        frame = self.protocol.create_hangup_frame()

        response = self.protocol.handle_frame(frame)
        self.assertIsNone(response)
        self.assertFalse(self.protocol.connected)

    def test_handle_silence_frame(self):
        """Test silence frame handling"""
        frame = self.protocol.create_silence_frame()

        response = self.protocol.handle_frame(frame)
        self.assertIsNotNone(response)
        self.assertEqual(response.frame_type, FrameType.SILENCE)

    def test_validate_audio_data(self):
        """Test audio data validation"""
        # Valid audio data
        valid_audio = b"\x00" * self.config.frame_size
        self.assertTrue(self.protocol.validate_audio_data(valid_audio))

        # Invalid size
        invalid_audio = b"\x00" * 100
        self.assertFalse(self.protocol.validate_audio_data(invalid_audio))

        # Silence detection
        silence_audio = b"\x00" * self.config.frame_size
        self.assertTrue(self.protocol.validate_audio_data(silence_audio))

    def test_create_silence_audio(self):
        """Test silence audio creation"""
        silence = self.protocol.create_silence_audio()
        self.assertEqual(len(silence), self.config.frame_size)
        self.assertTrue(all(b == 0 for b in silence))

    def test_get_statistics(self):
        """Test statistics gathering"""
        # Initial statistics
        stats = self.protocol.get_statistics()
        self.assertFalse(stats["connected"])
        self.assertEqual(stats["frame_count"], 0)
        self.assertEqual(stats["bytes_received"], 0)
        self.assertEqual(stats["bytes_sent"], 0)
        self.assertEqual(stats["error_count"], 0)
        self.assertIsNone(stats["last_error"])

        # Process some frames - use parse_frame to update statistics
        frame = self.protocol.create_audio_frame(
            b"\x00" * self.config.frame_size
        )
        frame_bytes = frame.to_bytes()
        parsed_frame = self.protocol.parse_frame(frame_bytes)

        stats = self.protocol.get_statistics()
        self.assertGreater(stats["frame_count"], 0)
        self.assertGreater(stats["bytes_received"], 0)

    def test_reset_statistics(self):
        """Test statistics reset"""
        # Process some frames
        frame = self.protocol.create_audio_frame(
            b"\x00" * self.config.frame_size
        )
        self.protocol.handle_frame(frame)

        # Reset statistics
        self.protocol.reset_statistics()

        stats = self.protocol.get_statistics()
        self.assertEqual(stats["frame_count"], 0)
        self.assertEqual(stats["bytes_received"], 0)
        self.assertEqual(stats["bytes_sent"], 0)
        self.assertEqual(stats["error_count"], 0)
        self.assertIsNone(stats["last_error"])


class TestAudioSocketConnection(unittest.TestCase):
    """Test AudioSocketConnection class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_socket = MagicMock()
        self.peer_addr = ("127.0.0.1", 12345)
        self.config = AudioSocketConfig()
        self.connection = AudioSocketConnection(
            self.mock_socket, self.peer_addr, self.config
        )

    def test_connection_initialization(self):
        """Test connection initialization"""
        self.assertEqual(self.connection.peer_addr, self.peer_addr)
        self.assertEqual(self.connection.socket, self.mock_socket)
        self.assertTrue(self.connection.protocol.connected)
        self.assertEqual(self.connection.protocol.peer_addr, self.peer_addr)

    def test_read_frame_success(self):
        """Test successful frame reading"""
        # Mock socket to return frame data
        frame = AudioSocketFrame(FrameType.AUDIO, b"test")
        frame_data = frame.to_bytes()

        self.mock_socket.recv.side_effect = [
            frame_data[:3],  # Header
            frame_data[3:],  # Payload
        ]

        result = self.connection.read_frame()
        self.assertIsNotNone(result)
        self.assertEqual(result.frame_type, FrameType.AUDIO)
        self.assertEqual(result.payload, b"test")

    def test_read_frame_connection_closed(self):
        """Test frame reading when connection is closed"""
        self.mock_socket.recv.return_value = b""

        result = self.connection.read_frame()
        self.assertIsNone(result)
        # The connection should be marked as disconnected when socket returns empty
        self.assertFalse(self.connection.protocol.connected)

    def test_write_frame_success(self):
        """Test successful frame writing"""
        frame = AudioSocketFrame(FrameType.AUDIO, b"test")

        result = self.connection.write_frame(frame)
        self.assertTrue(result)
        self.mock_socket.sendall.assert_called_once()

    def test_write_frame_failure(self):
        """Test frame writing failure"""
        frame = AudioSocketFrame(FrameType.AUDIO, b"test")
        self.mock_socket.sendall.side_effect = ConnectionError(
            "Connection lost"
        )

        result = self.connection.write_frame(frame)
        self.assertFalse(result)
        self.assertFalse(self.connection.protocol.connected)

    def test_close(self):
        """Test connection close"""
        self.connection.close()
        self.assertFalse(self.connection.protocol.connected)
        self.mock_socket.close.assert_called_once()

    def test_get_statistics(self):
        """Test connection statistics"""
        stats = self.connection.get_statistics()
        self.assertIsInstance(stats, dict)
        self.assertTrue(stats["connected"])


class TestAudioSocketServer(unittest.TestCase):
    """Test AudioSocketServer class"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = AudioSocketConfig()
        self.server = AudioSocketServer(
            bind_address="127.0.0.1",
            bind_port=0,  # Use random port
            config=self.config,
        )

    def test_server_initialization(self):
        """Test server initialization"""
        self.assertEqual(self.server.bind_address, "127.0.0.1")
        self.assertEqual(self.server.config, self.config)
        self.assertFalse(self.server.running)
        self.assertEqual(self.server.total_connections, 0)
        self.assertEqual(self.server.active_connections, 0)

    def test_server_start_stop(self):
        """Test server start and stop"""
        # Start server in a thread
        server_thread = threading.Thread(target=self.server.start)
        server_thread.daemon = True
        server_thread.start()

        # Wait a bit for server to start
        time.sleep(0.1)

        # Check server is running
        self.assertTrue(self.server.running)
        self.assertIsNotNone(self.server.server_socket)

        # Stop server
        self.server.stop()

        # Check server is stopped
        self.assertFalse(self.server.running)
        self.assertIsNone(self.server.server_socket)

    def test_get_server_statistics(self):
        """Test server statistics"""
        stats = self.server.get_server_statistics()
        self.assertIsInstance(stats, dict)
        self.assertFalse(stats["running"])
        self.assertEqual(stats["total_connections"], 0)
        self.assertEqual(stats["active_connections"], 0)
        self.assertEqual(len(stats["connection_details"]), 0)


class TestEchoServer(unittest.TestCase):
    """Test EchoServer class"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = AudioSocketConfig()
        self.server = EchoServer(
            bind_address="127.0.0.1",
            bind_port=0,  # Use random port
            config=self.config,
        )

    def test_echo_handler(self):
        """Test echo frame handler"""
        # Audio frame should be echoed
        audio_frame = AudioSocketFrame(FrameType.AUDIO, b"test audio")
        response = self.server._echo_handler(audio_frame)
        self.assertEqual(response, audio_frame)

        # Non-audio frame should not be echoed
        uuid_frame = AudioSocketFrame(FrameType.UUID, b"test uuid")
        response = self.server._echo_handler(uuid_frame)
        self.assertIsNone(response)


class TestVoiceBotServer(unittest.TestCase):
    """Test VoiceBotServer class"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = AudioSocketConfig()
        self.audio_responses = {"dtmf_1": b"response1", "dtmf_2": b"response2"}
        self.server = VoiceBotServer(
            bind_address="127.0.0.1",
            bind_port=0,  # Use random port
            config=self.config,
            audio_responses=self.audio_responses,
        )

    def test_voice_bot_handler_audio(self):
        """Test voice bot audio frame handling"""
        audio_frame = AudioSocketFrame(FrameType.AUDIO, b"test audio")
        response = self.server._voice_bot_handler(audio_frame)
        self.assertEqual(response, audio_frame)  # Should echo audio

    def test_voice_bot_handler_dtmf(self):
        """Test voice bot DTMF frame handling"""
        # DTMF with known response
        dtmf_frame = AudioSocketFrame(FrameType.DTMF, b"1")
        response = self.server._voice_bot_handler(dtmf_frame)
        self.assertIsNotNone(response)
        self.assertEqual(response.frame_type, FrameType.AUDIO)

        # DTMF with unknown response
        dtmf_frame = AudioSocketFrame(FrameType.DTMF, b"9")
        response = self.server._voice_bot_handler(dtmf_frame)
        self.assertIsNone(response)

    def test_add_audio_response(self):
        """Test adding audio responses"""
        self.server.add_audio_response("test_response", b"test audio")
        self.assertIn("test_response", self.server.audio_responses)
        self.assertEqual(
            self.server.audio_responses["test_response"], b"test audio"
        )


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(level=logging.WARNING)

    # Run tests
    unittest.main(verbosity=2)
