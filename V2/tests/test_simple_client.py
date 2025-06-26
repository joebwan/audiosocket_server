import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import socket
import threading
import time
import unittest
import uuid
import wave

from protocol import AudioSocketProtocol, ErrorCode, MessageType


class TestSimpleClient(unittest.TestCase):
    """Strict protocol-compliance tests for SimpleAudioSocketClient (Asterisk-conforming)"""

    def setUp(self):
        self.test_host = "127.0.0.1"
        self.test_port = 0

    def test_client_protocol_compliance(self):
        """Test client can connect, send UUID, audio, and receive audio (Asterisk behavior)"""
        from simple_client import SimpleAudioSocketClient
        from simple_server import SimpleAudioSocketServer

        # Start server
        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)

        # Create and connect client
        client = SimpleAudioSocketClient(self.test_host, server.port)
        self.assertTrue(client.connect(), "Client should connect successfully")
        self.assertTrue(client.is_connected)
        self.assertIsNotNone(client.socket)

        # Send UUID (ast_audiosocket_init)
        test_uuid = uuid.uuid4().bytes
        self.assertTrue(
            client.send_uuid(test_uuid), "Client should send UUID successfully"
        )
        time.sleep(0.1)
        self.assertEqual(server.last_uuid, test_uuid)

        # Server speaks first (how_can_i_help_you.wav)
        server.play_audio("tests/recordings/how_can_i_help_you.wav")

        # Client receives audio from server (ast_audiosocket_receive_frame)
        received_audio = client.receive_audio(timeout=5.0)
        self.assertIsNotNone(
            received_audio, "Client should receive audio from server"
        )
        self.assertEqual(
            len(received_audio),
            320,
            "Received audio should be 320 bytes per frame",
        )

        # Client sends audio response (ast_audiosocket_send_frame)
        # Load client audio file and send it frame by frame
        with wave.open(
            "tests/recordings/need_schedule_appt_furnace.wav", "rb"
        ) as wav_file:
            audio_data = wav_file.readframes(wav_file.getnframes())

        # Send first frame (320 bytes)
        first_frame = audio_data[:320]
        self.assertTrue(
            client.send_audio(first_frame),
            "Client should send audio successfully",
        )
        time.sleep(0.1)
        self.assertEqual(server.processed_frames, 1)

        # Simulate connection loss (Asterisk behavior - no explicit hangup message)
        client.close()
        self.assertFalse(client.is_connected)
        self.assertIsNone(client.socket)

        # Cleanup
        server.stop()
        server.close()

    def test_client_asterisk_conforming_behavior(self):
        """Test that client only implements Asterisk-conforming methods"""
        from simple_client import SimpleAudioSocketClient

        client = SimpleAudioSocketClient(self.test_host, self.test_port)

        # Should have Asterisk methods
        self.assertTrue(hasattr(client, "connect"))
        self.assertTrue(hasattr(client, "send_uuid"))
        self.assertTrue(hasattr(client, "send_audio"))
        self.assertTrue(hasattr(client, "receive_audio"))
        self.assertTrue(hasattr(client, "close"))

        # Should NOT have non-Asterisk methods
        self.assertFalse(hasattr(client, "send_error"))
        self.assertFalse(hasattr(client, "send_hangup"))
        self.assertFalse(hasattr(client, "receive_message"))


if __name__ == "__main__":
    unittest.main()
