#!/usr/bin/env python3
"""
AudioSocket Protocol Implementation

This module implements the complete Asterisk AudioSocket protocol specification
as defined in chan_audiosocket.c and res_audiosocket.c.

Protocol Specification:
- Frame Format: [1 byte type][2 bytes length][variable payload]
- Audio Format: 8kHz, 16-bit, mono PCM (little-endian)
- Frame Duration: 20ms (320 bytes)
- Frame Rate: 50 FPS

Reference: https://github.com/asterisk/asterisk/blob/certified/20.7/channels/chan_audiosocket.c
"""

import logging
import socket
import struct
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Tuple, Union


class FrameType(IntEnum):
    """AudioSocket frame types according to specification"""

    HANGUP = 0x00  # Terminate the connection
    UUID = 0x01  # Payload contains UUID (16-byte binary)
    SILENCE = 0x02  # Payload contains silence indicator
    DTMF = 0x03  # Payload is 1 byte (ascii) DTMF digit
    AUDIO = 0x10  # Payload is signed linear, 16-bit, 8kHz, mono PCM (little-endian)
    ERROR = 0xFF  # An error has occurred; payload is optional error code


class ErrorCode(IntEnum):
    """AudioSocket error codes according to specification"""

    NONE = 0x00  # No error
    HANGUP = 0x01  # Called party hungup
    FRAME = 0x02  # Failed to forward frame
    MEMORY = 0x04  # Memory allocation error


@dataclass
class AudioSocketFrame:
    """Represents a complete AudioSocket frame"""

    frame_type: FrameType
    payload: bytes

    @property
    def length(self) -> int:
        """Get the payload length"""
        return len(self.payload)

    def to_bytes(self) -> bytes:
        """Convert frame to wire format"""
        return struct.pack(">B H", self.frame_type, self.length) + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "AudioSocketFrame":
        """Create frame from wire format"""
        if len(data) < 3:
            raise ValueError(f"Frame data too short: {len(data)} bytes")

        frame_type = FrameType(data[0])
        length = struct.unpack(">H", data[1:3])[0]

        if len(data) < 3 + length:
            raise ValueError(
                f"Incomplete frame: expected {3 + length} bytes, got {len(data)}"
            )

        payload = data[3 : 3 + length]
        return cls(frame_type, payload)

    def __str__(self) -> str:
        return f"AudioSocketFrame(type={self.frame_type.name}, length={self.length})"


@dataclass
class AudioSocketConfig:
    """Configuration for AudioSocket protocol"""

    sample_rate: int = 8000
    channels: int = 1
    bit_depth: int = 16
    frame_duration_ms: int = 20
    ulaw2lin: bool = True

    @property
    def frame_size(self) -> int:
        """Calculate frame size in bytes"""
        return (
            self.sample_rate
            * self.frame_duration_ms
            // 1000
            * self.channels
            * self.bit_depth
            // 8
        )

    @property
    def frame_interval(self) -> float:
        """Calculate frame interval in seconds"""
        return self.frame_duration_ms / 1000.0

    @property
    def frames_per_second(self) -> int:
        """Calculate frames per second"""
        return 1000 // self.frame_duration_ms


