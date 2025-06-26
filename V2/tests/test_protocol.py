"""
Test suite for AudioSocket Protocol

These tests validate the protocol implementation against the Asterisk source code
in res_audiosocket.c and chan_audiosocket.c.
"""

import unittest
import uuid
from unittest.mock import Mock

# Add src to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from protocol import AudioSocketProtocol, MessageType, ErrorCode


class TestMessageTypes(unittest.TestCase):
    """Test message type constants match Asterisk implementation"""
    
    def test_message_type_values(self):
        """Test that message types match Asterisk source code"""
        self.assertEqual(MessageType.UUID, 0x01)
        self.assertEqual(MessageType.AUDIO, 0x10)
        self.assertEqual(MessageType.HANGUP, 0x00)
        self.assertEqual(MessageType.ERROR, 0xFF)


class TestErrorCodes(unittest.TestCase):
    """Test error code constants match Asterisk implementation"""
    
    def test_error_code_values(self):
        """Test that error codes match Asterisk source code"""
        self.assertEqual(ErrorCode.NONE, 0x00)
        self.assertEqual(ErrorCode.HANGUP, 0x01)
        self.assertEqual(ErrorCode.FRAME, 0x02)
        self.assertEqual(ErrorCode.MEMORY, 0x04)


class TestAudioSocketProtocolConstants(unittest.TestCase):
    """Test protocol constants"""
    
    def test_audio_format_constants(self):
        """Test audio format constants match Asterisk implementation"""
        self.assertEqual(AudioSocketProtocol.AUDIO_SAMPLE_RATE, 8000)
        self.assertEqual(AudioSocketProtocol.AUDIO_BITS_PER_SAMPLE, 16)
        self.assertEqual(AudioSocketProtocol.AUDIO_CHANNELS, 1)
        self.assertEqual(AudioSocketProtocol.AUDIO_FRAME_SIZE, 320)


class TestMessageParsing(unittest.TestCase):
    """Test message parsing functionality"""
    
    def test_parse_uuid_message(self):
        """Test parsing UUID message according to Asterisk format"""
        # Create UUID message: 0x01 + 0x00 + 0x10 + 16-byte UUID
        test_uuid = uuid.uuid4().bytes
        uuid_message = bytes([0x01, 0x00, 0x10]) + test_uuid
        
        msg_type, length, payload = AudioSocketProtocol.parse_message(uuid_message)
        
        self.assertEqual(msg_type, MessageType.UUID)
        self.assertEqual(length, 16)
        self.assertEqual(payload, test_uuid)
    
    def test_parse_audio_message(self):
        """Test parsing audio message according to Asterisk format"""
        # Create audio message: 0x10 + 2-byte length + audio data
        audio_data = b"\x00" * 320  # 320 bytes of silence
        audio_message = bytes([0x10]) + (320).to_bytes(2, 'big') + audio_data
        
        msg_type, length, payload = AudioSocketProtocol.parse_message(audio_message)
        
        self.assertEqual(msg_type, MessageType.AUDIO)
        self.assertEqual(length, 320)
        self.assertEqual(payload, audio_data)
    
    def test_parse_hangup_message(self):
        """Test parsing hangup message"""
        hangup_message = bytes([0x00])
        
        msg_type, length, payload = AudioSocketProtocol.parse_message(hangup_message)
        
        self.assertEqual(msg_type, MessageType.HANGUP)
        self.assertEqual(length, 0)
        self.assertEqual(payload, b"")
    
    def test_parse_error_message(self):
        """Test parsing error message"""
        error_message = bytes([0xFF, 0x01])  # Hangup error
        
        msg_type, length, payload = AudioSocketProtocol.parse_message(error_message)
        
        self.assertEqual(msg_type, MessageType.ERROR)
        self.assertEqual(length, 1)
        self.assertEqual(payload, b"\x01")
    
    def test_parse_message_too_short(self):
        """Test parsing fails for messages that are too short"""
        with self.assertRaises(ValueError, msg="Message too short: missing type field"):
            AudioSocketProtocol.parse_message(b"")
    
    def test_parse_uuid_message_too_short(self):
        """Test parsing fails for incomplete UUID message"""
        incomplete_uuid = bytes([0x01, 0x00])  # Missing 0x10 and UUID
        with self.assertRaises(ValueError, msg="UUID message too short"):
            AudioSocketProtocol.parse_message(incomplete_uuid)
    
    def test_parse_uuid_message_invalid_format(self):
        """Test parsing fails for UUID message with wrong format"""
        # Wrong format: 0x01 + 0x01 + 0x10 + UUID (should be 0x00, not 0x01)
        test_uuid = uuid.uuid4().bytes
        invalid_uuid_message = bytes([0x01, 0x01, 0x10]) + test_uuid
        
        with self.assertRaises(ValueError, msg="Invalid UUID message format"):
            AudioSocketProtocol.parse_message(invalid_uuid_message)
    
    def test_parse_audio_message_too_short(self):
        """Test parsing fails for incomplete audio message"""
        incomplete_audio = bytes([0x10, 0x01])  # Missing second length byte
        with self.assertRaises(ValueError, msg="Audio message too short: missing length field"):
            AudioSocketProtocol.parse_message(incomplete_audio)
    
    def test_parse_audio_message_incomplete_payload(self):
        """Test parsing fails for audio message with incomplete payload"""
        # Length says 320 bytes but only provide 100
        incomplete_audio = bytes([0x10]) + (320).to_bytes(2, 'big') + b"\x00" * 100
        
        with self.assertRaises(ValueError):
            AudioSocketProtocol.parse_message(incomplete_audio)
    
    def test_parse_error_message_too_short(self):
        """Test parsing fails for incomplete error message"""
        incomplete_error = bytes([0xFF])  # Missing error code
        with self.assertRaises(ValueError, msg="Error message too short: missing error code"):
            AudioSocketProtocol.parse_message(incomplete_error)
    
    def test_parse_unknown_message_type(self):
        """Test parsing fails for unknown message type"""
        unknown_message = bytes([0x99])  # Unknown type
        with self.assertRaises(ValueError, msg="Unknown message type: 0x99"):
            AudioSocketProtocol.parse_message(unknown_message)


