"""
Simple AudioSocket Client Implementation

This module provides a simple client for the AudioSocket protocol,
capable of connecting to an AudioSocket server and sending audio data.
This client mocks the Asterisk AudioSocket behavior as defined in
res_audiosocket.c and chan_audiosocket.c.
"""

import logging
import socket
import time
from typing import Optional, Tuple

from protocol import AudioSocketProtocol, ErrorCode, MessageType


class SimpleAudioSocketClient:
    """
    A simple AudioSocket client that mocks Asterisk AudioSocket behavior.

    This client implements the core AudioSocket protocol functionality that
    Asterisk uses:
    - Connect to a server
    - Send UUID messages (ast_audiosocket_init)
    - Send audio messages (ast_audiosocket_send_frame)
    - Receive audio messages (ast_audiosocket_receive_frame)
    - Handle connection cleanup

    Note: Asterisk does NOT send hangup or error messages to the server.
    """

    def __init__(self, host: str, port: int):
        """
        Initialize the AudioSocket client.

        Args:
            host: Server hostname or IP address
            port: Server port number
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.is_connected = False

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """
        Connect to the AudioSocket server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # 5 second timeout

            # Connect to server
            self.socket.connect((self.host, self.port))
            self.is_connected = True

            self.logger.info(f"Connected to server at {self.host}:{self.port}")
            return True

        except OSError as e:
            self.logger.error(
                f"Failed to connect to {self.host}:{self.port}: {e}"
            )
            self.is_connected = False
            self.socket = None
            return False

    def send_uuid(self, uuid_bytes: bytes) -> bool:
        """
        Send a UUID message to the server (ast_audiosocket_init).

        Args:
            uuid_bytes: 16-byte UUID in binary format

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_connected or self.socket is None:
            self.logger.error("Cannot send UUID: not connected to server")
            return False

        try:
            # Create UUID message
            message = AudioSocketProtocol.create_uuid_message(uuid_bytes)

            # Send message
            sent = self.socket.send(message)
            if sent != len(message):
                self.logger.error(
                    f"Failed to send complete UUID message: sent {sent} of {len(message)} bytes"
                )
                self.is_connected = False
                return False
            self.logger.info(f"Sent UUID: {uuid_bytes.hex()}")
            return True
        except OSError as e:
            self.logger.error(f"Failed to send UUID: {e}")
            self.is_connected = False
            return False

    def send_audio(self, audio_data: bytes) -> bool:
        """
        Send an audio message to the server (ast_audiosocket_send_frame).

        Args:
            audio_data: Raw audio data bytes

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_connected or self.socket is None:
            self.logger.error("Cannot send audio: not connected to server")
            return False

        try:
            # Create audio message
            message = AudioSocketProtocol.create_audio_message(audio_data)

            # Send message
            sent = self.socket.send(message)
            if sent != len(message):
                self.logger.error(
                    f"Failed to send complete audio message: sent {sent} of {len(message)} bytes"
                )
                self.is_connected = False
                return False
            self.logger.info(f"Sent audio: {len(audio_data)} bytes")
            return True
        except OSError as e:
            self.logger.error(f"Failed to send audio: {e}")
            self.is_connected = False
            return False

    def receive_audio(self, timeout: float = 5.0) -> Optional[bytes]:
        """
        Receive an audio message from the server (ast_audiosocket_receive_frame).

        Args:
            timeout: Socket timeout in seconds

        Returns:
            Audio data bytes if successful, None otherwise
        """
        if not self.is_connected or self.socket is None:
            self.logger.error("Cannot receive audio: not connected to server")
            return None

        try:
            # Set timeout
            self.socket.settimeout(timeout)

            # Receive data
            data = self.socket.recv(1024)
            if not data:
                return None

            # Parse message
            try:
                msg_type, length, payload = AudioSocketProtocol.parse_message(
                    data
                )

                if msg_type == MessageType.AUDIO:
                    self.logger.info(f"Received audio: {len(payload)} bytes")
                    return payload
                elif msg_type == MessageType.HANGUP:
                    self.logger.info("Received hangup from server")
                    self.is_connected = False
                    return None
                else:
                    self.logger.warning(
                        f"Received non-audio message type: {msg_type}"
                    )
                    return None

            except ValueError as e:
                self.logger.error(f"Failed to parse message: {e}")
                return None

        except socket.timeout:
            self.logger.warning("Timeout waiting for audio from server")
            return None
        except OSError as e:
            self.logger.error(f"Failed to receive audio: {e}")
            self.is_connected = False
            return None

    def close(self):
        """Close the connection and clean up resources."""
        if self.socket is not None:
            try:
                self.socket.close()
                self.logger.info("Connection closed")
            except OSError as e:
                self.logger.error(f"Error closing socket: {e}")
            finally:
                self.socket = None
                self.is_connected = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
