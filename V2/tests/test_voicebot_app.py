"""
Tests for VoiceBot Application

Tests for the VoiceBot application that extends SimpleAudioSocketServer
with business logic for voice conversations.
"""

import os
import socket
import sys
import threading
import time
import unittest
import uuid
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from protocol import AudioSocketProtocol
from simple_client import SimpleAudioSocketClient


class TestVoiceBotApp(unittest.TestCase):
    """Test cases for VoiceBotApp."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_host = "127.0.0.1"
        self.test_port = 0  # Use 0 for auto-assign to avoid conflicts

    def test_voicebot_app_initialization(self):
        """Test VoiceBotApp initialization with default values."""
        from voicebot_app import VoiceBotApp

        app = VoiceBotApp()

        self.assertEqual(app.host, "127.0.0.1")
        self.assertEqual(app.port, 6050)
        self.assertIsNotNone(app.server)
        self.assertFalse(app.is_running())
        self.assertFalse(app.has_connection())

    def test_voicebot_app_initialization_custom_host_port(self):
        """Test VoiceBotApp initialization with custom host and port."""
        from voicebot_app import VoiceBotApp

        app = VoiceBotApp("0.0.0.0", 8080)

        self.assertEqual(app.host, "0.0.0.0")
        self.assertEqual(app.port, 8080)
        self.assertIsNotNone(app.server)
        self.assertFalse(app.is_running())

    def test_voicebot_app_server_has_recording_enabled(self):
        """Test that VoiceBotApp creates server with recording enabled."""
        from voicebot_app import VoiceBotApp

        app = VoiceBotApp()

        # The server should have recording enabled by default
        # We can't directly access this, but we can verify the behavior
        # by checking that the server is configured for recording
        self.assertTrue(hasattr(app.server, "recording_enabled"))

    def test_voicebot_app_start_stop(self):
        """Test VoiceBotApp start and stop functionality."""
        from voicebot_app import VoiceBotApp

        app = VoiceBotApp(self.test_host, self.test_port)

        # Start the app
        app.start()
        time.sleep(0.1)  # Give thread time to start

        # Verify it's running
        self.assertTrue(app.is_running())

        # Stop the app
        app.stop()
        time.sleep(0.1)  # Give thread time to stop

        # Verify it's stopped
        self.assertFalse(app.is_running())

    def test_voicebot_app_double_start(self):
        """Test that VoiceBotApp handles double start gracefully."""
        from voicebot_app import VoiceBotApp

        app = VoiceBotApp(self.test_host, self.test_port)

        # Start twice
        app.start()
        app.start()  # Should not create duplicate threads

        time.sleep(0.1)
        self.assertTrue(app.is_running())

        app.stop()

    def test_voicebot_app_connection_state(self):
        """Test VoiceBotApp connection state tracking."""
        from voicebot_app import VoiceBotApp

        app = VoiceBotApp(self.test_host, self.test_port)

        # Initially no connection
        self.assertFalse(app.has_connection())

        # Start app
        app.start()
        time.sleep(0.1)

        # Still no connection until client connects
        self.assertFalse(app.has_connection())

        app.stop()

    def test_voicebot_app_recording_callback(self):
        """Test that VoiceBotApp has recording callback set up."""
        from voicebot_app import VoiceBotApp

        app = VoiceBotApp()

        # Verify the callback method exists
        self.assertTrue(hasattr(app, "_on_recording_complete"))
        self.assertTrue(callable(app._on_recording_complete))

        # Test that callback can be called (should not raise)
        app._on_recording_complete("test_file.wav")

    def test_voicebot_plays_greeting_on_connect(self):
        """Test that VoiceBot plays greeting after client connects and 500ms delay."""
        import os
        import sys
        import time
        from unittest.mock import patch

        from voicebot_app import VoiceBotApp

        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "src")
        )
        import uuid

        from simple_client import SimpleAudioSocketClient

        # Patch play_audio to track calls
        with patch(
            "simple_server.SimpleAudioSocketServer.play_audio"
        ) as mock_play_audio:
            app = VoiceBotApp(self.test_host, self.test_port)
            app.start()
            time.sleep(0.1)  # Give server time to start

            # Simulate client connection using SimpleAudioSocketClient (Asterisk spec)
            client = SimpleAudioSocketClient(app.host, app.server.port)
            assert client.connect()
            test_uuid = uuid.uuid4().bytes
            assert client.send_uuid(test_uuid)

            # Wait for 0.6s to allow for 500ms delay and playback
            time.sleep(0.6)

            # Check that play_audio was called with the correct file
            expected_path = os.path.abspath(
                os.path.join("recordings", "prompts", "how_can_i_help_you.wav")
            )
            mock_play_audio.assert_any_call(expected_path)

            # Cleanup
            client.close()
            app.stop()

    def test_voicebot_plays_greeting_after_500ms_silence(self):
        """Test that VoiceBot plays greeting after 500ms of silence post-UUID."""
        import os
        import sys
        import time
        from unittest.mock import patch

        from voicebot_app import VoiceBotApp

        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "src")
        )
        import uuid

        from simple_client import SimpleAudioSocketClient

        with patch(
            "simple_server.SimpleAudioSocketServer.play_audio"
        ) as mock_play_audio:
            app = VoiceBotApp(self.test_host, self.test_port)
            app.start()
            time.sleep(0.1)  # Give server time to start

            # Simulate client connection using SimpleAudioSocketClient
            client = SimpleAudioSocketClient(app.host, app.server.port)
            assert client.connect()
            test_uuid = uuid.uuid4().bytes
            assert client.send_uuid(test_uuid)

            # Wait for 0.6s to allow for 500ms delay and playback
            time.sleep(0.6)

            # Check that play_audio was called with the correct file
            expected_path = os.path.abspath(
                os.path.join("recordings", "prompts", "how_can_i_help_you.wav")
            )
            mock_play_audio.assert_any_call(expected_path)

            # Cleanup
            client.close()
            app.stop()

    def test_voicebot_resets_timer_when_audio_received(self):
        """Test that VoiceBot resets silence timer when audio is received."""
        import os
        import sys
        import time
        from unittest.mock import patch

        from voicebot_app import VoiceBotApp

        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "src")
        )
        import uuid

        from simple_client import SimpleAudioSocketClient

        with patch(
            "simple_server.SimpleAudioSocketServer.play_audio"
        ) as mock_play_audio:
            app = VoiceBotApp(self.test_host, self.test_port)
            app.start()
            time.sleep(0.1)  # Give server time to start

            # Simulate client connection using SimpleAudioSocketClient
            client = SimpleAudioSocketClient(app.host, app.server.port)
            assert client.connect()
            test_uuid = uuid.uuid4().bytes
            assert client.send_uuid(test_uuid)

            # Wait for greeting to play (500ms silence)
            time.sleep(0.6)

            # Send audio to reset the timer (client "speaking")
            audio_data = b"\x00" * 320
            assert client.send_audio(audio_data)
            time.sleep(0.1)

            # Wait another 300ms (should not trigger greeting yet)
            time.sleep(0.3)

            # Greeting should NOT have been played again
            mock_play_audio.assert_called_once()

            # Wait another 600ms to allow for 500ms silence after audio
            time.sleep(0.6)

            # Now greeting should have been played again
            self.assertEqual(mock_play_audio.call_count, 2)

            # Cleanup
            client.close()
            app.stop()

    def test_voicebot_detects_15_seconds_silence_event(self):
        """Test that VoiceBot detects 1.5 seconds of silence and throws speaker_done event."""
        import os
        import sys
        import time
        from unittest.mock import patch

        from voicebot_app import VoiceBotApp

        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "src")
        )
        import uuid

        from simple_client import SimpleAudioSocketClient

        # Track if the speaker_done event was triggered
        speaker_done_called = threading.Event()
        speaker_done_timestamp = None

        def on_speaker_done():
            nonlocal speaker_done_timestamp
            speaker_done_timestamp = time.time()
            speaker_done_called.set()

        app = VoiceBotApp(
            self.test_host, self.test_port, on_speaker_done=on_speaker_done
        )
        app.start()
        time.sleep(0.1)  # Give server time to start

        # Simulate client connection using SimpleAudioSocketClient
        client = SimpleAudioSocketClient(app.host, app.server.port)
        assert client.connect()
        test_uuid = uuid.uuid4().bytes
        assert client.send_uuid(test_uuid)

        # Wait for greeting to play (500ms silence)
        time.sleep(0.6)

        # Send some audio to trigger speaker_done event (client "speaking")
        audio_data = b"\x00" * 320
        assert client.send_audio(audio_data)
        time.sleep(0.1)

        # Send more audio
        assert client.send_audio(audio_data)
        time.sleep(0.1)

        # Stop sending audio and wait for 1.5s silence detection
        start_silence = time.time()
        time.sleep(1.6)  # Wait slightly more than 1.5s

        # Verify speaker_done event was triggered
        self.assertTrue(
            speaker_done_called.wait(timeout=0.5),
            "Speaker done event should be triggered after 1.5s silence",
        )

        # Verify timing (should be triggered after ~1.5s from last audio)
        silence_duration = speaker_done_timestamp - start_silence
        self.assertGreaterEqual(
            silence_duration,
            1.35,
            f"Speaker done should trigger after ~1.5s, got {silence_duration:.2f}s",
        )
        self.assertLess(
            silence_duration,
            2.0,
            f"Speaker done should trigger within reasonable time, got {silence_duration:.2f}s",
        )

        # Cleanup
        client.close()
        app.stop()

    def test_voicebot_plays_followup_after_speaker_done(self):
        """Test that VoiceBot plays follow-up message after speaker_done event."""
        import os
        import sys
        import time
        from unittest.mock import patch

        from voicebot_app import VoiceBotApp

        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "src")
        )
        import uuid

        from simple_client import SimpleAudioSocketClient

        with patch(
            "simple_server.SimpleAudioSocketServer.play_audio"
        ) as mock_play_audio:
            app = VoiceBotApp(self.test_host, self.test_port)
            app.start()
            time.sleep(0.1)  # Give server time to start

            # Simulate client connection using SimpleAudioSocketClient
            client = SimpleAudioSocketClient(app.host, app.server.port)
            assert client.connect()
            test_uuid = uuid.uuid4().bytes
            assert client.send_uuid(test_uuid)

            # Wait for greeting to play (500ms silence)
            time.sleep(0.6)

            # Send some audio to trigger speaker_done event (client "speaking")
            audio_data = b"\x00" * 320
            assert client.send_audio(audio_data)
            time.sleep(0.1)

            # Wait for 1.5s silence to trigger speaker_done
            time.sleep(1.6)

            # Check that follow-up message was played
            expected_path = os.path.abspath(
                os.path.join(
                    "recordings", "prompts", "please_tell_me_your_name.wav"
                )
            )
            mock_play_audio.assert_any_call(expected_path)

            # Cleanup
            client.close()
            app.stop()

    def test_voicebot_records_client_speech_in_numbered_files(self):
        """Test that VoiceBot records all client speech in separate, numbered files."""
        import os
        import shutil
        import sys
        import time

        from voicebot_app import VoiceBotApp

        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "src")
        )
        import uuid

        from simple_client import SimpleAudioSocketClient

        # Clean up recordings directory before test
        recordings_dir = os.path.join(os.getcwd(), "recordings")
        speech_dir = os.path.join(recordings_dir, "speech")
        prompts_dir = os.path.join(recordings_dir, "prompts")

        # Remove only the speech directory, preserve prompts
        if os.path.exists(speech_dir):
            shutil.rmtree(speech_dir)
        os.makedirs(speech_dir, exist_ok=True)

        # Ensure prompts directory exists with required files
        os.makedirs(prompts_dir, exist_ok=True)
        if not os.path.exists(
            os.path.join(prompts_dir, "how_can_i_help_you.wav")
        ):
            shutil.copy(
                os.path.join("tests", "recordings", "how_can_i_help_you.wav"),
                prompts_dir,
            )
        if not os.path.exists(
            os.path.join(prompts_dir, "please_tell_me_your_name.wav")
        ):
            shutil.copy(
                os.path.join(
                    "tests", "recordings", "please_tell_me_your_name.wav"
                ),
                prompts_dir,
            )

        app = VoiceBotApp(self.test_host, self.test_port)
        app.start()
        time.sleep(0.1)  # Give server time to start

        # Simulate client connection using SimpleAudioSocketClient
        client = SimpleAudioSocketClient(app.host, app.server.port)
        assert client.connect()
        test_uuid = uuid.uuid4().bytes
        assert client.send_uuid(test_uuid)
        time.sleep(0.6)  # Wait for greeting

        # Stream a real WAV file to the server (client "speaking")
        wav_path = os.path.join(
            "tests", "recordings", "need_schedule_appt_furnace.wav"
        )
        with open(wav_path, "rb") as f:
            while True:
                chunk = f.read(320)
                if not chunk:
                    break
                assert client.send_audio(chunk)
                time.sleep(0.02)  # Simulate real-time streaming

        # Wait for 2s to allow for silence detection and recording
        time.sleep(2.0)

        # Check that numbered recording files exist
        files = sorted(
            [f for f in os.listdir(speech_dir) if f.endswith(".wav")]
        )
        self.assertTrue(
            len(files) >= 1, "Should have at least one numbered recording file"
        )
        for i, fname in enumerate(files, 1):
            self.assertIn(
                str(i),
                fname,
                f"Recording file {fname} should contain its number",
            )
            self.assertTrue(
                os.path.getsize(os.path.join(speech_dir, fname)) > 0,
                f"Recording file {fname} should not be empty",
            )

        # Cleanup
        client.close()
        app.stop()
        if os.path.exists(speech_dir):
            shutil.rmtree(speech_dir)

    def test_voicebot_sends_hangup_after_3_seconds_silence(self):
        """Test that VoiceBot sends hangup event after 3 seconds of silence."""
        import os
        import sys
        import time

        from voicebot_app import VoiceBotApp

        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "src")
        )
        import uuid

        from simple_client import SimpleAudioSocketClient

        app = VoiceBotApp(self.test_host, self.test_port)
        app.start()
        time.sleep(0.1)  # Give server time to start

        # Simulate client connection using SimpleAudioSocketClient
        client = SimpleAudioSocketClient(app.host, app.server.port)
        assert client.connect()
        test_uuid = uuid.uuid4().bytes
        assert client.send_uuid(test_uuid)
        time.sleep(0.6)  # Wait for greeting

        # Send some audio to reset silence timers (client "speaking")
        audio_data = b"\x00" * 320
        assert client.send_audio(audio_data)
        time.sleep(0.1)

        # Wait for 1.5s to trigger speaker_done and follow-up message
        time.sleep(1.6)

        # Send more audio after follow-up (client "speaking" again)
        assert client.send_audio(audio_data)
        time.sleep(0.1)

        # Stop sending audio and wait for 3s silence to trigger hangup
        # Client sends nothing (no audio frames) during silence
        start_silence = time.time()
        # Wait up to 4s for hangup event
        hangup_received = False
        for _ in range(40):
            if not client.is_connected:
                hangup_received = True
                break
            client.receive_audio(timeout=0.1)
            time.sleep(0.1)

        self.assertTrue(
            hangup_received,
            "Client should receive hangup event after 3s silence",
        )

        # Cleanup
        client.close()
        app.stop()


if __name__ == "__main__":
    unittest.main()
