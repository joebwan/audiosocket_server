#!/usr/bin/env python3
# Standard library imports
# Third-party imports
import base64
import json
import math
import sys
import threading
import wave
from enum import Enum, auto
from time import sleep

import numpy as np
import requests

# Try to import webrtcvad, but handle import errors gracefully
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError as e:
    print(f"Warning: webrtcvad not available: {e}")
    print("Voice Activity Detection will be disabled. Install setuptools to enable VAD.")
    VAD_AVAILABLE = False
except Exception as e:
    print(f"Warning: webrtcvad initialization failed: {e}")
    VAD_AVAILABLE = False

# Local imports
from mapping import mapping
from mylogging import ColouredLogger
from req import Requests


class ConversationState(Enum):
    """Enumeration for conversation flow states"""

    NORMAL_PROGRESSION = auto()  # Levels 1-7 for normal conversation flow
    HANG_UP = auto()  # End conversation
    TRANSITION = auto()  # Transition state between levels
    LONG_SILENCE = auto()  # Handle long silence periods
    INTERRUPTION = auto()  # Handle interruptions during playback


class AudioStreamer:
    """
    Advanced voice bot that handles real-time audio streaming with intelligent conversation management.
    Similar to a voice assistant in Node.js or Java, but designed for telephony applications with
    state-based conversation flow and voice activity detection.
    """

    def __init__(self, call):
        """
        Constructor method (similar to Java constructor or JavaScript constructor).
        Initializes the audio streamer with voice activity detection and conversation state management.

        Args:
            call: AudioSocket connection object for reading/writing audio data
        """
        # Initialize colored logging for this audio streamer instance
        self.logger = ColouredLogger("audio sharing")

        # Audio configuration for telephony (8kHz, mono)
        self.channels = 1
        self.sample_rate = 8000

        # Voice Activity Detection (VAD) setup using WebRTC
        if VAD_AVAILABLE:
            self.vad = webrtcvad.Vad()
            self.vad.set_mode(3)  # Most aggressive VAD mode for telephony
            self.logger.info("Voice Activity Detection enabled")
        else:
            self.vad = None
            self.logger.warning("Voice Activity Detection disabled - webrtcvad not available")

        # Noise detection thresholds and counters
        self.noise_frames_threshold = int(2 * self.sample_rate / 512)
        self.noise_frames_count = 0

        # AudioSocket connection reference
        self.call = call

        # Audio frame processing variables
        self.audio_start = 0
        self.audio_end = 320  # 320 bytes = 20ms of 8kHz audio

        # Conversation state management
        self.state = ConversationState.NORMAL_PROGRESSION
        self.progression_level = (
            1  # Tracks the actual conversation level (1-7)
        )
        self.last_progression_level = 1

        # Audio playback control
        self.audioplayback = False

        # Silence detection counters
        self.silent_frames_count = 0
        self.total_frames = 0
        self.continues_silence_from_start = 0
        self.continues_silence_normal = 0

        # Audio data accumulation for processing
        self.combined_audio = b""

        # Language channel configuration
        self.channel = "en"  # Default to English

        # Noise level tracking
        self.noise_level = 0

    def read_wave_file(self, filename):
        """
        Reads a WAV file and returns its audio data as bytes.
        This method handles the file I/O for audio response files.

        Args:
            filename (str): Path to the WAV file to read

        Returns:
            bytes: Raw audio data from the WAV file
        """
        # self.logger.debug("Reading wave file")
        with wave.open(filename, "rb") as wave_file:
            audio = wave_file.readframes(wave_file.getnframes())
        return audio

    def detect_noise(self, indata, frames, rate):
        """
        Detects voice activity in incoming audio using WebRTC VAD.
        This method analyzes audio frames to determine if speech is present.

        Args:
            indata (bytes): Raw audio data to analyze
            frames (int): Number of audio frames
            rate (int): Sample rate of the audio data

        Returns:
            bool: True if speech is detected, False otherwise
        """
        if not VAD_AVAILABLE or self.vad is None:
            # Fallback: simple amplitude-based detection
            samples = np.frombuffer(indata, dtype=np.int16)
            amplitude = np.abs(samples).mean()
            is_noise = amplitude > 1000  # Simple threshold
        else:
            # Convert bytes to numpy array for processing
            samples = np.frombuffer(indata, dtype=np.int16)
            # Use WebRTC VAD to detect speech activity
            is_noise = self.vad.is_speech(samples.tobytes(), rate)

        if is_noise:
            # self.logger.debug(f"Noise detected in frames {self.noise_frames_count}")
            self.noise_frames_count += frames
            return True

    def send_audio(self, audio_file):
        """
        Sends audio data to the AudioSocket connection with proper timing and interruption detection.
        This method handles the streaming of audio responses while monitoring for user interruptions.

        Args:
            audio_file (bytes): Raw audio data to send to the caller
        """
        self.logger.info(
            f"Sending audio file of length {len(audio_file) / (320 * 25)}"
        )

        # Audio streaming variables
        count = 0
        audio_start = 0
        audio_end = 320
        sleep_seconds = 0

        # Enable audio playback mode to prevent noise detection conflicts
        self.audioplayback = True

        # Stream audio in 320-byte chunks (20ms frames)
        for i in range(math.floor(int(len(audio_file) / (320)))):
            # Send audio chunk to the caller
            self.call.write(audio_file[audio_start:audio_end])
            audio_start += 320
            audio_end += 320

            # self.detect_noise(indata, 1, 8000)
            count += 1

            # Add timing delays every 25 frames (500ms) to maintain proper audio pacing
            if count % 25 == 0:
                sleep(0.25)
                sleep_seconds += 0.25

            # Check for user interruptions during playback
            if self.state != ConversationState.INTERRUPTION:
                if self.noise_frames_count >= 4:
                    # User is speaking - interrupt the playback
                    self.noise_level = self.progression_level
                    self.state = ConversationState.INTERRUPTION
                    self.logger.info("State changed to INTERRUPTION")

                    self.noise_frames_count = 0
                    self.audioplayback = False
                    return

        self.logger.info(f"number of iterations are {count}")

        # Calculate remaining sleep time to match audio duration
        sleep(len(audio_file) / 16000 - sleep_seconds)
        self.logger.info(sleep_seconds)
        self.logger.info(
            f"Sleeping for {len(audio_file) / 16000 - sleep_seconds} seconds"
        )

        # Reset noise detection and disable playback mode
        self.noise_frames_count = 0
        self.audioplayback = False
        return

    def read_length(self, audio_file):
        """
        Reads the duration of a WAV file in seconds.
        This utility method helps with audio timing calculations.

        Args:
            audio_file (str): Path to the WAV file

        Returns:
            float: Duration of the audio file in seconds
        """
        with wave.open(audio_file, "rb") as wave_file:
            audio = wave_file.getnframes()
        return audio / 8000

    def detect_silence(self, indata, frames, rate):
        """
        Detects silence periods in incoming audio using WebRTC VAD.
        This method tracks continuous silence for conversation flow management.

        Args:
            indata (bytes): Raw audio data to analyze
            frames (int): Number of audio frames
            rate (int): Sample rate of the audio data
        """
        if not VAD_AVAILABLE or self.vad is None:
            # Fallback: simple amplitude-based silence detection
            samples = np.frombuffer(indata, dtype=np.int16)
            amplitude = np.abs(samples).mean()
            is_noise = amplitude > 1000  # Simple threshold
        else:
            # Convert bytes to numpy array for processing
            samples = np.frombuffer(indata, dtype=np.int16)
            # Use WebRTC VAD to detect speech activity (inverted for silence detection)
            is_noise = self.vad.is_speech(samples.tobytes(), rate)

        if not is_noise:
            # self.logger.debug(f"Noise detected in frames {self.noise_frames_count}")
            self.silent_frames_count += frames

            # Track different types of silence for conversation management
            if self.silent_frames_count - self.total_frames == 0:
                # Continuous silence from the start of the conversation
                self.continues_silence_from_start += 1
                self.continues_silence_normal += 1
            else:
                # Normal silence during conversation
                self.continues_silence_normal += 1
        else:
            # Reset silence counters when speech is detected
            self.continues_silence_from_start = 0
            self.continues_silence_normal = 0
        return

    def start_noise_detection(self):
        """
        Main noise detection loop that runs in a separate thread.
        This method continuously monitors incoming audio for voice activity
        and manages the conversation state based on detected speech patterns.
        """
        while self.call.connected:
            # Read audio data from the AudioSocket connection
            audio_data = self.call.read()

            if self.audioplayback:
                # During audio playback, detect interruptions
                # self.logger.info(f"noise detection started the value of noise fames is {self.noise_frames_count}")
                self.detect_noise(audio_data, 1, 8000)
            else:
                # During silence, accumulate audio and detect speech
                self.total_frames += 1
                self.combined_audio += audio_data
                self.detect_silence(audio_data, 1, 8000)
                # self.logger.info(f"silence detection started the value of silent fames is {self.silent_frames_count}")
        return

    def start_audio_playback(self, mapping):
        """
        Main audio playback loop that manages the conversation flow and audio responses.
        This method implements the state machine for conversation progression and handles
        various conversation states including interruptions, long silence, and transitions.

        Args:
            mapping (dict): Audio file mapping configuration for different languages and levels
        """
        self.logger.info(f"Received connection from {self.call.peer_addr}")

        # Main conversation loop
        while self.call.connected:

            if not self.audioplayback:
                self.logger.info(
                    f"we are in state {self.state.name} with progression level {self.progression_level}"
                )

                # Load and play the appropriate audio response
                x = self.read_wave_file(
                    mapping[self.channel][self.progression_level]
                )
                self.send_audio(x)

                # Reset silence detection counters
                self.silent_frames_count = 0
                self.continues_silence_normal = 0
                self.total_frames = 0
                self.continues_silence_from_start = 0

                # Handle interruption state - replay the current message
                if self.state == ConversationState.INTERRUPTION:
                    sleep(1)
                    x = self.read_wave_file(
                        mapping[self.channel][self.progression_level]
                    )
                    self.send_audio(x)
                    self.logger.info("playing interruption message")

                # Handle long silence state - play escalation messages
                if self.state == ConversationState.LONG_SILENCE:
                    self.long_silence_num = 0
                    num = 0
                    self.logger.info(
                        f"silence count is {self.silent_frames_count}"
                    )
                    self.logger.info(f"total frames is {self.total_frames}")

                    # Continue playing messages until user responds or max attempts reached
                    while self.silent_frames_count == self.total_frames:

                        if num == 0:
                            sleep(2)
                            self.logger.info(
                                "playing no audio message and sleeping for 2 seconds"
                            )

                        x = self.read_wave_file(
                            mapping[self.channel][self.progression_level]
                        )
                        self.send_audio(x)
                        self.logger.info("playing no audio message")
                        sleep(2)
                        num += 1

                        # Hang up after 3 attempts if no response
                        if num > 3:
                            self.state = ConversationState.HANG_UP
                            break

                    if self.state != ConversationState.TRANSITION:
                        self.progression_level = self.last_progression_level

                # self.logger.info("audio length is "+str(self.read_length(mapping[self.channel][self.progression_level])) + " seconds")

                # Handle hang up state - terminate the call
                if self.state == ConversationState.HANG_UP:
                    self.call.hangup()
                    self.audioplayback = False
                    sleep(1)
                    return

                # Wait for silence before proceeding to next conversation level
                if self.state != ConversationState.TRANSITION:
                    while self.continues_silence_normal < 150:
                        sleep(0.01)

                    # Detect long silence from start of conversation
                    if self.continues_silence_from_start > 100:
                        self.state = ConversationState.LONG_SILENCE
                        self.continues_silence_from_start = 0
                        self.continues_silence_normal = 0

                    self.logger.info("waiting for silence")
                    self.silent_frames_count = 0
                    self.continues_silence_normal = 0
                    self.data_array = []

                    # Handle state transitions based on conversation flow
                    if self.state != ConversationState.INTERRUPTION:
                        if self.state != ConversationState.LONG_SILENCE:
                            self.logger.info(self.progression_level)
                            self.last_progression_level = (
                                self.progression_level
                            )
                            self.logger.info(self.progression_level)
                            self.state = ConversationState.TRANSITION
                            self.logger.info("state changed to TRANSITION")
                        else:
                            self.logger.info("state is LONG_SILENCE")
                            pass
                    else:
                        self.logger.info("state is INTERRUPTION")
                        self.progression_level = self.last_progression_level

                    # Handle transition to next conversation level
                    if self.state == ConversationState.TRANSITION:
                        self.logger.info("state is TRANSITION")
                        self.progression_level = (
                            self.last_progression_level + 1
                        )
                        self.logger.info(
                            f"progression level changed to {self.progression_level}"
                        )
                        self.last_progression_level = self.progression_level
                        self.logger.info(
                            f"last progression level is {self.last_progression_level}"
                        )
                        self.progression_level = 1
                        self.state = ConversationState.NORMAL_PROGRESSION
                        self.logger.info("state changed to NORMAL_PROGRESSION")


def handle_call():
    audiosocket = Audiosocket(("localhost", 6050))
    audiosocket.prepare_output(outrate=44000, channels=2)
    audiosocket.prepare_input(inrate=44000, channels=2)
    call = audiosocket.listen()
    stream = AudioStreamer(call)
    noise_stream = threading.Thread(target=stream.start_noise_detection)
    noise_stream.start()
    playback_stream = threading.Thread(
        target=stream.start_audio_playback, args=(mapping,)
    )
    playback_stream.start()
    noise_stream.join()
    playback_stream.join()


if __name__ == "__main__":
    handle_call()
