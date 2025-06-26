"""
AudioSocket Protocol Definition

This module defines the AudioSocket protocol constants and message types
based on the Asterisk implementation in res_audiosocket.c and chan_audiosocket.c.

Protocol Overview:
- All messages start with a 1-byte type field
- Audio messages have a 2-byte length field (big-endian) followed by audio data
- UUID messages have a fixed 16-byte payload
- Error messages have a 1-byte error code
- Hangup messages have no payload
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class MessageType:
    """AudioSocket message types based on Asterisk implementation"""
    
    # UUID message: sent during connection initialization
    # Format: 0x01 + 0x00 + 0x10 + 16-byte UUID
    UUID: int = 0x01
    
    # Audio message: contains PCM audio data
    # Format: 0x10 + 2-byte length + audio data
    AUDIO: int = 0x10
    
    # Hangup message: signals connection termination
    # Format: 0x00 (no payload)
    HANGUP: int = 0x00
    
    # Error message: contains error information
    # Format: 0xFF + 1-byte error code
    ERROR: int = 0xFF


@dataclass(frozen=True)
class ErrorCode:
    """AudioSocket error codes based on Asterisk implementation"""
    
    NONE: int = 0x00      # No error
    HANGUP: int = 0x01    # Called party hung up
    FRAME: int = 0x02     # Failed to forward frame
    MEMORY: int = 0x04    # Memory allocation error


class AudioSocketProtocol:
    """
    AudioSocket protocol implementation based on Asterisk source code.
    
    This class provides methods to parse and construct AudioSocket messages
    according to the protocol defined in res_audiosocket.c.
    """
    
    # Protocol constants
    MESSAGE_TYPES = MessageType()
    ERROR_CODES = ErrorCode()
    
    # Audio format constants (from Asterisk implementation)
    AUDIO_SAMPLE_RATE = 8000      # 8kHz
    AUDIO_BITS_PER_SAMPLE = 16    # 16-bit
    AUDIO_CHANNELS = 1            # Mono
    AUDIO_FRAME_SIZE = 320        # 20ms of 8kHz 16-bit mono = 320 bytes
    
    @staticmethod
    def parse_message(data: bytes) -> Tuple[int, int, bytes]:
        """
        Parse an AudioSocket message according to Asterisk protocol.
        
        Based on ast_audiosocket_receive_frame() in res_audiosocket.c
        
        Args:
            data: Raw message data from socket
            
        Returns:
            Tuple of (message_type, payload_length, payload_data)
            
        Raises:
            ValueError: If message format is invalid
        """
        if len(data) < 1:
            raise ValueError("Message too short: missing type field")
        
        message_type = data[0]
        
        if message_type == AudioSocketProtocol.MESSAGE_TYPES.HANGUP:
            # Hangup message has no payload
            return message_type, 0, b""
        
        if message_type == AudioSocketProtocol.MESSAGE_TYPES.UUID:
            # UUID message: 0x01 + 0x00 + 0x10 + 16-byte UUID
            if len(data) < 19:  # 1 + 2 + 16
                raise ValueError("UUID message too short")
            if data[1] != 0x00 or data[2] != 0x10:
                raise ValueError("Invalid UUID message format")
            return message_type, 16, data[3:19]
        
        if message_type == AudioSocketProtocol.MESSAGE_TYPES.AUDIO:
            # Audio message: 0x10 + 2-byte length + audio data
            if len(data) < 3:
                raise ValueError("Audio message too short: missing length field")
            
            payload_length = int.from_bytes(data[1:3], byteorder='big')
            
            if len(data) < 3 + payload_length:
                raise ValueError(f"Audio message too short: expected {3 + payload_length} bytes, got {len(data)}")
            
            return message_type, payload_length, data[3:3 + payload_length]
        
        if message_type == AudioSocketProtocol.MESSAGE_TYPES.ERROR:
            # Error message: 0xFF + 1-byte error code
            if len(data) < 2:
                raise ValueError("Error message too short: missing error code")
            return message_type, 1, data[1:2]
        
        # Unknown message type
        raise ValueError(f"Unknown message type: 0x{message_type:02x}")
    
    @staticmethod
    def create_uuid_message(uuid_bytes: bytes) -> bytes:
        """
        Create a UUID message according to Asterisk protocol.
        
        Based on ast_audiosocket_init() in res_audiosocket.c
        
        Args:
            uuid_bytes: 16-byte UUID
            
        Returns:
            Complete UUID message bytes
            
        Raises:
            ValueError: If UUID is not 16 bytes
        """
        if len(uuid_bytes) != 16:
            raise ValueError("UUID must be exactly 16 bytes")
        
        # Format: 0x01 + 0x00 + 0x10 + 16-byte UUID
        return bytes([0x01, 0x00, 0x10]) + uuid_bytes
    
    @staticmethod
    def create_audio_message(audio_data: bytes) -> bytes:
        """
        Create an audio message according to Asterisk protocol.
        
        Based on ast_audiosocket_send_frame() in res_audiosocket.c
        
        Args:
            audio_data: Raw audio data (should be 320 bytes for 20ms frame)
            
        Returns:
            Complete audio message bytes
        """
        # Format: 0x10 + 2-byte length + audio data
        length_bytes = len(audio_data).to_bytes(2, byteorder='big')
        return bytes([0x10]) + length_bytes + audio_data
    
    @staticmethod
    def create_hangup_message() -> bytes:
        """
        Create a hangup message according to Asterisk protocol.
        
        Returns:
            Hangup message bytes
        """
        # Format: 0x00 (no payload)
        return bytes([0x00])
    
    @staticmethod
    def create_error_message(error_code: int) -> bytes:
        """
        Create an error message according to Asterisk protocol.
        
        Args:
            error_code: 1-byte error code
            
        Returns:
            Complete error message bytes
        """
        # Format: 0xFF + 1-byte error code
        return bytes([0xFF, error_code])
    
    @staticmethod
    def get_error_description(error_code: int) -> str:
        """
        Get human-readable description of error code.
        
        Args:
            error_code: Error code byte
            
        Returns:
            Error description string
        """
        error_descriptions = {
            AudioSocketProtocol.ERROR_CODES.NONE: "No error",
            AudioSocketProtocol.ERROR_CODES.HANGUP: "Called party hung up",
            AudioSocketProtocol.ERROR_CODES.FRAME: "Failed to forward frame",
            AudioSocketProtocol.ERROR_CODES.MEMORY: "Memory allocation error",
        }
        
        return error_descriptions.get(error_code, f"Unknown error code: 0x{error_code:02x}") 