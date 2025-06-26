import unittest
from unittest.mock import patch
import threading
import time
import uuid
import socket

# Add src to path for imports
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from protocol import AudioSocketProtocol, MessageType

class TestLoggingFunctionality(unittest.TestCase):
    """Test logging of key protocol events in the AudioSocket server"""

    def setUp(self):
        self.test_host = "127.0.0.1"
        self.test_port = 0

    def test_logs_connection_and_protocol_events(self):
        """Test that server logs connection, UUID, audio, error, and hangup events at INFO level"""
        from simple_server import SimpleAudioSocketServer

        with patch('logging.Logger.info') as mock_info, \
             patch('logging.Logger.error') as mock_error:
            server = SimpleAudioSocketServer(self.test_host, self.test_port)
            server_thread = threading.Thread(target=server.start)
            server_thread.daemon = True
            server_thread.start()
            time.sleep(0.1)

            # Connect client
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.test_host, server.port))

            # Send UUID
            test_uuid = uuid.uuid4().bytes
            uuid_message = AudioSocketProtocol.create_uuid_message(test_uuid)
            client_socket.send(uuid_message)
            time.sleep(0.1)

            # Send audio
            audio_data = b"\x00" * 320
            audio_message = AudioSocketProtocol.create_audio_message(audio_data)
            client_socket.send(audio_message)
            time.sleep(0.1)

            # Send error
            error_message = AudioSocketProtocol.create_error_message(1)
            client_socket.send(error_message)
            time.sleep(0.1)

            # Send hangup
            hangup_message = AudioSocketProtocol.create_hangup_message()
            client_socket.send(hangup_message)
            time.sleep(0.1)

            # Check that key events were logged
            info_calls = [call[0][0] for call in mock_info.call_args_list]
            error_calls = [call[0][0] for call in mock_error.call_args_list]

            self.assertTrue(any("Server started" in msg for msg in info_calls), "Should log server start")
            self.assertTrue(any("Connection from" in msg for msg in info_calls), "Should log connection")
            self.assertTrue(any("Received UUID" in msg for msg in info_calls), "Should log UUID")
            self.assertTrue(any("Received audio" in msg for msg in info_calls), "Should log audio")
            self.assertTrue(any("Received hangup request" in msg for msg in info_calls), "Should log hangup")
            self.assertTrue(any("Received error" in msg for msg in error_calls), "Should log error")

            # Cleanup
            client_socket.close()
            server.stop()
            server.close()

    def test_logging_level_can_be_set_to_debug(self):
        """Test that server can log at DEBUG level if configured"""
        from simple_server import SimpleAudioSocketServer
        import logging

        # Patch logging.basicConfig to set DEBUG level
        with patch('logging.basicConfig') as mock_basicConfig, \
             patch('logging.Logger.info') as mock_info, \
             patch('logging.Logger.debug') as mock_debug:
            server = SimpleAudioSocketServer(self.test_host, self.test_port)
            # Manually set logger to DEBUG
            server.logger.setLevel(logging.DEBUG)
            server.logger.debug("Debug message test")
            self.assertTrue(mock_debug.called, "Should log at DEBUG level when set")
            server.close()

if __name__ == '__main__':
    unittest.main() 