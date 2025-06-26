import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import socket
import threading
import time
import uuid

from protocol import AudioSocketProtocol, MessageType, ErrorCode

class TestSimpleClient(unittest.TestCase):
    """Strict protocol-compliance tests for SimpleAudioSocketClient"""

    def setUp(self):
        self.test_host = "127.0.0.1"
        self.test_port = 0

    def test_client_protocol_compliance(self):
        """Test client can connect, send UUID, audio, error, hangup, and handle connection loss"""
        from simple_server import SimpleAudioSocketServer
        from simple_client import SimpleAudioSocketClient

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

        # Send UUID
        test_uuid = uuid.uuid4().bytes
        self.assertTrue(client.send_uuid(test_uuid), "Client should send UUID successfully")
        time.sleep(0.1)
        self.assertEqual(server.last_uuid, test_uuid)

        # Send audio
        audio_data = b"\x00" * 320
        self.assertTrue(client.send_audio(audio_data), "Client should send audio successfully")
        time.sleep(0.1)
        self.assertEqual(server.processed_frames, 1)

        # Send error
        self.assertTrue(client.send_error(ErrorCode.HANGUP), "Client should send error successfully")
        time.sleep(0.1)
        self.assertEqual(server.last_error_code, ErrorCode.HANGUP)

        # Send hangup
        self.assertTrue(client.send_hangup(), "Client should send hangup successfully")
        time.sleep(0.1)
        self.assertFalse(server.is_running)

        # Simulate connection loss
        client.close()
        self.assertFalse(client.is_connected)
        self.assertIsNone(client.socket)

        # Cleanup
        server.stop()
        server.close()

if __name__ == '__main__':
    unittest.main() 