class AudioSocketProtocol:
    """
    AudioSocket Protocol Implementation

    This class provides a complete implementation of the Asterisk AudioSocket protocol
    with proper frame parsing, message handling, and error management.
    """

    def __init__(self, config: Optional[AudioSocketConfig] = None):
        """
        Initialize AudioSocket protocol handler

        Args:
            config: Protocol configuration (uses defaults if None)
        """
        self.config = config or AudioSocketConfig()
        self.logger = logging.getLogger(__name__)

        # Connection state
        self.connected = False
        self.uuid: Optional[str] = None
        self.peer_addr: Optional[tuple[str, int]] = None

        # Statistics
        self.frame_count = 0
        self.bytes_received = 0
        self.bytes_sent = 0
        self.start_time: Optional[float] = None
        self.last_frame_time: Optional[float] = None

        # Error tracking
        self.error_count = 0
        self.last_error: Optional[ErrorCode] = None

    def create_frame(
        self, frame_type: FrameType, payload: bytes = b""
    ) -> AudioSocketFrame:
        """
        Create an AudioSocket frame

        Args:
            frame_type: Type of frame to create
            payload: Frame payload data

        Returns:
            AudioSocketFrame instance
        """
        return AudioSocketFrame(frame_type, payload)

    def create_audio_frame(self, audio_data: bytes) -> AudioSocketFrame:
        """
        Create an audio frame with proper validation

        Args:
            audio_data: Raw audio data (should be frame_size bytes)

        Returns:
            AudioSocketFrame with audio payload
        """
        expected_size = self.config.frame_size
        if len(audio_data) != expected_size:
            self.logger.warning(
                f"Audio frame size mismatch: expected {expected_size}, got {len(audio_data)}"
            )
            # Pad or truncate to expected size
            if len(audio_data) < expected_size:
                audio_data += b"\x00" * (expected_size - len(audio_data))
            else:
                audio_data = audio_data[:expected_size]

        return self.create_frame(FrameType.AUDIO, audio_data)

    def create_uuid_frame(self, uuid: str) -> AudioSocketFrame:
        """
        Create a UUID frame

        Args:
            uuid: UUID string (will be converted to 16-byte binary)

        Returns:
            AudioSocketFrame with UUID payload
        """
        # Convert UUID string to 16-byte binary
        uuid_bytes = bytes.fromhex(uuid.replace("-", ""))
        if len(uuid_bytes) != 16:
            raise ValueError(f"Invalid UUID length: {len(uuid_bytes)} bytes")

        return self.create_frame(FrameType.UUID, uuid_bytes)

    def create_hangup_frame(self) -> AudioSocketFrame:
        """Create a hangup frame"""
        return self.create_frame(FrameType.HANGUP)

    def create_silence_frame(self) -> AudioSocketFrame:
        """Create a silence frame"""
        return self.create_frame(FrameType.SILENCE)

    def create_error_frame(self, error_code: ErrorCode) -> AudioSocketFrame:
        """
        Create an error frame

        Args:
            error_code: Error code to send

        Returns:
            AudioSocketFrame with error payload
        """
        return self.create_frame(FrameType.ERROR, bytes([error_code]))

    def create_dtmf_frame(self, digit: str) -> AudioSocketFrame:
        """
        Create a DTMF frame

        Args:
            digit: DTMF digit (0-9, *, #, A-D)

        Returns:
            AudioSocketFrame with DTMF payload
        """
        if len(digit) != 1 or digit not in "0123456789*#ABCD":
            raise ValueError(f"Invalid DTMF digit: {digit}")

        return self.create_frame(FrameType.DTMF, digit.encode("ascii"))

    def parse_frame(self, data: bytes) -> AudioSocketFrame:
        """
        Parse raw data into an AudioSocket frame

        Args:
            data: Raw frame data from socket

        Returns:
            Parsed AudioSocketFrame

        Raises:
            ValueError: If frame data is invalid
        """
        try:
            frame = AudioSocketFrame.from_bytes(data)
            self._update_statistics(frame, received=True)
            return frame
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Frame parsing error: {e}")
            raise

    def handle_frame(
        self, frame: AudioSocketFrame
    ) -> Optional[AudioSocketFrame]:
        """
        Handle a received frame and optionally return a response frame

        Args:
            frame: Received AudioSocket frame

        Returns:
            Response frame to send (None if no response needed)
        """
        self.logger.debug(f"Handling frame: {frame}")

        if frame.frame_type == FrameType.AUDIO:
            return self._handle_audio_frame(frame)
        elif frame.frame_type == FrameType.UUID:
            return self._handle_uuid_frame(frame)
        elif frame.frame_type == FrameType.DTMF:
            return self._handle_dtmf_frame(frame)
        elif frame.frame_type == FrameType.ERROR:
            return self._handle_error_frame(frame)
        elif frame.frame_type == FrameType.HANGUP:
            return self._handle_hangup_frame(frame)
        elif frame.frame_type == FrameType.SILENCE:
            return self._handle_silence_frame(frame)
        else:
            self.logger.warning(
                f"Unknown frame type: 0x{frame.frame_type:02x}"
            )
            return None

    def _handle_audio_frame(
        self, frame: AudioSocketFrame
    ) -> Optional[AudioSocketFrame]:
        """Handle audio frame - echo back by default"""
        # Default behavior: echo audio back
        return self.create_audio_frame(frame.payload)

    def _handle_uuid_frame(self, frame: AudioSocketFrame) -> None:
        """Handle UUID frame - store UUID"""
        if len(frame.payload) == 16:
            self.uuid = frame.payload.hex()
            self.logger.info(f"Received UUID: {self.uuid}")
        else:
            self.logger.warning(
                f"Invalid UUID length: {len(frame.payload)} bytes"
            )

    def _handle_dtmf_frame(self, frame: AudioSocketFrame) -> None:
        """Handle DTMF frame - log digit"""
        if frame.payload:
            digit = frame.payload.decode("ascii", errors="ignore")
            self.logger.info(f"Received DTMF: {digit}")

    def _handle_error_frame(self, frame: AudioSocketFrame) -> None:
        """Handle error frame - log error"""
        if frame.payload:
            try:
                error_code = ErrorCode(frame.payload[0])
                self.last_error = error_code
                self.logger.error(f"Received error: {error_code.name}")
            except ValueError:
                self.logger.error(
                    f"Unknown error code: 0x{frame.payload[0]:02x}"
                )

    def _handle_hangup_frame(self, frame: AudioSocketFrame) -> None:
        """Handle hangup frame - mark as disconnected"""
        self.connected = False
        self.logger.info("Received hangup request")

    def _handle_silence_frame(
        self, frame: AudioSocketFrame
    ) -> Optional[AudioSocketFrame]:
        """Handle silence frame - respond with silence"""
        return self.create_silence_frame()

    def _update_statistics(
        self, frame: AudioSocketFrame, received: bool = True
    ) -> None:
        """Update protocol statistics"""
        current_time = time.time()

        if self.start_time is None:
            self.start_time = current_time

        self.last_frame_time = current_time
        self.frame_count += 1

        frame_size = len(frame.to_bytes())
        if received:
            self.bytes_received += frame_size
        else:
            self.bytes_sent += frame_size

    def get_statistics(self) -> dict:
        """Get protocol statistics"""
        if self.start_time is None:
            return {
                "connected": self.connected,
                "frame_count": self.frame_count,
                "bytes_received": self.bytes_received,
                "bytes_sent": self.bytes_sent,
                "error_count": self.error_count,
                "last_error": (
                    self.last_error.name if self.last_error else None
                ),
                "uuid": self.uuid,
                "peer_addr": self.peer_addr,
            }

        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0

        return {
            "connected": self.connected,
            "frame_count": self.frame_count,
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
            "error_count": self.error_count,
            "last_error": self.last_error.name if self.last_error else None,
            "uuid": self.uuid,
            "peer_addr": self.peer_addr,
            "elapsed_time": elapsed,
            "frames_per_second": fps,
            "expected_fps": self.config.frames_per_second,
            "frame_rate_ratio": (
                fps / self.config.frames_per_second
                if self.config.frames_per_second > 0
                else 0
            ),
        }

    def reset_statistics(self) -> None:
        """Reset all statistics"""
        self.frame_count = 0
        self.bytes_received = 0
        self.bytes_sent = 0
        self.start_time = None
        self.last_frame_time = None
        self.error_count = 0
        self.last_error = None

    def validate_audio_data(self, audio_data: bytes) -> bool:
        """
        Validate audio data against protocol requirements

        Args:
            audio_data: Raw audio data to validate

        Returns:
            True if valid, False otherwise
        """
        expected_size = self.config.frame_size

        if len(audio_data) != expected_size:
            self.logger.warning(
                f"Audio data size mismatch: expected {expected_size}, got {len(audio_data)}"
            )
            return False

        # Check for all-zero data (silence)
        if all(b == 0 for b in audio_data):
            self.logger.debug("Audio data is silence")

        return True

    def create_silence_audio(self) -> bytes:
        """Create silence audio data of the correct frame size"""
        return b"\x00" * self.config.frame_size

    def __str__(self) -> str:
        stats = self.get_statistics()
        return (
            f"AudioSocketProtocol(connected={self.connected}, "
            f"frames={stats['frame_count']}, "
            f"fps={stats.get('frames_per_second', 0):.1f})"
        )


