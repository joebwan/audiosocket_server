# Asterisk AudioSocket Server - Project Index

## Project Overview

This is a Python-based AudioSocket server for Asterisk that enables real-time audio streaming and processing of phone calls. The project provides a complete solution for integrating voice applications with Asterisk PBX systems through the AudioSocket protocol.

## Project Structure

### Core Components

#### 1. **audiosocket.py** - Main AudioSocket Server Class
- **Purpose**: Primary server class that handles AudioSocket connections
- **Key Features**:
  - Creates TCP socket server for AudioSocket connections
  - Supports audio resampling and format conversion
  - Handles input/output audio preparation
  - Manages connection lifecycle
- **Key Methods**:
  - `__init__(bind_info, timeout=None)`: Initialize server
  - `prepare_input(inrate=44000, channels=2, ulaw2lin=False)`: Configure input audio processing
  - `prepare_output(outrate=44000, channels=2, ulaw2lin=False)`: Configure output audio processing
  - `listen()`: Accept and return new connections

#### 2. **connection.py** - AudioSocket Connection Handler
- **Purpose**: Manages individual AudioSocket connections and audio processing
- **Key Features**:
  - Handles AudioSocket protocol messages (audio, UUID, errors, hangup)
  - Provides audio read/write operations
  - Supports audio format conversion (ULAW ↔ Linear PCM)
  - Manages audio queues for thread-safe operations
- **Key Methods**:
  - `read()`: Read audio data from Asterisk
  - `write(audio)`: Send audio data to Asterisk
  - `hangup()`: Terminate the call
  - `_process()`: Main processing loop (runs in separate thread)

#### 3. **example_application.py** - Voice Bot Application
- **Purpose**: Complete voice bot implementation with noise detection and audio playback
- **Key Features**:
  - Voice Activity Detection (VAD) using WebRTC
  - Multi-language audio response system (English/Hindi)
  - Silence detection and interruption handling
  - Audio file playback with proper timing
- **Key Classes**:
  - `AudioStreamer`: Main voice bot class
  - `handel_call()`: Main call handling function

### Supporting Components

#### 4. **mapping.py** - Audio File Configuration
- **Purpose**: Maps audio levels to specific audio files for different languages
- **Structure**:
  - English audio files: `demo_audios/en/`
  - Hindi audio files: `demo_audios/hi/`
  - Level-based mapping for different conversation states

#### 5. **mylogging.py** - Custom Logging System
- **Purpose**: Provides colored console logging and file logging
- **Features**:
  - Colored output for different log levels
  - File logging to `audiosocket.log`
  - Debug, info, warning, error, and critical levels

#### 6. **req.py** - HTTP Request Handler
- **Purpose**: Wrapper for HTTP requests with logging
- **Methods**: GET, POST, PUT, DELETE requests with debug logging

### Example Implementations

#### 7. **example_multithread.py** - Multi-threaded Server
- **Purpose**: Demonstrates handling multiple simultaneous calls
- **Features**:
  - Thread-per-connection architecture
  - Echo server functionality
  - Automatic call termination after 1000 frames

#### 8. **test.py** - Testing Framework
- **Purpose**: Test implementation for audio streaming
- **Features**: Audio data collection and HTTP posting

### Asterisk Integration

#### 9. **agi.py** - Asterisk Gateway Interface
- **Purpose**: AGI script for Asterisk integration
- **Features**:
  - Call answering
  - AudioSocket application execution
  - UUID generation for call tracking

#### 10. **astrisk.py** - Asterisk AGI Handler
- **Purpose**: Alternative AGI implementation
- **Features**:
  - Call answering and audio playback
  - Multi-processing for audio streaming
  - DTMF digit collection

### Audio Resources

#### 11. **demo_audios/** - Audio File Collection
- **Structure**:
  - `en/`: English audio files (hello.wav, ask.wav, voice1.wav, etc.)
  - `hi/`: Hindi audio files (1.wav, 2.wav, 3.wav, 4.wav)
- **Format**: WAV files, 8kHz, 16-bit, mono (telephony quality)

## Technical Specifications

### Audio Format Requirements
- **Input/Output**: 16-bit, 8kHz, mono LE PCM
- **Frame Size**: 320 bytes (20ms of audio)
- **Codec Support**: Linear PCM, ULAW (with conversion)
- **Resampling**: Built-in support for various sample rates

### Protocol Details
- **Transport**: TCP socket connection
- **Message Types**:
  - `0x01`: UUID message
  - `0x10`: Audio data
  - `0x02`: Silence
  - `0x00`: Hangup
  - `0xFF`: Error

### Dependencies
```
numpy          # Numerical computing
webrtcvad      # Voice Activity Detection
wave           # WAV file handling
threading      # Multi-threading support
requests       # HTTP requests
termcolor      # Colored console output
```

## Usage Patterns

### 1. Basic Echo Server
```python
from audiosocket import *
audiosocket = Audiosocket(("0.0.0.0", 1234))
connection = audiosocket.listen()
while connection.connected:
    data = connection.read()
    connection.write(data)
```

### 2. Voice Bot with VAD
```python
from example_application import AudioStreamer
# Initialize with call connection
streamer = AudioStreamer(call)
# Start voice detection and audio playback
streamer.start_noise_detection()
streamer.start_audio_playback(mapping)
```

### 3. Multi-threaded Server
```python
from example_multithread import AudiosocketServer
server = AudiosocketServer()
server.start()  # Handles multiple calls simultaneously
```

## Key Features

1. **Real-time Audio Processing**: Low-latency audio streaming
2. **Voice Activity Detection**: Automatic speech detection using WebRTC VAD
3. **Multi-language Support**: English and Hindi audio responses
4. **Silence Handling**: Intelligent silence detection and interruption
5. **Audio Format Conversion**: Automatic ULAW ↔ Linear PCM conversion
6. **Multi-threading**: Support for multiple simultaneous calls
7. **Comprehensive Logging**: Colored console and file logging
8. **Asterisk Integration**: AGI scripts for seamless PBX integration

## Development Notes

- The project is designed for telephony applications
- Audio processing is optimized for 8kHz sample rate
- Thread-safe operations using queues and locks
- Error handling for network disconnections
- Support for both standalone and channel driver AudioSocket modes

## File Size Summary
- **Core Files**: ~11KB (audiosocket.py, connection.py)
- **Examples**: ~10KB (example_application.py, example_multithread.py)
- **Audio Files**: ~1MB (demo_audios directory)
- **Total Project**: ~1.1MB

This project provides a complete foundation for building voice applications with Asterisk, from simple echo servers to complex voice bots with natural language processing capabilities.
