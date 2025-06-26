# AudioSocket Server V2

A clean, test-first implementation of the Asterisk AudioSocket server based on the official Asterisk source code, with VoiceBot capabilities for interactive voice applications.

## Overview

This is a complete rewrite of the AudioSocket server implementation, built using a test-first approach and strict adherence to the Asterisk protocol specification. The implementation includes both strict protocol compliance and VoiceBot functionality for building interactive voice applications.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Virtual environment tool (venv, virtualenv, or conda)

### Setup Commands
```bash
# Create and activate virtual environment
python3 -m venv python_modules
source python_modules/bin/activate  # On Windows: python_modules\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run all tests
python3 -m pytest tests/ -v
```

## Project Structure

```
voicebot-py/
├── src/                    # Source code
│   ├── protocol.py         # AudioSocket protocol definition
│   ├── simple_client.py    # Simple AudioSocket client (Asterisk-conforming)
│   ├── simple_server.py    # Simple AudioSocket server implementation
│   ├── audio_playback.py   # Audio playback system (VoiceBot Feature 1)
│   ├── voicebot_app.py     # VoiceBot application with conversation flow
│   └── asterisk/           # Asterisk source code reference
│       ├── res_audiosocket.c
│       └── chan_audiosocket.c
├── tests/                  # Test suite
│   ├── test_protocol.py        # Protocol compliance tests
│   ├── test_simple_server.py   # Server protocol tests
│   ├── test_simple_client.py   # Client protocol tests (Asterisk-conforming)
│   ├── test_integration.py     # End-to-end integration tests
│   ├── test_recording.py       # Recording functionality tests
│   ├── test_logging.py         # Logging and debugging tests
│   ├── test_audio_playback.py  # Audio playback system tests
│   ├── test_server_playback.py # Server playback API tests
│   ├── test_voicebot_app.py    # VoiceBot application tests
│   └── recordings/             # Test WAV files (Asterisk-compatible)
│       ├── how_can_i_help_you.wav
│       ├── need_schedule_appt_furnace.wav
│       └── please_tell_me_your_name.wav
├── recordings/             # Application audio files
│   ├── prompts/            # Menu prompts and system audio (persistent)
│   │   ├── how_can_i_help_you.wav
│   │   └── please_tell_me_your_name.wav
│   └── speech/             # Recorded client speech (test output, cleaned up)
├── requirements.txt       # Dependencies
├── .gitignore            # Git ignore rules
├── python_modules/        # Python virtual environment (not tracked in version control)
└── README.md              # This file
```

## Development Approach

This implementation follows a strict test-first development paradigm:

1. **Protocol Definition**: Start with exact protocol specification from Asterisk source code
2. **Comprehensive Testing**: Write tests that validate against the Asterisk implementation
3. **Minimal Implementation**: Write only enough code to pass the tests
4. **Incremental Development**: Build functionality in small, focused groups

## Current Status

### Asterisk AudioSocket Support ✅
- [x] Protocol constants matching Asterisk implementation
- [x] Message parsing according to `ast_audiosocket_receive_frame()`
- [x] Message creation according to `ast_audiosocket_send_frame()`
- [x] Comprehensive test suite with **65 tests** and **94% coverage**
- [x] Minimal server implementation strictly matching Asterisk protocol
- [x] Real-time, frame-by-frame protocol handling
- [x] Connection management and resource cleanup
- [x] Simple AudioSocket client for testing server functionality
- [x] End-to-end protocol compliance tests
- [x] Optional recording functionality for testing audio quality
- [x] Comprehensive logging of protocol events

### VoiceBot Feature 1: Audio Playback System ✅
**Goal**: Extending apps can "speak" to callers by streaming pre-recorded .wav files via AudioSocket
- [x] WAV file loader and validator (Asterisk-compatible format: 8kHz, 16-bit, mono)
- [x] Audio streaming mechanism compatible with AudioSocket protocol
- [x] Server-side playback API with queue management
- [x] Thread-safe playback with real-time frame timing (20ms per frame)
- [x] Comprehensive tests for audio playback functionality
- [x] Real WAV file testing with Asterisk-compatible format
- [x] Client audio reception (mocks `ast_audiosocket_receive_frame`)
- [x] End-to-end audio conversation testing

### VoiceBot Feature 2: Interactive VoiceBot Application ✅
**Goal**: Complete VoiceBot application with conversation flow management
- [x] VoiceBotApp class composing SimpleAudioSocketServer
- [x] Automatic greeting playback after client connection (500ms delay)
- [x] Silence detection and timer management (1.5s for speaker done, 3s for hangup)
- [x] Client speech recording in numbered WAV files
- [x] Follow-up message playback after speaker silence
- [x] Automatic hangup after 3 seconds of client silence
- [x] Configurable menu prompts directory
- [x] Comprehensive VoiceBot application tests (14 tests)
- [x] Proper directory structure: `recordings/prompts/` for menu prompts, `recordings/speech/` for recordings
- [x] Asterisk-conforming client usage in all tests

