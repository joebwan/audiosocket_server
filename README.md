# Asterisk AudioSocket Server

A modern Python-based AudioSocket server for Asterisk that enables real-time audio streaming and processing of phone calls. This project provides a complete solution for building voice applications that integrate with Asterisk PBX systems through the AudioSocket protocol.

## 📡 AudioSocket Protocol Specification

This project implements the complete [Asterisk AudioSocket protocol](https://github.com/asterisk/asterisk/blob/certified/20.7/channels/chan_audiosocket.c) specification, which consists of:

- **Channel Driver** (`chan_audiosocket.c`) - Handles the channel interface
- **Resource Module** (`res_audiosocket.c`) - Manages socket connections and frame formatting

### Frame Format

The AudioSocket protocol uses a binary frame format:

```
[1 byte type][2 bytes length][variable payload]
```

**Frame Types:**
- `0x01` - UUID frame (call identification)
- `0x10` - Audio frame (actual audio data)
- `0x02` - Silence frame (silence indicator)
- `0x00` - Hangup frame (call termination)
- `0xFF` - Error frame (error conditions)

**Error Codes:**
- `0x00` - No error
- `0x01` - Called party hungup
- `0x02` - Failed to forward frame
- `0x04` - Memory allocation error

### Audio Characteristics

**Standard Audio Format:**
- **Sample Rate**: 8kHz (telephony standard)
- **Channels**: Mono (1 channel)
- **Bit Depth**: 16-bit PCM (little-endian)
- **Frame Duration**: 20ms
- **Frame Size**: 320 bytes exactly
- **Encoding**: Linear PCM (default) or ULAW

**Frame Size Calculation:**
```python
# 8kHz * 0.02s * 1 channel * 2 bytes = 320 bytes
frame_size = 8000 * 0.02 * 1 * 2 = 320
```

### Protocol Flow

1. **Connection Establishment**
   - TCP connection to AudioSocket server
   - Optional UUID frame sent for call identification

2. **Audio Exchange**
   - Asterisk sends audio frames every 20ms
   - Server must respond with audio frames of same size
   - Frame timing is critical for audio quality

3. **Error Handling**
   - Frame corruption detection
   - Memory allocation errors
   - Connection reset handling

### Implementation Requirements

To be fully compliant with the Asterisk AudioSocket specification, servers must:

1. **Handle variable frame sizes** (though 320 bytes is standard)
2. **Respond within frame timing** (20ms intervals)
3. **Process all frame types** (audio, silence, UUID, error, hangup)
4. **Maintain connection state** (connected/disconnected)
5. **Handle protocol errors** gracefully

## 🚀 Features

- **Real-time Audio Processing**: Low-latency audio streaming with 8kHz, 16-bit mono PCM
- **Voice Activity Detection**: Automatic speech detection using WebRTC VAD
- **Multi-language Support**: English and Hindi audio responses with configurable mappings
- **Silence Handling**: Intelligent silence detection and interruption handling
- **Audio Format Conversion**: Automatic ULAW ↔ Linear PCM conversion ([📖 Detailed Documentation](docs/audio_conversion.md))
- **Multi-threading**: Support for multiple simultaneous calls
- **Comprehensive Logging**: Colored console and file logging
- **Python 3.13+ Compatible**: Modern Python support with compatibility layers
- **Production Ready**: 65/65 tests passing with comprehensive coverage
- **Protocol Compliant**: Full implementation of Asterisk AudioSocket specification

## 📋 Prerequisites

### For Local Development (macOS)
- Python 3.7+ (recommended) or Python 3.8+
- pip (Python package installer)
- Git

### For Production Deployment (Ubuntu 24.04)
- Ubuntu 24.04 LTS
- Python 3.7+ or Python 3.8+
- Asterisk PBX (for production use)
- Systemd (for service management)

## 🛠️ Local Development Setup (macOS)

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd audiosocket_server
```

### 2. Create Virtual Environment
```bash
python3 -m venv py_env
source py_env/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Tests
```bash
python -m unittest discover -v
```

### 5. Start the Server
```bash
# Multi-threaded echo server (16kHz optimized)
python example_multithread.py

# Voice bot with VAD and multi-language support
python example_application.py

# Fixed version with improved protocol handling
python audiosocket_fixed.py
```

**Server Options:**
- **`example_multithread.py`**: Simple echo server optimized for 16kHz audio with ULAW conversion
- **`example_application.py`**: Full-featured voice bot with voice activity detection and multi-language support
- **`audiosocket_fixed.py`**: Improved AudioSocket implementation with better frame parsing

## 🐧 Ubuntu Server Setup

### Quick Installation (Recommended)
```bash
# Clone repository
git clone <your-repo-url> /opt/audiosocket_server
cd /opt/audiosocket_server

# Run installation script
chmod +x install_ubuntu.sh
./install_ubuntu.sh
```

### Manual Installation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git build-essential python3-dev

# Create virtual environment
python3 -m venv py_env
source py_env/bin/activate

# Install setuptools first (required for webrtcvad)
pip install setuptools>=65.0.0

# Install Python dependencies
pip install -r requirements.txt

# Test installation
python -m unittest discover -v
```

### Voice Activity Detection (VAD) Compatibility

The project uses `webrtcvad` for voice activity detection, which may have compatibility issues on some systems:

- **Python 3.12+**: Requires `setuptools>=65.0.0` for `pkg_resources`
- **System Libraries**: May require `build-essential` and `python3-dev`
- **Fallback Mode**: If VAD fails to load, the server will use simple amplitude-based detection

If VAD tests fail, the server will still work with reduced voice detection capabilities.

**For detailed VAD troubleshooting, see**: [VAD Troubleshooting Guide](docs/vad_troubleshooting.md)

## 🏗️ Project Structure

```
audiosocket_server/
├── audiosocket.py              # Main AudioSocket server class
├── audiosocket_fixed.py        # Fixed version with improved frame parsing
├── connection.py               # Connection handler and audio processing
├── connection_fixed.py         # Fixed connection with proper protocol handling
├── example_application.py      # Complete voice bot implementation
├── example_multithread.py      # Multi-threaded server example
├── mapping.py                  # Audio file configuration
├── mylogging.py                # Custom logging system
├── req.py                      # HTTP request wrapper
├── audioop_compat.py           # Python 3.13+ compatibility layer
├── agi.py                      # AGI (Asterisk Gateway Interface) helper
├── call.py                     # Call handling utilities
├── astrisk.py                  # Asterisk integration utilities
├── demo_audios/                # Audio files for voice responses
│   ├── en/                     # English audio files (14 files)
│   └── hi/                     # Hindi audio files (4 files)
├── docs/                       # Documentation
│   ├── audio_conversion.md     # Audio format conversion guide
│   └── audio_quality_testing.md # Audio quality troubleshooting
├── captured_audio/             # Captured audio files for analysis
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── requirements-optional.txt   # Optional dependencies
├── test_audiosocket.py         # Comprehensive test suite (47 tests)
├── test_example.py             # Example application tests (18 tests)
├── .pre-commit-config.yaml     # Pre-commit hooks configuration
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## 🔧 Configuration

### AudioSocket Protocol Configuration

**Optimal Configuration (Recommended):**
```python
# ✅ Protocol-compliant settings
self.audiosocket.prepare_input(
    inrate=8000,      # 8kHz telephony standard
    channels=1,       # Mono
    ulaw2lin=True     # Convert ULAW to PCM
)

self.audiosocket.prepare_output(
    outrate=8000,     # 8kHz telephony standard
    channels=1,       # Mono
    ulaw2lin=True     # Convert ULAW to PCM
)
```

**Frame Processing:**
```python
# Expected frame characteristics
expected_frame_size = 320  # bytes
expected_frame_interval = 0.02  # seconds (20ms)
expected_fps = 50  # frames per second

# Monitor frame timing
if len(audio_data) != expected_frame_size:
    # Handle frame size mismatch
    pass
```

### Audio File Mapping
Configure audio responses in `mapping.py`:
```python
mapping = {
    "en": {
        1: "demo_audios/en/hello.wav",
        2: "demo_audios/en/ask.wav",
        # ... more mappings (11 total)
    },
    "hi": {
        1: "demo_audios/hi/1.wav",
        2: "demo_audios/hi/2.wav",
        # ... more mappings (4 total)
    }
}
```

### Server Configuration
```python
# Create server instance
audiosocket = Audiosocket(("0.0.0.0", 1122))

# Configure audio processing (legacy - not recommended)
audiosocket.prepare_output(outrate=44000, channels=2)
audiosocket.prepare_input(inrate=44000, channels=2)
```

## 🧪 Testing

### Run All Tests
```bash
python -m unittest discover -v
```

### Test Results
```
Ran 65 tests in 0.474s
OK
```

### Test Coverage Breakdown
- **Core Infrastructure**: 31 tests (data structures, server, connections, logging)
- **Audio Processing**: 9 tests (format conversion, resampling, file generation)
- **Voice Activity Detection**: 5 tests (WebRTC VAD functionality)
- **AudioSocket Protocol**: 7 tests (message parsing, error handling)
- **Example Applications**: 13 tests (voice bot, mapping, requests)

### Run Specific Test Categories
```bash
# Test core functionality
python -m unittest test_audiosocket.TestAudiosocket -v

# Test connection handling
python -m unittest test_audiosocket.TestConnection -v

# Test audio processing
python -m unittest test_audiosocket.TestAudioFileGeneration -v

# Test voice activity detection
python -m unittest test_audiosocket.TestVoiceActivityDetection -v
```

### Test Quality Metrics
- **Execution Time**: ~0.5 seconds for full suite
- **Resource Management**: Proper cleanup of file handlers and temporary files
- **Mock Usage**: Comprehensive mocking of external dependencies
- **Error Coverage**: Invalid inputs, edge cases, and error conditions
- **Synthetic Data**: Realistic test audio generation for VAD and processing

## 🔍 Audio Quality Troubleshooting

### Common Issues and Solutions

**1. Choppy/Fast Audio**
- **Cause**: Incorrect sample rate (44kHz vs 8kHz)
- **Solution**: Use 8kHz telephony standard

**2. Poor Sound Quality**
- **Cause**: Wrong audio format (ULAW vs PCM)
- **Solution**: Enable ULAW to PCM conversion

**3. Echo Issues**
- **Cause**: Processing delays and frame size mismatches
- **Solution**: Proper frame timing and 320-byte frame validation

**4. Frame Size Errors**
- **Cause**: Inconsistent frame sizes (640 bytes vs expected 320)
- **Solution**: Monitor and validate frame sizes

### Real-time Monitoring

The protocol requires:
- **Frame size validation** (320 bytes expected)
- **Frame timing analysis** (~20ms intervals)
- **Audio format detection** (PCM vs ULAW)
- **Error condition handling** (memory, frame, hangup errors)

For detailed troubleshooting, see: [Audio Quality Testing Guide](docs/audio_quality_testing.md)

## 📚 Additional Resources

- [Asterisk AudioSocket Channel Driver](https://github.com/asterisk/asterisk/blob/certified/20.7/channels/chan_audiosocket.c)
- [Asterisk AudioSocket Resource Module](https://github.com/asterisk/asterisk/blob/certified/20.7/res/res_audiosocket.c)
- [Audio Conversion Documentation](docs/audio_conversion.md)
- [Audio Quality Testing Guide](docs/audio_quality_testing.md)

## 🤝 Contributing

This project implements the complete Asterisk AudioSocket protocol specification. When contributing:

1. Ensure protocol compliance with the [Asterisk specification](https://github.com/asterisk/asterisk/blob/certified/20.7/channels/chan_audiosocket.c)
2. Maintain frame timing requirements (20ms intervals)
3. Handle all message types (audio, silence, UUID, error, hangup)
4. Test with the provided test client
5. Follow the established code style and documentation standards

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Original AudioSocket implementation by CyCoreSystems
- WebRTC VAD for voice activity detection
- Asterisk community for PBX integration support

## 📞 Support

For issues and questions:
- Check the troubleshooting section above
- Review the test suite for usage examples
- Open an issue on GitHub with detailed error information

---

**Note**: This project is designed for telephony applications and is optimized for 8kHz sample rate audio processing. For high-fidelity audio applications, consider using higher sample rates and appropriate audio processing libraries.