class TestMessageCreation(unittest.TestCase):
    """Test message creation functionality"""
    
    def test_create_uuid_message(self):
        """Test creating UUID message according to Asterisk format"""
        test_uuid = uuid.uuid4().bytes
        uuid_message = AudioSocketProtocol.create_uuid_message(test_uuid)
        
        # Should be: 0x01 + 0x00 + 0x10 + 16-byte UUID
        expected = bytes([0x01, 0x00, 0x10]) + test_uuid
        self.assertEqual(uuid_message, expected)
    
    def test_create_uuid_message_invalid_length(self):
        """Test creating UUID message fails with wrong UUID length"""
        invalid_uuid = b"\x00" * 15  # 15 bytes instead of 16
        with self.assertRaises(ValueError, msg="UUID must be exactly 16 bytes"):
            AudioSocketProtocol.create_uuid_message(invalid_uuid)
    
    def test_create_audio_message(self):
        """Test creating audio message according to Asterisk format"""
        audio_data = b"\x00" * 320
        audio_message = AudioSocketProtocol.create_audio_message(audio_data)
        
        # Should be: 0x10 + 2-byte length + audio data
        expected = bytes([0x10]) + (320).to_bytes(2, 'big') + audio_data
        self.assertEqual(audio_message, expected)
    
    def test_create_audio_message_different_length(self):
        """Test creating audio message with different payload length"""
        audio_data = b"\x00" * 160  # 160 bytes
        audio_message = AudioSocketProtocol.create_audio_message(audio_data)
        
        expected = bytes([0x10]) + (160).to_bytes(2, 'big') + audio_data
        self.assertEqual(audio_message, expected)
    
    def test_create_hangup_message(self):
        """Test creating hangup message"""
        hangup_message = AudioSocketProtocol.create_hangup_message()
        expected = bytes([0x00])
        self.assertEqual(hangup_message, expected)
    
    def test_create_error_message(self):
        """Test creating error message"""
        error_message = AudioSocketProtocol.create_error_message(0x01)
        expected = bytes([0xFF, 0x01])
        self.assertEqual(error_message, expected)


class TestErrorDescriptions(unittest.TestCase):
    """Test error description functionality"""
    
    def test_get_error_description_known_codes(self):
        """Test getting descriptions for known error codes"""
        self.assertEqual(
            AudioSocketProtocol.get_error_description(0x00),
            "No error"
        )
        self.assertEqual(
            AudioSocketProtocol.get_error_description(0x01),
            "Called party hung up"
        )
        self.assertEqual(
            AudioSocketProtocol.get_error_description(0x02),
            "Failed to forward frame"
        )
        self.assertEqual(
            AudioSocketProtocol.get_error_description(0x04),
            "Memory allocation error"
        )
    
    def test_get_error_description_unknown_code(self):
        """Test getting description for unknown error code"""
        description = AudioSocketProtocol.get_error_description(0x99)
        self.assertEqual(description, "Unknown error code: 0x99")


class TestProtocolRoundTrip(unittest.TestCase):
    """Test round-trip message creation and parsing"""
    
    def test_uuid_message_round_trip(self):
        """Test UUID message creation and parsing round-trip"""
        test_uuid = uuid.uuid4().bytes
        created_message = AudioSocketProtocol.create_uuid_message(test_uuid)
        msg_type, length, payload = AudioSocketProtocol.parse_message(created_message)
        
        self.assertEqual(msg_type, MessageType.UUID)
        self.assertEqual(length, 16)
        self.assertEqual(payload, test_uuid)
    
    def test_audio_message_round_trip(self):
        """Test audio message creation and parsing round-trip"""
        audio_data = b"\x00" * 320
        created_message = AudioSocketProtocol.create_audio_message(audio_data)
        msg_type, length, payload = AudioSocketProtocol.parse_message(created_message)
        
        self.assertEqual(msg_type, MessageType.AUDIO)
        self.assertEqual(length, 320)
        self.assertEqual(payload, audio_data)
    
    def test_hangup_message_round_trip(self):
        """Test hangup message creation and parsing round-trip"""
        created_message = AudioSocketProtocol.create_hangup_message()
        msg_type, length, payload = AudioSocketProtocol.parse_message(created_message)
        
        self.assertEqual(msg_type, MessageType.HANGUP)
        self.assertEqual(length, 0)
        self.assertEqual(payload, b"")
    
    def test_error_message_round_trip(self):
        """Test error message creation and parsing round-trip"""
        created_message = AudioSocketProtocol.create_error_message(0x01)
        msg_type, length, payload = AudioSocketProtocol.parse_message(created_message)
        
        self.assertEqual(msg_type, MessageType.ERROR)
        self.assertEqual(length, 1)
        self.assertEqual(payload, b"\x01")


if __name__ == '__main__':
    unittest.main() 