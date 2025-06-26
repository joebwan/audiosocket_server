"""
Simple AudioSocket Server

A minimal implementation of the AudioSocket server that matches Asterisk C code behavior:
1. Listens on configurable TCP port and address
2. Logs connection details
3. Processes audio frames immediately (real-time)
4. Responds to client hangup messages
5. Handles protocol messages correctly
6. Optional recording functionality for testing audio quality
7. Audio playback functionality for VoiceBot applications
"""

import logging
import os
import socket
import threading
import time
import wave
from datetime import datetime
from typing import Callable, List, Optional

from audio_playback import WavAudioStreamer
from protocol import AudioSocketProtocol, ErrorCode, MessageType


class SimpleAudioSocketServer:
    """
    Simple AudioSocket server implementation.

    This server accepts a single connection, processes audio frames immediately,
    and responds to client hangup messages like the Asterisk C code.

    Optional recording functionality can be enabled for testing audio quality.
    """

    def __init__(
        self,
        host: str,
        port: int,
        recording_enabled: bool = False,
        recording_dir: Optional[str] = None,
        on_recording_complete: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the server.

        Args:
            host: Host address to bind to
            port: Port to listen on (0 for auto-assign)
            recording_enabled: Enable recording functionality for testing (default: False)
            recording_dir: Directory to save recordings (defaults to ./recordings/)
            on_recording_complete: Callback function called when recording is saved
                                  Signature: callback(filename: str) -> None
        """
        self.host = host
        self.port = port
        self.recording_enabled = recording_enabled
        self.recording_dir = recording_dir or os.path.join(
            os.getcwd(), "recordings"
        )
        self.on_recording_complete = on_recording_complete

        self.socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )  # Always create socket
        self.client_socket = None
        self.client_address = None
        self.is_running = False
        self.server_thread = None
        self.processed_frames = 0
        self.last_uuid = None
        self.last_error_code = None

        # Recording-specific attributes (only when enabled)
        if self.recording_enabled:
            self.audio_frames = []
            self.recording_filename = None

        # Playback-specific attributes
        self.playback_queue = []
        self.current_playback = None
        self.playback_thread = None
        self.playback_active = False
        self.playback_lock = threading.Lock()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("simple_server")

    def _create_socket(self):
        """Bind and listen on the server socket."""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        if self.port == 0:
            self.port = self.socket.getsockname()[1]

    def _reset_state(self):
        """Reset server state for new connections."""
        self.client_socket = None
        self.client_address = None
        self.processed_frames = 0
        self.last_uuid = None
        self.last_error_code = None
        self.is_running = False

        # Reset recording state if enabled
        if self.recording_enabled:
            self.audio_frames = []
            self.recording_filename = None

        # Reset playback state
        self.stop_playback()

    def start(self):
        """Start the server and accept a single connection."""
        try:
            self._create_socket()
            self.is_running = True
            self.logger.info(f"Server started on {self.host}:{self.port}")

            # Accept single connection
            self.client_socket, self.client_address = self.socket.accept()
            self.logger.info(f"Connection from {self.client_address}")

            # Handle the connection
            self._handle_connection()

        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self._reset_state()
            self.stop()

    def _handle_connection(self):
        """Handle the client connection."""
        try:
            # Process messages
            while self.is_running and self.client_socket:
                try:
                    # Receive data
                    data = self.client_socket.recv(1024)
                    if not data:
                        break

                    # Parse message
                    msg_type, length, payload = (
                        AudioSocketProtocol.parse_message(data)
                    )

                    # Handle different message types
                    if msg_type == MessageType.UUID:
                        self._handle_uuid_message(payload)
                    elif msg_type == MessageType.AUDIO:
                        self._handle_audio_message(payload)
                    elif msg_type == MessageType.HANGUP:
                        self._handle_hangup_message()
                        break
                    elif msg_type == MessageType.ERROR:
                        self._handle_error_message(payload)

                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    break

            # Save recording if enabled
            if self.recording_enabled:
                self._save_recording()

        except Exception as e:
            self.logger.error(f"Connection handling error: {e}")
        finally:
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None

    def _handle_uuid_message(self, payload: bytes):
        """Handle UUID message."""
        uuid_hex = payload.hex()
        self.last_uuid = payload
        self.logger.info(f"Received UUID: {uuid_hex}")

    def _handle_audio_message(self, payload: bytes):
        """Handle audio message - process immediately like Asterisk C code."""
        self.logger.info(f"Received audio: {len(payload)} bytes")
        self.processed_frames += 1

        # Accumulate audio frames if recording is enabled
        if self.recording_enabled:
            self.audio_frames.append(payload)

    def _handle_hangup_message(self):
        """Handle hangup message from client."""
        self.logger.info("Received hangup request from client")
        self.is_running = False

    def _handle_error_message(self, payload: bytes):
        """Handle error message."""
        error_code = payload[0] if payload else 0
        self.last_error_code = error_code
        error_desc = AudioSocketProtocol.get_error_description(error_code)
        self.logger.error(f"Received error: {error_desc}")

    def _save_recording(self):
        """Save recorded audio to WAV file (only when recording is enabled)."""
        if not self.recording_enabled or not self.audio_frames:
            return

        # Create recordings directory if it doesn't exist
        os.makedirs(self.recording_dir, exist_ok=True)

        # Generate filename using UUID if available, otherwise use timestamp
        if self.last_uuid:
            uuid_hex = self.last_uuid.hex()
            self.recording_filename = os.path.join(
                self.recording_dir, f"audiosocket_recording_{uuid_hex}.wav"
            )
        else:
            # Fallback to timestamp if no UUID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.recording_filename = os.path.join(
                self.recording_dir, f"audiosocket_recording_{timestamp}.wav"
            )

        self.logger.info(f"Saving recording to: {self.recording_filename}")

        # Write WAV file
        with wave.open(self.recording_filename, "wb") as wav_file:
            wav_file.setnchannels(AudioSocketProtocol.AUDIO_CHANNELS)
            wav_file.setsampwidth(
                AudioSocketProtocol.AUDIO_BITS_PER_SAMPLE // 8
            )
            wav_file.setframerate(AudioSocketProtocol.AUDIO_SAMPLE_RATE)

            # Write all audio frames
            for frame in self.audio_frames:
                wav_file.writeframes(frame)

        self.logger.info(f"Recording saved: {self.recording_filename}")

        # Notify recording completion
        if self.on_recording_complete:
            self.on_recording_complete(self.recording_filename)

    def has_connection(self) -> bool:
        """Check if server has an active connection."""
        return self.client_socket is not None

    def stop(self):
        """Stop the server."""
        self.is_running = False

        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None

        if self.socket:
            self.socket.close()
            self.socket = None

    def close(self):
        """Close the server (alias for stop)."""
        self.stop()

    def play_audio(self, wav_filename: str) -> bool:
        """
        Play audio from a WAV file to the connected client.

        Args:
            wav_filename: Path to the WAV file to play

        Returns:
            True if playback started successfully, False otherwise

        Raises:
            RuntimeError: If no client is connected
            ValueError: If WAV file is invalid or doesn't conform to Asterisk format
        """
        if not self.has_connection():
            raise RuntimeError("Cannot play audio: no client connected")

        abs_path = os.path.abspath(wav_filename)
        self.logger.info(
            f"[DEBUG] play_audio called with: {wav_filename} (absolute: {abs_path})"
        )
        try:
            # Validate and create streamer
            streamer = WavAudioStreamer(wav_filename)

            with self.playback_lock:
                # Add to playback queue
                self.playback_queue.append(streamer)
                self.logger.info(
                    f"Added audio file to playback queue: {wav_filename}"
                )

                # Start playback thread if not already running
                if not self.playback_active:
                    self._start_playback_thread()

            return True

        except ValueError as e:
            self.logger.error(f"Invalid WAV file for playback: {e}")
            raise ValueError(f"Invalid WAV file for playback: {e}")
        except Exception as e:
            self.logger.error(f"Error starting playback: {e}")
            return False

    def _start_playback_thread(self):
        """Start the playback thread."""
        if self.playback_thread and self.playback_thread.is_alive():
            return

        self.playback_active = True
        self.playback_thread = threading.Thread(
            target=self._playback_worker, daemon=True
        )
        self.playback_thread.start()
        self.logger.info("Playback thread started")

    def _playback_worker(self):
        """Worker thread that handles audio playback."""
        while self.playback_active and self.is_running:
            try:
                with self.playback_lock:
                    if not self.playback_queue:
                        # No audio to play, wait a bit
                        time.sleep(0.01)
                        continue

                    # Get next audio streamer
                    self.current_playback = self.playback_queue.pop(0)

                # Play the audio
                self._play_audio_streamer(self.current_playback)

                with self.playback_lock:
                    self.current_playback = None

            except Exception as e:
                self.logger.error(f"Error in playback worker: {e}")
                time.sleep(0.1)

        self.logger.info("Playback thread stopped")

    def _play_audio_streamer(self, streamer: WavAudioStreamer):
        """Play audio from a WavAudioStreamer to the connected client."""
        try:
            self.logger.info(f"Starting playback of {len(streamer)} frames")

            for frame in streamer:
                if not self.playback_active or not self.is_running:
                    break

                # Send frame to client
                if self.client_socket:
                    try:
                        sent = self.client_socket.send(frame)
                        if sent != len(frame):
                            self.logger.error(
                                f"Failed to send complete audio frame: sent {sent} of {len(frame)} bytes"
                            )
                            break

                        # Small delay to maintain real-time playback (20ms per frame)
                        time.sleep(0.02)

                    except OSError as e:
                        self.logger.error(f"Error sending audio frame: {e}")
                        break
                else:
                    # Client disconnected
                    break

            self.logger.info("Playback completed")

        except Exception as e:
            self.logger.error(f"Error during audio playback: {e}")

    def stop_playback(self):
        """Stop current playback and clear queue."""
        with self.playback_lock:
            self.playback_active = False
            self.playback_queue.clear()
            self.current_playback = None

        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)

        self.logger.info("Playback stopped")

    def is_playing(self) -> bool:
        """Check if audio is currently being played."""
        with self.playback_lock:
            return self.playback_active and (
                self.current_playback is not None
                or len(self.playback_queue) > 0
            )

    # TODO: Add a 'detect_silence' function that can monitor incoming audio and
    #       throw an event or call a callback when a configurable period of silence is detected.
    #       This will be useful for business logic such as hangup after silence, etc.