class AudioSocketConnection:
    """
    AudioSocket connection handler with protocol implementation
    """

    def __init__(
        self,
        socket_conn: socket.socket,
        peer_addr: tuple[str, int],
        config: Optional[AudioSocketConfig] = None,
    ):
        """
        Initialize AudioSocket connection

        Args:
            socket_conn: Underlying socket connection
            peer_addr: Peer address tuple (host, port)
            config: Protocol configuration
        """
        self.socket = socket_conn
        self.peer_addr = peer_addr
        self.protocol = AudioSocketProtocol(config)
        self.protocol.connected = True
        self.protocol.peer_addr = peer_addr

        self.logger = logging.getLogger(
            f"{__name__}.{peer_addr[0]}:{peer_addr[1]}"
        )
        self.logger.info("AudioSocket connection established")

    def read_frame(self) -> Optional[AudioSocketFrame]:
        """
        Read a frame from the socket

        Returns:
            Parsed AudioSocketFrame or None if connection closed
        """
        try:
            # Read frame header (3 bytes)
            header_data = self._read_exact(3)
            if not header_data:
                self.protocol.connected = False
                return None

            frame_type = FrameType(header_data[0])
            length = struct.unpack(">H", header_data[1:3])[0]

            # Read frame payload
            payload = self._read_exact(length) if length > 0 else b""
            if payload is None:
                self.protocol.connected = False
                return None

            # Create frame
            frame = AudioSocketFrame(frame_type, payload)
            self.protocol._update_statistics(frame, received=True)

            return frame

        except (ConnectionError, OSError) as e:
            self.logger.info(f"Connection closed: {e}")
            self.protocol.connected = False
            return None
        except Exception as e:
            self.logger.error(f"Error reading frame: {e}")
            return None

    def write_frame(self, frame: AudioSocketFrame) -> bool:
        """
        Write a frame to the socket

        Args:
            frame: AudioSocketFrame to send

        Returns:
            True if successful, False otherwise
        """
        try:
            frame_data = frame.to_bytes()
            self.socket.sendall(frame_data)
            self.protocol._update_statistics(frame, received=False)
            return True

        except (ConnectionError, OSError) as e:
            self.logger.error(f"Error writing frame: {e}")
            self.protocol.connected = False
            return False

    def _read_exact(self, num_bytes: int) -> Optional[bytes]:
        """Read exactly num_bytes from socket"""
        data = b""
        while len(data) < num_bytes:
            chunk = self.socket.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def close(self) -> None:
        """Close the connection"""
        self.protocol.connected = False
        try:
            self.socket.close()
        except OSError:
            pass
        self.logger.info("AudioSocket connection closed")

    def get_statistics(self) -> dict:
        """Get connection statistics"""
        return self.protocol.get_statistics()
