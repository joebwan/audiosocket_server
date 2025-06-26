"""
VoiceBot Application

A VoiceBot application that extends the SimpleAudioSocketServer with business logic
for handling voice conversations. This application composes the server rather than
inheriting from it to keep the core server clean.
"""

import os
import threading
import time
from typing import Callable, Optional

from simple_server import SimpleAudioSocketServer


class VoiceBotApp:
    """
    VoiceBot application that handles voice conversations.

    This class composes the SimpleAudioSocketServer and adds business logic
    for managing voice interactions without polluting the core server code.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6050,
        on_speaker_done: Optional[Callable] = None,
        menu_prompts_dir: Optional[str] = None,
    ):
        """
        Initialize the VoiceBot application.

        Args:
            host: Host address to bind to (default: 127.0.0.1)
            port: Port to listen on (default: 6050)
            on_speaker_done: Callback function called when 1.5 seconds of silence is detected
                           indicating the speaker is done talking
            menu_prompts_dir: Directory containing menu prompt WAV files (default: recordings/prompts)
        """
        self.host = host
        self.port = port
        self.server = SimpleAudioSocketServer(
            host,
            port,
            recording_enabled=True,
            on_recording_complete=self._on_recording_complete,
        )
        self._server_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._silence_timer: Optional[threading.Timer] = None
        self._speaker_silence_timer: Optional[threading.Timer] = None
        self._greeting_played = False
        self._on_speaker_done = on_speaker_done
        self._recording_counter = 1
        self._current_recording_file = None
        self._current_recording_path = None
        # Use project_root/recordings/speech for recorded speech (client audio)
        self._recordings_dir = os.path.join(
            os.getcwd(), "recordings", "speech"
        )
        os.makedirs(self._recordings_dir, exist_ok=True)
        # Use project_root/recordings/prompts for menu prompts (server audio) by default
        self._menu_prompts_dir = menu_prompts_dir or os.path.join(
            os.getcwd(), "recordings", "prompts"
        )
        self._hangup_timer: Optional[threading.Timer] = None
        # Patch server's handlers to inject business logic
        self._patch_server_handlers()

    def _patch_server_handlers(self):
        """Patch the server's message handlers to inject business logic."""
        # Patch UUID handler
        original_handle_uuid = self.server._handle_uuid_message
        app = self

        def new_handle_uuid(payload):
            original_handle_uuid(payload)
            app._start_silence_timer()

        # Patch audio handler
        original_handle_audio = self.server._handle_audio_message

        def new_handle_audio(payload):
            original_handle_audio(payload)
            app._reset_silence_timer()
            app._start_speaker_silence_timer()
            app._write_audio_to_recording(payload)

        self.server._handle_uuid_message = new_handle_uuid
        self.server._handle_audio_message = new_handle_audio

    def _start_silence_timer(self):
        """Start or restart the 500ms silence timer after UUID or audio received."""
        if self._silence_timer:
            print(f"DEBUG: Cancelling previous silence timer")
            self._silence_timer.cancel()
            self._silence_timer = None
        self._greeting_played = False
        print(f"DEBUG: Starting 500ms silence timer")
        self._silence_timer = threading.Timer(0.5, self._play_greeting)
        self._silence_timer.daemon = True
        self._silence_timer.start()

    def _reset_silence_timer(self):
        """Reset the silence timer when audio is received (restart 500ms timer)."""
        self._start_silence_timer()

    def _play_greeting(self):
        """Play the greeting audio after 500ms of silence."""
        if not self._greeting_played:
            print(f"DEBUG: Playing greeting after 500ms silence")
            self._greeting_played = True
            greeting_path = os.path.join(
                self._menu_prompts_dir, "how_can_i_help_you.wav"
            )
            self.server.play_audio(greeting_path)

    def _start_speaker_silence_timer(self):
        """Start or restart the 1.5 second speaker silence timer."""
        if self._speaker_silence_timer:
            self._speaker_silence_timer.cancel()
            self._speaker_silence_timer = None

        self._speaker_silence_timer = threading.Timer(
            1.5, self._on_speaker_silence
        )
        self._speaker_silence_timer.daemon = True
        self._speaker_silence_timer.start()

    def _on_speaker_silence(self):
        """Called when 1.5 seconds of silence is detected (speaker is done talking)."""
        if self._on_speaker_done:
            self._on_speaker_done()

        # Play follow-up message after speaker is done
        followup_path = os.path.join(
            self._menu_prompts_dir, "please_tell_me_your_name.wav"
        )
        self.server.play_audio(followup_path)

        # Start 3-second hangup timer
        self._start_hangup_timer()

        # Close the current recording file and increment counter
        if self._current_recording_file:
            self._current_recording_file.close()
            self._current_recording_file = None
            self._current_recording_path = None
            self._recording_counter += 1

    def _start_hangup_timer(self):
        """Start the 3-second hangup timer."""
        if self._hangup_timer:
            self._hangup_timer.cancel()
            self._hangup_timer = None

        self._hangup_timer = threading.Timer(3.0, self._send_hangup)
        self._hangup_timer.daemon = True
        self._hangup_timer.start()

    def _send_hangup(self):
        """Send hangup event to the client."""
        if self.server.client_socket:
            from protocol import AudioSocketProtocol

            hangup_message = AudioSocketProtocol.create_hangup_message()
            try:
                self.server.client_socket.send(hangup_message)
            except:
                pass  # Client may have already disconnected

    def start(self):
        """Start the VoiceBot application."""
        if self._is_running:
            return

        self._is_running = True
        self._server_thread = threading.Thread(
            target=self.server.start, daemon=True
        )
        self._server_thread.start()

    def stop(self):
        """Stop the VoiceBot application."""
        self._is_running = False
        self.server.stop()
        if self._server_thread:
            self._server_thread.join(timeout=1.0)

    def _on_recording_complete(self, filename: str):
        """Callback when recording is completed."""
        # This will be implemented in future steps
        pass

    def is_running(self) -> bool:
        """Check if the VoiceBot is running."""
        return self._is_running and self.server.is_running

    def has_connection(self) -> bool:
        """Check if a client is connected."""
        return self.server.has_connection()

    def _write_audio_to_recording(self, audio_bytes):
        """Write incoming audio to the current recording file."""
        if self._current_recording_file is None:
            filename = f"recording_{self._recording_counter}.wav"
            path = os.path.join(self._recordings_dir, filename)
            import wave

            wf = wave.open(path, "wb")
            from protocol import AudioSocketProtocol

            wf.setnchannels(AudioSocketProtocol.AUDIO_CHANNELS)
            wf.setsampwidth(AudioSocketProtocol.AUDIO_BITS_PER_SAMPLE // 8)
            wf.setframerate(AudioSocketProtocol.AUDIO_SAMPLE_RATE)
            self._current_recording_file = wf
            self._current_recording_path = path
        self._current_recording_file.writeframes(audio_bytes)
