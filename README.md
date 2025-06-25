# Asterisk AudioSocket Server

A modern Python-based AudioSocket server for Asterisk that enables real-time audio streaming and processing of phone calls. This project provides a complete solution for building voice applications that integrate with Asterisk PBX systems through the AudioSocket protocol.

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
# Basic echo server
python example_multithread.py

# Voice bot with VAD
python example_application.py
```

## 🏗️ Project Structure

```
audiosocket_server/
├── audiosocket.py          # Main AudioSocket server class
├── connection.py           # Connection handler and audio processing
├── example_application.py  # Complete voice bot implementation
├── example_multithread.py  # Multi-threaded server example
├── mapping.py             # Audio file configuration
├── mylogging.py           # Custom logging system
├── req.py                 # HTTP request wrapper
├── audioop_compat.py      # Python 3.13+ compatibility layer
├── demo_audios/           # Audio files for voice responses
│   ├── en/               # English audio files (11 files)
│   └── hi/               # Hindi audio files (4 files)
├── requirements.txt       # Python dependencies
├── test_audiosocket.py    # Comprehensive test suite (47 tests)
├── test_example.py        # Example application tests (18 tests)
└── README.md             # This file
```

## 🔧 Configuration

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

# Configure audio processing
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

## 🛡️ Pre-commit Style Checks

This project uses [pre-commit](https://pre-commit.com/) to automatically check and enforce code style before each commit.

### Setup

1. Install pre-commit (if not already installed):
   ```bash
   pip install pre-commit
   ```
2. Install the pre-commit hooks:
   ```bash
   pre-commit install
   ```
   This will set up the hooks to run automatically on every commit.

### What Gets Checked
- **Black**: Code formatting (PEP 8, 4-space indentation, line length, etc.)
- **isort**: Import sorting (standard library, third-party, local)
- **pyupgrade**: Modern Python syntax (including f-strings)
- **Whitespace**: Trailing whitespace, end-of-file, YAML, large files
- **flake8**: PEP 8 compliance, naming, unused imports, etc. (manual only)

### Usage

- **On every commit:** Black, isort, pyupgrade, and whitespace checks will run and auto-fix issues. If any files are changed, the commit will be blocked and you must re-add and recommit.
- **flake8** will NOT block commits, but you can run it manually to see all style warnings:
  ```bash
  pre-commit run flake8 --all-files --hook-stage manual
  ```

### Example Workflow
```bash
# Make code changes
# ...
git add .
git commit -m "Your message"
# If style issues are auto-fixed, re-add and recommit
# To see all style warnings (not blocking):
pre-commit run flake8 --all-files --hook-stage manual
```

### Updating Hooks
To update all hooks to their latest versions:
```bash
pre-commit autoupdate
```

For more details, see the `.pre-commit-config.yaml` file in the repo.

## 🚀 Production Deployment (Ubuntu 24.04)

### 1. System Setup

#### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

#### Install Python and Dependencies
```bash
sudo apt install python3 python3-pip python3-venv git -y
```

#### Install Asterisk (if needed)
```bash
sudo apt install asterisk -y
```

### 2. Application Setup

#### Clone and Setup Application
```bash
# Clone repository
git clone <your-repo-url> /opt/audiosocket_server
cd /opt/audiosocket_server

# Create virtual environment
python3 -m venv py_env
source py_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set permissions
sudo chown -R asterisk:asterisk /opt/audiosocket_server
```

### 3. Systemd Service Configuration

#### Create Service File
```bash
sudo nano /etc/systemd/system/audiosocket.service
```

Add the following content:
```ini
[Unit]
Description=Asterisk AudioSocket Server
After=network.target asterisk.service
Wants=asterisk.service

[Service]
Type=simple
User=asterisk
Group=asterisk
WorkingDirectory=/opt/audiosocket_server
Environment=PATH=/opt/audiosocket_server/py_env/bin
ExecStart=/opt/audiosocket_server/py_env/bin/python example_multithread.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable audiosocket
sudo systemctl start audiosocket
sudo systemctl status audiosocket
```

### 4. Asterisk Configuration

#### Add to dialplan
Edit `/etc/asterisk/extensions.conf`:
```ini
[default]
exten => 1234,1,Answer()
exten => 1234,2,AudioSocket(uuid,127.0.0.1:1122)
exten => 1234,3,Hangup()
```

#### Reload Asterisk
```bash
sudo asterisk -rx "dialplan reload"
```

### 5. Firewall Configuration
```bash
# Allow AudioSocket port
sudo ufw allow 1122/tcp

# Allow Asterisk ports
sudo ufw allow 5060/udp  # SIP
sudo ufw allow 10000:20000/udp  # RTP
```

## 📊 Monitoring and Logs

### View Application Logs
```bash
# Systemd logs
sudo journalctl -u audiosocket -f

# Application logs
tail -f /opt/audiosocket_server/audiosocket.log
```

### Health Check
```bash
# Check service status
sudo systemctl status audiosocket

# Test connectivity
telnet localhost 1122
```

## 🔧 Advanced Configuration

### Custom Audio Processing
```python
from audiosocket import Audiosocket

# Create server with custom audio processing
audiosocket = Audiosocket(("0.0.0.0", 1122))

# Configure input audio processing
audiosocket.prepare_input(
    inrate=48000,      # Input sample rate
    channels=2,        # Input channels (stereo)
    ulaw2lin=True      # Convert ULAW to linear PCM
)

# Configure output audio processing
audiosocket.prepare_output(
    outrate=44100,     # Output sample rate
    channels=1,        # Output channels (mono)
    ulaw2lin=False     # Keep as linear PCM
)
```

### Voice Bot Customization
```python
from example_application import AudioStreamer

# Custom voice bot configuration
streamer = AudioStreamer(call)
streamer.channel = "en"  # Set language
streamer.level = 1       # Set initial level
```

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
sudo netstat -tlnp | grep :1122

# Kill the process if needed
sudo kill -9 <PID>
```

#### Permission Denied
```bash
# Fix permissions
sudo chown -R asterisk:asterisk /opt/audiosocket_server
sudo chmod +x /opt/audiosocket_server/*.py
```

#### Audio Issues
- Ensure audio files are 8kHz, 16-bit, mono WAV format
- Check audio file paths in `mapping.py`
- Verify audio file permissions

#### Python 3.13 Compatibility
The project includes a compatibility layer for `audioop` which was removed in Python 3.13. This is handled automatically.

### Debug Mode
```bash
# Run with debug logging
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from example_application import handle_call
handle_call()
"
```

## 📚 API Reference

### Audiosocket Class
```python
class Audiosocket:
    def __init__(self, bind_info, timeout=None)
    def prepare_input(self, inrate=44000, channels=2, ulaw2lin=False)
    def prepare_output(self, outrate=44000, channels=2, ulaw2lin=False)
    def listen(self)
```

### Connection Class
```python
class Connection:
    def read(self)
    def write(self, audio)
    def hangup(self)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure compatibility with Python 3.7+

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
