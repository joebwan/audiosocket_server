#!/usr/bin/env python3
"""
AudioSocket Server Implementation

This module provides a complete AudioSocket server implementation using the
AudioSocket protocol class for proper communication with Asterisk.
"""

import logging
import socket
import threading
import time
from typing import Any, Callable, Optional

from audiosocket_protocol import (
    AudioSocketConfig,
    AudioSocketConnection,
    AudioSocketFrame,
    AudioSocketProtocol,
    ErrorCode,
    FrameType,
)


class AudioSocketServer:
    """
    AudioSocket Server with protocol-compliant implementation

    This server properly implements the Asterisk AudioSocket protocol and can
    handle multiple simultaneous connections with proper frame parsing and handling.
    """

    def __init__(
        self,
        bind_address: str = "0.0.0.0",
        bind_port: int = 6050,
        config: Optional[AudioSocketConfig] = None,
        frame_handler: Optional[
            Callable[[AudioSocketFrame], Optional[AudioSocketFrame]]
        ] = None,
    ):
        """
        Initialize AudioSocket server

        Args:
            bind_address: Address to bind to (default: 0.0.0.0)
            bind_port: Port to bind to (default: 6050)
            config: Protocol configuration
            frame_handler: Custom frame handler function
        """
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.config = config or AudioSocketConfig()
        self.frame_handler = frame_handler

        # Server state
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.connections: list[AudioSocketConnection] = []
        self.connection_lock = threading.Lock()

        # Statistics
        self.total_connections = 0
        self.active_connections = 0

        # Logging
        self.logger = logging.getLogger(__name__)

        # Set up logging if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def start(self) -> None:
        """Start the AudioSocket server"""
        if self.running:
            self.logger.warning("Server is already running")
            return

        try:
            # Create server socket
            self.server_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )
            self.server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
            self.server_socket.bind((self.bind_address, self.bind_port))
            self.server_socket.listen(5)

            self.running = True
            self.logger.info(
                f"AudioSocket server started on {self.bind_address}:{self.bind_port}"
            )
            self.logger.info(
                f"Audio configuration: {self.config.sample_rate}Hz, "
                f"{self.config.channels} channel(s), {self.config.bit_depth}-bit, "
                f"{self.config.frame_duration_ms}ms frames"
            )

            # Start connection acceptance loop
            self._accept_connections()

        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            self.running = False
            raise

    def stop(self) -> None:
        """Stop the AudioSocket server"""
        if not self.running:
            return

        self.logger.info("Stopping AudioSocket server...")
        self.running = False

        # Close all connections
        with self.connection_lock:
            for conn in self.connections[:]:
                conn.close()
            self.connections.clear()

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        self.logger.info("AudioSocket server stopped")

    def _accept_connections(self) -> None:
        """Accept incoming connections"""
        while self.running:
            try:
                # Accept connection with timeout
                self.server_socket.settimeout(1.0)
                client_socket, client_addr = self.server_socket.accept()

                # Create connection handler
                connection = AudioSocketConnection(
                    client_socket, client_addr, self.config
                )

                # Start connection handler thread
                thread = threading.Thread(
                    target=self._handle_connection,
                    args=(connection,),
                    daemon=True,
                )
                thread.start()

                # Track connection
                with self.connection_lock:
                    self.connections.append(connection)
                    self.total_connections += 1
                    self.active_connections += 1

                self.logger.info(
                    f"New connection from {client_addr} (total: {self.total_connections})"
                )

            except socket.timeout:
                # Timeout is expected, continue loop
                continue
            except OSError as e:
                if self.running:
                    self.logger.error(f"Error accepting connection: {e}")
                break
            except Exception as e:
                self.logger.error(
                    f"Unexpected error accepting connection: {e}"
                )

    def _handle_connection(self, connection: AudioSocketConnection) -> None:
        """Handle a single connection"""
        try:
            self.logger.info(
                f"Starting connection handler for {connection.peer_addr}"
            )

            while connection.protocol.connected and self.running:
                # Read frame from client
                frame = connection.read_frame()
                if frame is None:
                    break

                # Handle frame
                response_frame = self._process_frame(connection, frame)

                # Send response if provided
                if response_frame:
                    if not connection.write_frame(response_frame):
                        break

                # Log statistics periodically
                if connection.protocol.frame_count % 100 == 0:
                    stats = connection.get_statistics()
                    self.logger.debug(
                        f"Connection {connection.peer_addr}: "
                        f"frames={stats['frame_count']}, "
                        f"fps={stats.get('frames_per_second', 0):.1f}"
                    )

        except Exception as e:
            self.logger.error(
                f"Error handling connection {connection.peer_addr}: {e}"
            )

        finally:
            # Clean up connection
            connection.close()
            with self.connection_lock:
                if connection in self.connections:
                    self.connections.remove(connection)
                self.active_connections -= 1

            self.logger.info(
                f"Connection {connection.peer_addr} closed "
                f"(active: {self.active_connections})"
            )

    def _process_frame(
        self, connection: AudioSocketConnection, frame: AudioSocketFrame
    ) -> Optional[AudioSocketFrame]:
        """Process a received frame and return response frame"""
        try:
            # Use custom handler if provided
            if self.frame_handler:
                return self.frame_handler(frame)

            # Use default protocol handler
            return connection.protocol.handle_frame(frame)

        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            return None

    def get_server_statistics(self) -> dict:
        """Get server statistics"""
        with self.connection_lock:
            return {
                "running": self.running,
                "bind_address": self.bind_address,
                "bind_port": self.bind_port,
                "total_connections": self.total_connections,
                "active_connections": self.active_connections,
                "connection_details": [
                    {
                        "peer_addr": conn.peer_addr,
                        "uuid": conn.protocol.uuid,
                        "frame_count": conn.protocol.frame_count,
                        "connected": conn.protocol.connected,
                    }
                    for conn in self.connections
                ],
            }

    def broadcast_frame(self, frame: AudioSocketFrame) -> int:
        """
        Broadcast a frame to all connected clients

        Args:
            frame: Frame to broadcast

        Returns:
            Number of clients that received the frame
        """
        sent_count = 0
        with self.connection_lock:
            for conn in self.connections[
                :
            ]:  # Copy list to avoid modification during iteration
                if conn.protocol.connected:
                    if conn.write_frame(frame):
                        sent_count += 1
                    else:
                        # Remove disconnected connection
                        self.connections.remove(conn)
                        self.active_connections -= 1

        return sent_count

    def send_to_uuid(self, uuid: str, frame: AudioSocketFrame) -> bool:
        """
        Send a frame to a specific client by UUID

        Args:
            uuid: Client UUID
            frame: Frame to send

        Returns:
            True if sent successfully, False if client not found
        """
        with self.connection_lock:
            for conn in self.connections:
                if conn.protocol.uuid == uuid and conn.protocol.connected:
                    return conn.write_frame(frame)
        return False

    def disconnect_client(self, uuid: str) -> bool:
        """
        Disconnect a client by UUID

        Args:
            uuid: Client UUID

        Returns:
            True if client was found and disconnected, False otherwise
        """
        with self.connection_lock:
            for conn in self.connections:
                if conn.protocol.uuid == uuid:
                    conn.close()
                    self.connections.remove(conn)
                    self.active_connections -= 1
                    return True
        return False


