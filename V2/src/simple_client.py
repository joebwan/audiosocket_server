"""
Simple AudioSocket Client Implementation

This module provides a simple client for the AudioSocket protocol,
capable of connecting to an AudioSocket server and sending audio data.
"""

import socket
import logging
import time
from typing import Optional, Tuple

from protocol import AudioSocketProtocol, MessageType, ErrorCode


class SimpleAudioSocketClient:
    """
    A simple AudioSocket client that can connect to a server and send audio data.
    
    This client implements the basic AudioSocket protocol functionality:
    - Connect to a server
    - Send UUID messages
    - Send audio messages
    - Receive server responses
    - Handle connection cleanup
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
            format='%(asctime)s - %(levelname)s - %(message)s'
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
            
        except socket.error as e:
            self.logger.error(f"Failed to connect to {self.host}:{self.port}: {e}")
            self.is_connected = False
            self.socket = None
            return False
    
    def send_uuid(self, uuid_bytes: bytes) -> bool:
        """
        Send a UUID message to the server.
        
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
                self.logger.error(f"Failed to send complete UUID message: sent {sent} of {len(message)} bytes")
                self.is_connected = False
                return False
            self.logger.info(f"Sent UUID: {uuid_bytes.hex()}")
            return True
        except (socket.error, OSError) as e:
            self.logger.error(f"Failed to send UUID: {e}")
            self.is_connected = False
            return False
    
    def send_audio(self, audio_data: bytes) -> bool:
        """
        Send an audio message to the server.
        
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
                self.logger.error(f"Failed to send complete audio message: sent {sent} of {len(message)} bytes")
                self.is_connected = False
                return False
            self.logger.info(f"Sent audio: {len(audio_data)} bytes")
            return True
        except (socket.error, OSError) as e:
            self.logger.error(f"Failed to send audio: {e}")
            self.is_connected = False
            return False
    
    def send_error(self, error_code: ErrorCode) -> bool:
        """
        Send an error message to the server.
        
        Args:
            error_code: Error code to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_connected or self.socket is None:
            self.logger.error("Cannot send error: not connected to server")
            return False
        
        try:
            # Create error message
            message = AudioSocketProtocol.create_error_message(error_code)
            
            # Send message
            sent = self.socket.send(message)
            if sent != len(message):
                self.logger.error(f"Failed to send complete error message: sent {sent} of {len(message)} bytes")
                self.is_connected = False
                return False
            self.logger.info(f"Sent error: {error_code}")
            return True
        except (socket.error, OSError) as e:
            self.logger.error(f"Failed to send error: {e}")
            self.is_connected = False
            return False
    
    def send_hangup(self) -> bool:
        """
        Send a hangup message to the server.
        
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_connected or self.socket is None:
            self.logger.error("Cannot send hangup: not connected to server")
            return False
        
        try:
            # Create hangup message
            message = AudioSocketProtocol.create_hangup_message()
            
            # Send message
            sent = self.socket.send(message)
            if sent != len(message):
                self.logger.error(f"Failed to send complete hangup message: sent {sent} of {len(message)} bytes")
                self.is_connected = False
                return False
            self.logger.info("Sent hangup")
            return True
        except (socket.error, OSError) as e:
            self.logger.error(f"Failed to send hangup: {e}")
            self.is_connected = False
            return False
    
    def receive_message(self, timeout: float = 5.0) -> Optional[Tuple[MessageType, int, bytes]]:
        """
        Receive a message from the server.
        
        Args:
            timeout: Socket timeout in seconds
            
        Returns:
            Tuple of (message_type, length, payload) if successful, None otherwise
        """
        if not self.is_connected or self.socket is None:
            self.logger.error("Cannot receive message: not connected to server")
            return None
        
        try:
            # Set timeout
            self.socket.settimeout(timeout)
            
            # Receive message header (8 bytes)
            header = self.socket.recv(8)
            if len(header) < 8:
                self.logger.error("Incomplete message header received")
                return None
            
            # Parse header
            msg_type = int.from_bytes(header[0:4], byteorder='little')
            length = int.from_bytes(header[4:8], byteorder='little')
            
            # Receive payload if present
            payload = b""
            if length > 0:
                payload = self.socket.recv(length)
                if len(payload) < length:
                    self.logger.error("Incomplete message payload received")
                    return None
            
            message_type = MessageType(msg_type)
            self.logger.info(f"Received message: {message_type.name}, length: {length}")
            
            return (message_type, length, payload)
            
        except socket.timeout:
            self.logger.warning("Timeout waiting for message from server")
            return None
        except socket.error as e:
            self.logger.error(f"Failed to receive message: {e}")
            self.is_connected = False
            return None
    
    def close(self):
        """Close the connection and clean up resources."""
        if self.socket is not None:
            try:
                self.socket.close()
                self.logger.info("Connection closed")
            except socket.error as e:
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