## Feature Enhancements (TODO)

The following VoiceBot features are planned for future development. Each feature should be implemented individually with test-first development approach.

### VoiceBot Feature 3: Speech Recognition Integration
**Goal**: Server can transcribe speech from audio using external agents
**Tasks**:
- [ ] Design speech recognition service interface
- [ ] Implement audio preprocessing for speech recognition (format conversion, noise reduction)
- [ ] Create speech recognition agent integration (OpenAI Whisper, Google Speech-to-Text, etc.)
- [ ] Add transcription result handling and validation
- [ ] Implement retry logic and error handling for recognition failures
- [ ] Write tests for speech recognition functionality
- [ ] Add configuration for speech recognition service credentials and settings

### VoiceBot Feature 4: Text-to-Speech Integration
**Goal**: Server can generate speech from text using external agents
**Tasks**:
- [ ] Design TTS service interface
- [ ] Implement text preprocessing and validation
- [ ] Create TTS agent integration (OpenAI TTS, Google Text-to-Speech, etc.)
- [ ] Add audio format conversion for TTS output
- [ ] Implement TTS caching for performance optimization
- [ ] Write tests for TTS functionality
- [ ] Add configuration for TTS service credentials and voice settings

### VoiceBot Feature 5: Conversation Flow Management
**Goal**: Server can manage multi-turn conversations with callers
**Tasks**:
- [ ] Design conversation state management system
- [ ] Implement conversation flow controller
- [ ] Create prompt templates and variable substitution
- [ ] Add conversation history tracking
- [ ] Implement conversation timeout and cleanup
- [ ] Write tests for conversation flow management
- [ ] Add configuration for conversation settings and timeouts

### VoiceBot Feature 6: Name Collection Workflow
**Goal**: Complete end-to-end name collection workflow
**Tasks**:
- [ ] Implement "What's your name?" prompt playback
- [ ] Add speech recognition for name transcription
- [ ] Implement name validation and confirmation
- [ ] Create "Thank you <name>, goodbye." TTS generation
- [ ] Add error handling for unclear names or recognition failures
- [ ] Write integration tests for complete name collection workflow
- [ ] Add configuration for name collection settings

### VoiceBot Feature 7: Advanced Audio Processing
**Goal**: Enhanced audio quality and processing capabilities
**Tasks**:
- [ ] Implement audio format conversion utilities
- [ ] Add audio quality enhancement (noise reduction, echo cancellation)
- [ ] Create audio streaming optimization for real-time processing
- [ ] Implement audio buffering and synchronization
- [ ] Add audio level monitoring and automatic gain control
- [ ] Write tests for audio processing functionality
- [ ] Add configuration for audio processing settings

### VoiceBot Feature 8: Configuration and Deployment
**Goal**: Production-ready configuration and deployment system
**Tasks**:
- [ ] Create comprehensive configuration file system
- [ ] Implement environment variable support
- [ ] Add logging and monitoring for VoiceBot operations
- [ ] Create deployment scripts and Docker support
- [ ] Implement health checks and status endpoints
- [ ] Write deployment and configuration tests
- [ ] Add documentation for configuration and deployment

### Development Guidelines for Features

Each feature should follow the established test-first development approach:

1. **Write Tests First**: Create comprehensive tests that define the expected behavior
2. **Minimal Implementation**: Write only enough code to pass the tests
3. **Integration Testing**: Ensure features work together with existing functionality
4. **Configuration**: Make features configurable and environment-aware
5. **Documentation**: Update documentation as features are implemented
6. **Error Handling**: Implement robust error handling and recovery
7. **Performance**: Consider performance implications and optimize as needed

**Note**: Features should be implemented incrementally, with each feature being fully tested and documented before moving to the next. This ensures a stable, maintainable codebase throughout the development process.

## Features

### Core Protocol Implementation
- **Strict Asterisk Compliance**: All protocol constants, message formats, and error codes match the official Asterisk implementation
- **Real-time Processing**: Frame-by-frame audio processing like the C implementation
- **Connection Management**: Proper TCP connection handling and cleanup
- **Error Handling**: Comprehensive error code support and logging

### Audio Playback System (VoiceBot Feature 1)
- **Asterisk-Compatible WAV Files**: 8kHz, 16-bit, mono format validation
- **Real-time Audio Streaming**: 20ms frame timing for smooth playback
- **Thread-safe Playback Queue**: Multiple audio files can be queued
- **Server-side Playback API**: Simple `play_audio()` method for applications
- **Client Audio Reception**: Asterisk-conforming client can receive audio
- **End-to-end Testing**: Real WAV files for comprehensive validation