class EchoServer(AudioSocketServer):
    """
    Simple echo server that echoes back all audio frames
    """

    def __init__(
        self,
        bind_address: str = "0.0.0.0",
        bind_port: int = 6050,
        config: Optional[AudioSocketConfig] = None,
    ):
        super().__init__(bind_address, bind_port, config, self._echo_handler)

    def _echo_handler(
        self, frame: AudioSocketFrame
    ) -> Optional[AudioSocketFrame]:
        """Echo back audio frames, ignore other frame types"""
        if frame.frame_type == FrameType.AUDIO:
            return frame  # Echo back the same audio frame
        return None


class VoiceBotServer(AudioSocketServer):
    """
    Voice bot server with configurable audio responses
    """

    def __init__(
        self,
        bind_address: str = "0.0.0.0",
        bind_port: int = 6050,
        config: Optional[AudioSocketConfig] = None,
        audio_responses: Optional[dict] = None,
    ):
        """
        Initialize voice bot server

        Args:
            bind_address: Address to bind to
            bind_port: Port to bind to
            config: Protocol configuration
            audio_responses: Dictionary mapping response IDs to audio data
        """
        super().__init__(
            bind_address, bind_port, config, self._voice_bot_handler
        )
        self.audio_responses = audio_responses or {}
        self.response_counter = 0
        # Create protocol instance for frame creation
        self.protocol = AudioSocketProtocol(config)

    def add_audio_response(self, response_id: str, audio_data: bytes) -> None:
        """Add an audio response"""
        self.audio_responses[response_id] = audio_data

    def _voice_bot_handler(
        self, frame: AudioSocketFrame
    ) -> Optional[AudioSocketFrame]:
        """Handle frames for voice bot functionality"""
        if frame.frame_type == FrameType.AUDIO:
            # For now, just echo back with some processing
            # In a real implementation, you would do voice recognition here
            return frame

        elif frame.frame_type == FrameType.DTMF:
            # Handle DTMF input
            if frame.payload:
                digit = frame.payload.decode("ascii", errors="ignore")
                self.logger.info(f"Received DTMF: {digit}")

                # Send a response based on DTMF digit
                response_id = f"dtmf_{digit}"
                if response_id in self.audio_responses:
                    audio_data = self.audio_responses[response_id]
                    return self.protocol.create_audio_frame(audio_data)

        return None
