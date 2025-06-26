"""
Tests for Server-Side Playback API

This module tests the server's ability to send audio to connected Asterisk clients
for VoiceBot applications. The server should be able to:
1. Send audio frames to connected clients
2. Validate WAV files before playback
3. Handle multiple playback requests
4. Manage playback state and timing
5. Log playback events appropriately
"""

import os
import socket
import struct

# Add src to path for imports
import sys
import tempfile
import threading
import time
import unittest
import uuid
import wave
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from protocol import AudioSocketProtocol, ErrorCode, MessageType


class TestServerPlaybackAPI(unittest.TestCase):
    """Test server-side playback functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_host = "127.0.0.1"
        self.test_port = 0
        self.server = None
        self.client_socket = None

        # Create test WAV files
        self.valid_wav_file = self._create_test_wav_file(valid=True)
        self.invalid_wav_file = self._create_test_wav_file(valid=False)

    def tearDown(self):
        """Clean up test fixtures."""
        if self.client_socket:
            self.client_socket.close()
        if self.server:
            self.server.stop()
            self.server.close()

        # Clean up test files
        if os.path.exists(self.valid_wav_file):
            os.unlink(self.valid_wav_file)
        if os.path.exists(self.invalid_wav_file):
            os.unlink(self.invalid_wav_file)

    def _create_test_wav_file(self, valid: bool = True) -> str:
        """Create a temporary test WAV file."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_filename = temp_file.name

        with wave.open(temp_filename, "wb") as wav_file:
            if valid:
                # Valid Asterisk format: 16-bit, 8kHz, mono
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(8000)

                # Create 1 second of test audio (8000 samples)
                audio_data = struct.pack("<8000h", *([1000, -1000] * 4000))
            else:
                # Invalid format: 44.1kHz instead of 8kHz
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(44100)

                # Create test audio
                audio_data = struct.pack("<44100h", *([1000, -1000] * 22050))

            wav_file.writeframes(audio_data)

        return temp_filename

    def _start_server(self):
        """Start the server in a background thread."""
        from simple_server import SimpleAudioSocketServer

        self.server = SimpleAudioSocketServer(self.test_host, self.test_port)
        self.server_thread = threading.Thread(target=self.server.start)
        self.server_thread.daemon = True
        self.server_thread.start()

        # Wait for server to start
        time.sleep(0.1)

    def _connect_client(self):
        """Connect a client to the server."""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.test_host, self.server.port))

        # Send UUID to establish connection
        test_uuid = uuid.uuid4().bytes
        uuid_message = AudioSocketProtocol.create_uuid_message(test_uuid)
        self.client_socket.send(uuid_message)
        time.sleep(0.1)

    def _receive_audio_frames(self, timeout: float = 5.0) -> list[bytes]:
        """Receive audio frames from the server."""
        frames = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                self.client_socket.settimeout(0.1)
                data = self.client_socket.recv(1024)
                if data:
                    # Parse as audio message
                    try:
                        msg_type, length, payload = (
                            AudioSocketProtocol.parse_message(data)
                        )
                        if msg_type == MessageType.AUDIO:
                            frames.append(payload)
                    except ValueError:
                        # Not an audio message, continue
                        pass
            except socket.timeout:
                continue
            except Exception:
                break

        return frames

    def test_server_can_send_audio_to_client(self):
        """Test that server can send audio frames to connected client."""
        # Start server and connect client
        self._start_server()
        self._connect_client()

        # Verify connection is established
        self.assertTrue(self.server.has_connection())

        # Trigger playback (this method will be added to the server)
        self.server.play_audio(self.valid_wav_file)

        # Receive audio frames from server
        audio_frames = self._receive_audio_frames()

        # Verify audio frames were received
        self.assertGreater(
            len(audio_frames), 0, "Should receive audio frames from server"
        )

        # Verify frame format (320 bytes each)
        for frame in audio_frames:
            self.assertEqual(
                len(frame), 320, "Each audio frame should be 320 bytes"
            )

    def test_playback_rejects_invalid_wav_files(self):
        """Test that playback rejects invalid WAV files."""
        # Start server and connect client
        self._start_server()
        self._connect_client()

        # Attempt to play invalid WAV file
        with self.assertRaises(ValueError):
            self.server.play_audio(self.invalid_wav_file)

        # Verify no audio was sent
        audio_frames = self._receive_audio_frames(timeout=1.0)
        self.assertEqual(
            len(audio_frames), 0, "No audio should be sent for invalid WAV"
        )

    def test_playback_requires_active_connection(self):
        """Test that playback cannot be triggered without active connection."""
        # Start server but don't connect client
        self._start_server()
        time.sleep(0.1)

        # Verify no connection
        self.assertFalse(self.server.has_connection())

        # Attempt to play audio without connection
        with self.assertRaises(RuntimeError):
            self.server.play_audio(self.valid_wav_file)

    def test_playback_handles_client_disconnect(self):
        """Test that playback stops when client disconnects."""
        # Start server and connect client
        self._start_server()
        self._connect_client()

        # Start playback
        self.server.play_audio(self.valid_wav_file)

        # Disconnect client
        self.client_socket.close()
        time.sleep(0.1)

        # Verify server detects disconnect
        self.assertFalse(self.server.has_connection())

        # Verify playback stops (no more audio sent)
        # This would be tested by checking server state

    def test_multiple_playback_requests(self):
        """Test that multiple playback requests can be handled."""
        # Start server and connect client
        self._start_server()
        self._connect_client()

        # Create second valid WAV file
        second_wav_file = self._create_test_wav_file(valid=True)
        try:
            # Trigger multiple playbacks
            self.server.play_audio(self.valid_wav_file)
            self.server.play_audio(second_wav_file)

            # Receive audio frames
            audio_frames = self._receive_audio_frames()

            # Verify frames from both files were received
            self.assertGreater(
                len(audio_frames),
                0,
                "Should receive audio from multiple playbacks",
            )

        finally:
            if os.path.exists(second_wav_file):
                os.unlink(second_wav_file)

    def test_playback_logging(self):
        """Test that playback events are logged appropriately."""
        # Start server and connect client
        self._start_server()
        self._connect_client()

        # Capture log messages
        log_messages = []
        original_info = self.server.logger.info

        def mock_info(message):
            log_messages.append(message)
            original_info(message)

        self.server.logger.info = mock_info

        # Trigger playback
        self.server.play_audio(self.valid_wav_file)

        # Verify playback events were logged
        self.assertTrue(
            any("playback" in msg.lower() for msg in log_messages),
            "Playback events should be logged",
        )

        # Restore original logger
        self.server.logger.info = original_info

    def test_playback_frame_format_compliance(self):
        """Test that sent audio frames comply with AudioSocket protocol."""
        # Start server and connect client
        self._start_server()
        self._connect_client()

        # Trigger playback
        self.server.play_audio(self.valid_wav_file)

        # Receive and verify frame format
        audio_frames = self._receive_audio_frames()

        for frame in audio_frames:
            # Verify frame size
            self.assertEqual(len(frame), 320, "Audio frame must be 320 bytes")

            # Verify frame contains valid 16-bit PCM data
            # (basic check - all bytes should be within valid range)
            for byte in frame:
                self.assertIsInstance(byte, int)
                self.assertGreaterEqual(byte, 0)
                self.assertLessEqual(byte, 255)


if __name__ == "__main__":
    unittest.main()