### VoiceBot Application (VoiceBot Feature 2)
- **Interactive Conversation Flow**: Automatic greeting, silence detection, and hangup
- **Client Speech Recording**: Numbered WAV files saved to `recordings/speech/`
- **Menu Prompt System**: Configurable prompts loaded from `recordings/prompts/`
- **Silence Timer Management**: 1.5s for speaker done detection, 3s for hangup
- **Asterisk-conforming Client**: All tests use proper AudioSocket client
- **Comprehensive Testing**: 14 VoiceBot application tests with full coverage

### Optional Recording Functionality
- **Configurable Recording**: Enable/disable recording via constructor parameter
- **On-demand Directory Creation**: Recordings directory created only when needed
- **Configurable Path**: Custom recording directory path support
- **WAV Format**: Standard WAV files with proper audio format headers
- **UUID-based Naming**: Recordings named using client UUID for easy identification

### Testing and Development
- **Test-first Development**: 79 comprehensive tests covering all functionality
- **94% Code Coverage**: Thorough testing of all implemented features
- **Integration Testing**: End-to-end client-server interaction tests
- **Asterisk-conforming Client**: Simple client implementation for server testing
- **Real Audio Testing**: WAV files for realistic audio playback testing
- **Clean Architecture**: Minimal, focused implementation

## Running Tests

To run all tests:

```bash
python3 -m pytest tests/ -v
```

Or run a specific test file:

```bash
python3 -m pytest tests/test_simple_server.py -v
python3 -m pytest tests/test_simple_client.py -v
python3 -m pytest tests/test_integration.py -v
python3 -m pytest tests/test_protocol.py -v
python3 -m pytest tests/test_recording.py -v
python3 -m pytest tests/test_logging.py -v
python3 -m pytest tests/test_audio_playback.py -v
python3 -m pytest tests/test_server_playback.py -v
python3 -m pytest tests/test_voicebot_app.py -v
```

## Usage Examples

### Basic Server (Protocol Only)
```python
from src.simple_server import SimpleAudioSocketServer

# Start server with strict protocol compliance
server = SimpleAudioSocketServer("127.0.0.1", 0)
server.start()
```

### Server with Recording
```python
from src.simple_server import SimpleAudioSocketServer

# Start server with recording enabled
server = SimpleAudioSocketServer(
    "127.0.0.1",
    0,
    recording_enabled=True,
    recording_dir="/path/to/recordings"
)
server.start()
```

### Server with Audio Playback
```python
from src.simple_server import SimpleAudioSocketServer

# Start server and play audio to connected client
server = SimpleAudioSocketServer("127.0.0.1", 0)
server.start()

# When client connects, play audio
server.play_audio("path/to/asterisk_compatible.wav")
```

### VoiceBot Application
```python
from src.voicebot_app import VoiceBotApp

# Create VoiceBot with custom callback
def on_speaker_done():
    print("Speaker finished talking")

# Start VoiceBot application
app = VoiceBotApp(
    host="127.0.0.1",
    port=6050,
    on_speaker_done=on_speaker_done,
    menu_prompts_dir="recordings/prompts"
)
app.start()

# VoiceBot automatically:
# 1. Plays greeting after client connects (500ms delay)
# 2. Records client speech in numbered files
# 3. Detects 1.5s silence (speaker done)
# 4. Plays follow-up message
# 5. Hangs up after 3s silence
```

### Asterisk-conforming Client
```python
from src.simple_client import SimpleAudioSocketClient
import uuid

# Connect and send audio (Asterisk behavior)
client = SimpleAudioSocketClient("127.0.0.1", 5000)
client.connect()
client.send_uuid(uuid.uuid4().bytes)  # ast_audiosocket_init
client.send_audio(audio_data)         # ast_audiosocket_send_frame
received_audio = client.receive_audio()  # ast_audiosocket_receive_frame
client.close()
```

## Protocol Compliance

This implementation is based on the official Asterisk source code:
- `res_audiosocket.c` - Core protocol implementation
- `chan_audiosocket.c` - Channel driver implementation

All protocol constants, message formats, and error codes match the Asterisk implementation exactly.

**Key Asterisk Behaviors Implemented:**
- Client sends UUID during initialization (`ast_audiosocket_init`)
- Client sends audio frames (`ast_audiosocket_send_frame`)
- Client receives audio frames (`ast_audiosocket_receive_frame`)
- Client does NOT send hangup or error messages to server
- Server processes audio frames immediately (real-time)
- Client sends no audio during server playback (Asterisk spec compliance)

## License

This project is based on the Asterisk AudioSocket protocol and follows the same licensing terms as Asterisk.
