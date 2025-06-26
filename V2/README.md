# AudioSocket Server V2

A clean, test-first implementation of the Asterisk AudioSocket server based on the official Asterisk source code.

## Overview

This is a complete rewrite of the AudioSocket server implementation, built using a test-first approach and strict adherence to the Asterisk protocol specification. The implementation includes both strict protocol compliance and optional recording functionality for testing audio quality.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Virtual environment tool (venv, virtualenv, or conda)

### Setup Commands
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run all tests
python3 -m unittest discover tests -v
```

## Project Structure

```
V2/
├── src/                    # Source code
│   ├── protocol.py         # AudioSocket protocol definition
│   ├── simple_client.py    # Simple AudioSocket client implementation
│   └── simple_server.py    # Simple AudioSocket server implementation
├── tests/                  # Test suite
│   ├── test_protocol.py        # Protocol compliance tests
│   ├── test_simple_server.py   # Server protocol tests
│   ├── test_simple_client.py   # Client protocol tests
│   ├── test_integration.py     # End-to-end integration tests
│   ├── test_recording.py       # Recording functionality tests
│   └── test_logging.py         # Logging and debugging tests
├── requirements.txt       # Dependencies
├── .gitignore            # Git ignore rules
├── venv/                  # Python virtual environment (not tracked in version control)
└── README.md              # This file
```

**Note:** The recordings directory is created automatically when recording is enabled and a recording is saved.

## Development Approach

This implementation follows a strict test-first development paradigm:

1. **Protocol Definition**: Start with exact protocol specification from Asterisk source code
2. **Comprehensive Testing**: Write tests that validate against the Asterisk implementation
3. **Minimal Implementation**: Write only enough code to pass the tests
4. **Incremental Development**: Build functionality in small, focused groups

## Current Status

### Group 1: Protocol Definition and Constants ✅
- [x] Protocol constants matching Asterisk implementation
- [x] Message parsing according to `ast_audiosocket_receive_frame()`
- [x] Message creation according to `ast_audiosocket_send_frame()`
- [x] Comprehensive test suite with 44 tests

### Group 2: Server Architecture Simplification ✅
- [x] Minimal server implementation strictly matching Asterisk protocol
- [x] Real-time, frame-by-frame protocol handling
- [x] Connection management and resource cleanup

### Group 3: Client Implementation ✅
- [x] Simple AudioSocket client for testing server functionality
- [x] Protocol compliance and connection management
- [x] Error handling and resource cleanup

### Group 4: Integration Testing ✅
- [x] End-to-end protocol compliance tests
- [x] Multiple client scenarios
- [x] Error handling and cleanup verification

### Group 5: Audio Recording and File Management ✅
- [x] Optional recording functionality for testing audio quality
- [x] Configurable recording directory (created on-demand)
- [x] WAV file generation with proper audio format
- [x] UUID-based filename generation

### Group 6: Logging and Debugging ✅
- [x] Comprehensive logging of protocol events
- [x] Configurable logging levels
- [x] Connection and message tracking

## Feature Enhancements (TODO)

The following VoiceBot features are planned for future development. Each feature should be implemented individually with test-first development approach.

### VoiceBot Feature 1: Audio Playback System
**Goal**: Extending apps can "speak" to callers by streaming pre-recorded .wav files via AudioSocket
**Tasks**:
- [ ] Design audio playback architecture (file loading, streaming, buffering)
- [x] Implement WAV file loader and validator
- [x] Create audio streaming mechanism compatible with AudioSocket protocol
- [ ] Add audio playback queue management
- [ ] Implement server-side playback API (play WAV file over AudioSocket connection)
- [x] Write comprehensive tests for audio playback functionality
- [ ] Add configuration for audio file directory and supported formats

### VoiceBot Feature 2: Speech Recognition Integration
**Goal**: Server can transcribe speech from audio using external agents
**Tasks**:
- [ ] Design speech recognition service interface
- [ ] Implement audio preprocessing for speech recognition (format conversion, noise reduction)
- [ ] Create speech recognition agent integration (OpenAI Whisper, Google Speech-to-Text, etc.)
- [ ] Add transcription result handling and validation
- [ ] Implement retry logic and error handling for recognition failures
- [ ] Write tests for speech recognition functionality
- [ ] Add configuration for speech recognition service credentials and settings

### VoiceBot Feature 3: Text-to-Speech Integration
**Goal**: Server can generate speech from text using external agents
**Tasks**:
- [ ] Design TTS service interface
- [ ] Implement text preprocessing and validation
- [ ] Create TTS agent integration (OpenAI TTS, Google Text-to-Speech, etc.)
- [ ] Add audio format conversion for TTS output
- [ ] Implement TTS caching for performance optimization
- [ ] Write tests for TTS functionality
- [ ] Add configuration for TTS service credentials and voice settings

### VoiceBot Feature 4: Conversation Flow Management
**Goal**: Server can manage multi-turn conversations with callers
**Tasks**:
- [ ] Design conversation state management system
- [ ] Implement conversation flow controller
- [ ] Create prompt templates and variable substitution
- [ ] Add conversation history tracking
- [ ] Implement conversation timeout and cleanup
- [ ] Write tests for conversation flow management
- [ ] Add configuration for conversation settings and timeouts

### VoiceBot Feature 5: Name Collection Workflow
**Goal**: Complete end-to-end name collection workflow
**Tasks**:
- [ ] Implement "What's your name?" prompt playback
- [ ] Add speech recognition for name transcription
- [ ] Implement name validation and confirmation
- [ ] Create "Thank you <name>, goodbye." TTS generation
- [ ] Add error handling for unclear names or recognition failures
- [ ] Write integration tests for complete name collection workflow
- [ ] Add configuration for name collection settings

### VoiceBot Feature 6: Advanced Audio Processing
**Goal**: Enhanced audio quality and processing capabilities
**Tasks**:
- [ ] Implement audio format conversion utilities
- [ ] Add audio quality enhancement (noise reduction, echo cancellation)
- [ ] Create audio streaming optimization for real-time processing
- [ ] Implement audio buffering and synchronization
- [ ] Add audio level monitoring and automatic gain control
- [ ] Write tests for audio processing functionality
- [ ] Add configuration for audio processing settings

### VoiceBot Feature 7: Configuration and Deployment
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

### Optional Recording Functionality
- **Configurable Recording**: Enable/disable recording via constructor parameter
- **On-demand Directory Creation**: Recordings directory created only when needed
- **Configurable Path**: Custom recording directory path support
- **WAV Format**: Standard WAV files with proper audio format headers
- **UUID-based Naming**: Recordings named using client UUID for easy identification

### Testing and Development
- **Test-first Development**: 44 comprehensive tests covering all functionality
- **Integration Testing**: End-to-end client-server interaction tests
- **Mock Client**: Simple client implementation for server testing
- **Clean Architecture**: Minimal, focused implementation

## Running Tests

To run all tests:

```bash
cd V2
python3 -m unittest discover tests -v
```

Or run a specific test file:

```bash
python3 -m unittest tests.test_simple_server -v
python3 -m unittest tests.test_simple_client -v
python3 -m unittest tests.test_integration -v
python3 -m unittest tests.test_protocol -v
python3 -m unittest tests.test_recording -v
python3 -m unittest tests.test_logging -v
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

### Simple Client
```python
from src.simple_client import SimpleAudioSocketClient

# Connect and send audio
client = SimpleAudioSocketClient("127.0.0.1", 5000)
client.connect()
client.send_uuid(uuid.uuid4())
client.send_audio(audio_data)
client.send_hangup()
client.disconnect()
```

## Protocol Compliance

This implementation is based on the official Asterisk source code:
- `res_audiosocket.c` - Core protocol implementation
- `chan_audiosocket.c` - Channel driver implementation

All protocol constants, message formats, and error codes match the Asterisk implementation exactly.

## License

This project is based on the Asterisk AudioSocket protocol and follows the same licensing terms as Asterisk. 