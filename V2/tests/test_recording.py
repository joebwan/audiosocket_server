"""
Test suite for AudioSocket Server Recording Functionality

These tests validate optional recording functionality for testing audio quality:
1. Server can optionally record audio frames during a session
2. Server saves recording as WAV file when connection ends
3. Recording filename includes UUID for identification
4. Server provides callback notification when recording is complete
5. Recording is optional and can be disabled
"""

import unittest
import os
import threading
import time
import uuid
import wave
from typing import Optional

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from protocol import AudioSocketProtocol, MessageType


class TestRecordingFunctionality(unittest.TestCase):
    """Test optional recording functionality for audio quality testing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_host = "127.0.0.1"
        self.test_port = 0
        self.recordings_dir = os.path.join(os.getcwd(), "recordings")
        
        # Ensure recordings directory exists
        os.makedirs(self.recordings_dir, exist_ok=True)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up recordings directory after all tests have run."""
        recordings_dir = os.path.join(os.getcwd(), "recordings")
        if os.path.exists(recordings_dir):
            for file in os.listdir(recordings_dir):
                if file.endswith('.wav'):
                    try:
                        os.remove(os.path.join(recordings_dir, file))
                    except OSError:
                        pass  # File might already be deleted
    
    def test_server_recording_disabled_by_default(self):
        """Test that recording is disabled by default (strict protocol mode)"""
        from simple_server import SimpleAudioSocketServer
        
        # Server should have recording_enabled attribute set to False by default
        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        
        self.assertTrue(hasattr(server, 'recording_enabled'),
                        "Server should have recording_enabled attribute by default")
        self.assertFalse(server.recording_enabled,
                         "Server recording_enabled should be False by default")
        self.assertFalse(hasattr(server, 'audio_frames'),
                        "Server should not accumulate audio_frames by default")
        self.assertTrue(hasattr(server, 'on_recording_complete'),
                        "Server should have on_recording_complete attribute by default")
        self.assertIsNone(server.on_recording_complete,
                         "Server on_recording_complete should be None by default")
        
        server.close()
    
    def test_server_recording_enabled_with_parameter(self):
        """Test that recording can be enabled with recording_enabled parameter"""
        from simple_server import SimpleAudioSocketServer
        
        # Create server with recording enabled
        server = SimpleAudioSocketServer(self.test_host, self.test_port, recording_enabled=True)
        
        # Verify recording attributes exist
        self.assertTrue(hasattr(server, 'recording_enabled'), 
                       "Server should have recording_enabled attribute when enabled")
        self.assertTrue(server.recording_enabled, 
                       "Server recording should be enabled")
        self.assertTrue(hasattr(server, 'audio_frames'), 
                       "Server should accumulate audio_frames when recording enabled")
        self.assertTrue(hasattr(server, 'on_recording_complete'), 
                       "Server should have recording callback when enabled")
        
        server.close()
    
    def test_server_records_audio_frames_when_enabled(self):
        """Test that server accumulates audio frames when recording is enabled"""
        from simple_server import SimpleAudioSocketServer
        
        # Create server with recording enabled
        server = SimpleAudioSocketServer(self.test_host, self.test_port, recording_enabled=True)
        
        # Start server in background thread
        import threading
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)
        
        # Connect client and send audio
        import socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))
        
        # Send UUID first
        test_uuid = uuid.uuid4().bytes
        uuid_message = AudioSocketProtocol.create_uuid_message(test_uuid)
        client_socket.send(uuid_message)
        time.sleep(0.1)
        
        # Send audio frames
        audio_data = b"\x00" * 320
        audio_message = AudioSocketProtocol.create_audio_message(audio_data)
        client_socket.send(audio_message)
        time.sleep(0.1)
        
        # Verify audio frames are accumulated
        self.assertEqual(len(server.audio_frames), 1, 
                        "Server should accumulate audio frames when recording enabled")
        self.assertEqual(server.audio_frames[0], audio_data, 
                        "Server should store correct audio data")
        
        # Send hangup to end session
        hangup_message = AudioSocketProtocol.create_hangup_message()
        client_socket.send(hangup_message)
        time.sleep(0.1)
        
        # Cleanup
        client_socket.close()
        server.stop()
        server.close()
    
    def test_server_saves_recording_file_when_enabled(self):
        """Test that server saves recording as WAV file when recording is enabled"""
        from simple_server import SimpleAudioSocketServer
        
        # Track recording completion
        recording_completed = threading.Event()
        recorded_filename = None
        
        def on_recording_complete(filename):
            nonlocal recorded_filename
            recorded_filename = filename
            recording_completed.set()
        
        # Create server with recording enabled and callback
        server = SimpleAudioSocketServer(
            self.test_host, self.test_port, 
            recording_enabled=True,
            on_recording_complete=on_recording_complete
        )
        
        # Start server in background thread
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)
        
        # Connect client and send audio
        import socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))
        
        # Send UUID first
        test_uuid = uuid.uuid4().bytes
        uuid_hex = test_uuid.hex()
        uuid_message = AudioSocketProtocol.create_uuid_message(test_uuid)
        client_socket.send(uuid_message)
        time.sleep(0.1)
        
        # Send multiple audio frames
        for i in range(3):
            audio_data = bytes([i % 256] * 320)  # Different data for each frame
            audio_message = AudioSocketProtocol.create_audio_message(audio_data)
            client_socket.send(audio_message)
            time.sleep(0.05)
        
        # Send hangup to end session
        hangup_message = AudioSocketProtocol.create_hangup_message()
        client_socket.send(hangup_message)
        
        # Wait for recording completion
        self.assertTrue(recording_completed.wait(timeout=10.0), 
                       "Recording completion callback should be called")
        
        # Verify recording file was created
        self.assertIsNotNone(recorded_filename, "Recording filename should be provided")
        self.assertTrue(os.path.exists(recorded_filename), 
                       f"Recording file should exist: {recorded_filename}")
        
        # Verify filename contains UUID
        self.assertIn(uuid_hex, recorded_filename, 
                     f"Filename should contain UUID: {uuid_hex}")
        self.assertTrue(recorded_filename.endswith('.wav'), 
                       "Filename should end with .wav")
        
        # Verify WAV file is valid
        with wave.open(recorded_filename, 'rb') as wav_file:
            self.assertEqual(wav_file.getnchannels(), 1, "WAV should be mono")
            self.assertEqual(wav_file.getsampwidth(), 2, "WAV should be 16-bit")
            self.assertEqual(wav_file.getframerate(), 8000, "WAV should be 8kHz")
            self.assertGreater(wav_file.getnframes(), 0, "WAV should have audio frames")
        
        # Cleanup
        client_socket.close()
        server.stop()
        server.close()
    
    def test_server_no_recording_when_disabled(self):
        """Test that server does not save recording when recording is disabled"""
        from simple_server import SimpleAudioSocketServer
        
        # Create server with recording disabled (default)
        server = SimpleAudioSocketServer(self.test_host, self.test_port)
        
        # Start server in background thread
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.1)
        
        # Connect client and send audio
        import socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.test_host, server.port))
        
        # Send UUID and audio
        test_uuid = uuid.uuid4().bytes
        uuid_message = AudioSocketProtocol.create_uuid_message(test_uuid)
        client_socket.send(uuid_message)
        
        audio_data = b"\x00" * 320
        audio_message = AudioSocketProtocol.create_audio_message(audio_data)
        client_socket.send(audio_message)
        
        # Send hangup to end session
        hangup_message = AudioSocketProtocol.create_hangup_message()
        client_socket.send(hangup_message)
        time.sleep(0.1)
        
        # Verify no recording file was created
        recordings_before = len([f for f in os.listdir(self.recordings_dir) if f.endswith('.wav')])
        
        # Wait a bit more to ensure no delayed file creation
        time.sleep(0.5)
        
        recordings_after = len([f for f in os.listdir(self.recordings_dir) if f.endswith('.wav')])
        self.assertEqual(recordings_before, recordings_after, 
                        "No recording file should be created when recording is disabled")
        
        # Cleanup
        client_socket.close()
        server.stop()
        server.close()


if __name__ == '__main__':
    unittest.main() 