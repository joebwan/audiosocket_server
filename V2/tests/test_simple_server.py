"""
Test suite for Simple AudioSocket Server

These tests validate the basic server functionality against Asterisk C source code:
1. Server can listen on configurable TCP port and address
2. Server logs connection details
3. Server processes audio frames immediately (real-time)
4. Server responds to client hangup messages
5. Server handles protocol messages correctly
"""

import os
import socket

# Add src to path for imports
import sys
import threading
import time
import unittest
import uuid
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from protocol import AudioSocketProtocol, ErrorCode, MessageType


class TestSimpleServer(unittest.TestCase):
    """Test the simple AudioSocket server functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_host = "127.0.0.1"
        self.test_port = 0  # Let OS choose available port

    def test_server_initialization(self):
        """Test server can be initialized with configurable host and port"""
        from simple_server import SimpleAudioSocketServer

        server = SimpleAudioSocketServer(self.test_host, self.test_port)

        self.assertEqual(server.host, self.test_host)
        self.assertIsNotNone(server.port)  # Port should be assigned
        self.assertIsNotNone(server.socket)
        self.assertFalse(server.is_running)

        server.close()

    def test_server_listen_on_specific_port(self):
        """Test server can listen on a specific port"""
        from simple_server import SimpleAudioSocketServer

        # Use a specific port
        specific_port = 12345
        server = SimpleAudioSocketServer(self.test_host, specific_port)

        self.assertEqual(server.port, specific_port)

        server.close()

    def test_server_accepts_connection(self):
        """Test server can accept a connection from client"""
        from simple_server import SimpleAudioSocketServer

        server = SimpleAudioSocketServer(self.test_host, self.test_port)

        # Start server in background thread
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()

        # Wait for server to start
        time.sleep(0.1)

        # Connect client
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))

        # Wait a bit for connection to be processed
        time.sleep(0.1)

        # Verify server accepted connection
        self.assertTrue(server.has_connection())

        # Cleanup
        client_socket.close()
        server.stop()
        server.close()

    def test_server_logs_connection_details(self):
        """Test server records connection details when client connects (state-based, not logging)"""
        from simple_server import SimpleAudioSocketServer

        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))
        time.sleep(0.1)
        # Assert that the server recorded the client address
        self.assertIsNotNone(server.client_address)
        self.assertEqual(server.client_address[0], self.test_host)
        client_socket.close()
        server.stop()
        server.close()

    def test_server_receives_uuid_message(self):
        """Test server records last UUID received (state-based, not logging)"""
        from simple_server import SimpleAudioSocketServer

        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))
        test_uuid = uuid.uuid4().bytes
        uuid_message = AudioSocketProtocol.create_uuid_message(test_uuid)
        client_socket.send(uuid_message)
        time.sleep(0.1)
        self.assertIsNotNone(server.last_uuid)
        self.assertEqual(server.last_uuid, test_uuid)
        client_socket.close()
        server.stop()
        server.close()

    def test_server_processes_audio_frames_immediately(self):
        """Test server processes audio frames immediately (real-time) like Asterisk C code"""
        from simple_server import SimpleAudioSocketServer

        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))
        audio_data = b"\x00" * 320  # 320 bytes of silence
        audio_message = AudioSocketProtocol.create_audio_message(audio_data)
        client_socket.send(audio_message)
        time.sleep(0.1)
        # Server should process frame immediately (not accumulate)
        self.assertEqual(
            server.processed_frames,
            1,
            "Server should process frame immediately",
        )
        client_socket.close()
        server.stop()
        server.close()

    def test_server_responds_to_client_hangup(self):
        """Test server responds to client hangup message (not server-initiated)"""
        from simple_server import SimpleAudioSocketServer

        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))

        # Send hangup from client (like Asterisk does)
        hangup_message = AudioSocketProtocol.create_hangup_message()
        client_socket.send(hangup_message)

        # Wait for server to process hangup
        time.sleep(0.1)

        # Server should stop running after receiving hangup
        self.assertFalse(
            server.is_running,
            "Server should stop after receiving client hangup",
        )

        # Cleanup
        client_socket.close()
        server.stop()
        server.close()

    def test_server_handles_protocol_messages_correctly(self):
        """Test server handles all protocol message types correctly"""
        from simple_server import SimpleAudioSocketServer

        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))

        # Test UUID message
        test_uuid = uuid.uuid4().bytes
        uuid_message = AudioSocketProtocol.create_uuid_message(test_uuid)
        client_socket.send(uuid_message)
        time.sleep(0.1)
        self.assertEqual(server.last_uuid, test_uuid)

        # Test audio message
        audio_data = b"\x00" * 320
        audio_message = AudioSocketProtocol.create_audio_message(audio_data)
        client_socket.send(audio_message)
        time.sleep(0.1)
        self.assertEqual(server.processed_frames, 1)

        # Test error message
        error_message = AudioSocketProtocol.create_error_message(
            ErrorCode.HANGUP
        )
        client_socket.send(error_message)
        time.sleep(0.1)
        self.assertEqual(server.last_error_code, ErrorCode.HANGUP)

        # Test hangup message
        hangup_message = AudioSocketProtocol.create_hangup_message()
        client_socket.send(hangup_message)
        time.sleep(0.1)
        self.assertFalse(server.is_running)

        # Cleanup
        client_socket.close()
        server.stop()
        server.close()

    def test_server_cleans_up_resources(self):
        """Test server properly cleans up resources after connection ends"""
        from simple_server import SimpleAudioSocketServer

        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)

        # Connect and disconnect client
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))
        client_socket.close()

        # Wait for server to complete
        server_thread.join(timeout=5.0)

        # Verify server state is clean
        self.assertIsNone(
            server.client_socket, "Server should clean up client socket"
        )
        self.assertEqual(
            server.processed_frames, 0, "Server should reset processed frames"
        )
        self.assertIsNone(server.last_uuid, "Server should reset UUID")

        # Cleanup
        server.stop()
        server.close()

    def test_server_connection_handling_exception(self):
        """Test that server handles exceptions in connection handling gracefully."""
        from simple_server import SimpleAudioSocketServer

        # Create server
        server = SimpleAudioSocketServer(self.test_host, self.test_port)

        # Start server in background thread
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)

        # Connect client
        import socket

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))

        # Send invalid protocol data to cause parsing exception
        invalid_data = b"invalid_protocol_data"
        client_socket.send(invalid_data)
        time.sleep(0.1)

        # Close client socket
        client_socket.close()

        # Wait for server to handle the exception
        time.sleep(0.5)

        # Verify server stopped gracefully
        self.assertFalse(
            server.is_running, "Server should stop after protocol exception"
        )

        # Cleanup
        server.stop()
        server.close()


if __name__ == "__main__":
    unittest.main()
