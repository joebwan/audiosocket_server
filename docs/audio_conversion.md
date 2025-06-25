# Audio Format Conversion: ULAW ↔ Linear PCM

This document explains the automatic audio format conversion feature that enables seamless handling of both ULAW (μ-law) and Linear PCM audio formats in the Asterisk AudioSocket Server.

## Overview

The AudioSocket server includes built-in support for converting between ULAW and Linear PCM audio formats. This is essential for telephony applications where different codecs may be used throughout the audio processing pipeline.

### Why Audio Conversion Matters

- **Telephony Standards**: ULAW is a common telephony codec that compresses 16-bit audio to 8-bit
- **Asterisk Compatibility**: Many Asterisk configurations use ULAW for audio transmission
- **Processing Requirements**: Linear PCM is easier to process for voice activity detection and audio analysis
- **Quality Preservation**: Accurate conversion without quality loss

## Technical Implementation

### 1. Conversion Algorithm

The conversion uses a pre-computed lookup table that maps each 8-bit ULAW value to its corresponding 16-bit Linear PCM value:

```python
def ulaw2lin(data, width):
    """Convert u-law encoded data to linear PCM"""
    if width != 2:
        raise ValueError("Only 16-bit audio supported")

    # u-law decoding table - 256 values (128 negative + 128 positive)
    ulaw_table = [
        -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
        -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
        # ... complete table with 256 values
        32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
        # ... positive values
    ]

    # Convert bytes to list of u-law values
    ulaw_values = list(data)

    # Convert each u-law value to linear PCM
    linear_values = []
    for ulaw_val in ulaw_values:
        if ulaw_val < 128:
            linear_val = ulaw_table[ulaw_val]  # Negative values
        else:
            linear_val = ulaw_table[ulaw_val - 128]  # Positive values
        linear_values.append(linear_val)

    # Convert to bytes as 16-bit little-endian integers
    return struct.pack(f'<{len(linear_values)}h', *linear_values)
```

### 2. Conversion Process

1. **Input**: 8-bit ULAW encoded bytes (0-255 range)
2. **Lookup**: Each byte is mapped to a 16-bit linear PCM value using the pre-computed table
3. **Output**: 16-bit signed integers representing the original audio waveform
4. **Format**: Little-endian 16-bit integers packed as bytes

### 3. When Conversion Happens

The conversion is applied in two scenarios:

#### A. Reading Audio from Asterisk
```python
def read(self):
    # ... get audio from queue ...

    if self._asterisk_resample:
        # If AudioSocket is bridged with a channel using ULAW codec,
        # convert to linear encoding upon reading
        if self._asterisk_resample.ulaw2lin:
            audio = audioop.ulaw2lin(audio, 2)
```

#### B. Writing Audio to Asterisk
```python
def write(self, audio):
    if self._user_resample:
        # Convert ULAW encoded source audio to linear encoding
        if self._user_resample.ulaw2lin:
            audio = audioop.ulaw2lin(audio, 2)
```

## Configuration

### Enabling ULAW Conversion

Configure the conversion when setting up the AudioSocket server:

```python
from audiosocket import Audiosocket

# Create server instance
audiosocket = Audiosocket(("0.0.0.0", 1122))

# Enable ULAW conversion for input audio (from Asterisk)
audiosocket.prepare_input(
    inrate=8000,      # Input sample rate
    channels=1,       # Input channels (mono)
    ulaw2lin=True     # Enable ULAW to Linear PCM conversion
)

# Enable ULAW conversion for output audio (to Asterisk)
audiosocket.prepare_output(
    outrate=8000,     # Output sample rate
    channels=1,       # Output channels (mono)
    ulaw2lin=True     # Enable ULAW to Linear PCM conversion
)
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ulaw2lin` | bool | `False` | Enable/disable ULAW conversion |
| `inrate` | int | `44000` | Input sample rate |
| `outrate` | int | `44000` | Output sample rate |
| `channels` | int | `2` | Number of audio channels |

## Usage Examples

### 1. Basic Echo Server with ULAW Conversion

```python
from audiosocket import Audiosocket

# Create server with ULAW conversion enabled
audiosocket = Audiosocket(("0.0.0.0", 1122))
audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)

# Handle connection
connection = audiosocket.listen()
while connection.connected:
    audio_data = connection.read()  # Automatically converts ULAW to Linear PCM
    connection.write(audio_data)    # Automatically converts Linear PCM to ULAW
```

### 2. Voice Bot with Audio Processing

```python
from audiosocket import Audiosocket
from example_application import AudioStreamer

# Create server with ULAW conversion
audiosocket = Audiosocket(("0.0.0.0", 1122))
audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)

# Handle connection with voice processing
connection = audiosocket.listen()
streamer = AudioStreamer(connection)

# Start voice activity detection (works with Linear PCM)
streamer.start_noise_detection()
streamer.start_audio_playback(mapping)
```

### 3. Multi-threaded Server with Conversion

```python
from audiosocket import Audiosocket
from threading import Thread

class AudiosocketServer:
    def __init__(self):
        self.audiosocket = Audiosocket(('0.0.0.0', 1122))

        # Enable ULAW conversion for all connections
        self.audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
        self.audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)

    def handle_connection(self, call):
        while call.connected:
            audio_data = call.read()  # ULAW → Linear PCM
            # Process audio in Linear PCM format
            processed_audio = self.process_audio(audio_data)
            call.write(processed_audio)  # Linear PCM → ULAW

    def start(self):
        while True:
            call = self.audiosocket.listen()
            call_thread = Thread(target=self.handle_connection, args=(call,))
            call_thread.start()
```

## Compatibility

### Python Version Support

The conversion feature includes a compatibility layer for Python 3.13+ where the `audioop` module was removed:

```python
try:
    import audioop
except ImportError:
    # Fallback for Python 3.13+ where audioop was removed
    import audioop_compat as audioop
```

### Audio Format Requirements

- **Input ULAW**: 8-bit encoded audio data
- **Output Linear PCM**: 16-bit signed integers, little-endian
- **Sample Rate**: Supports various rates (typically 8kHz for telephony)
- **Channels**: Mono and stereo support

## Performance Considerations

### Memory Usage

- **Lookup Table**: 256 16-bit values (512 bytes) for conversion
- **Processing**: Minimal memory overhead during conversion
- **Buffering**: Uses existing audio buffers

### CPU Usage

- **Lookup-based**: O(n) time complexity where n is the number of audio samples
- **Efficient**: Table lookup is faster than mathematical conversion
- **Optimized**: Uses NumPy for bulk operations when available

### Latency

- **Real-time**: Conversion happens inline with audio processing
- **Minimal Delay**: Lookup table ensures fast conversion
- **Predictable**: Constant time per audio frame

## Troubleshooting

### Common Issues

#### 1. Audio Distortion
**Problem**: Converted audio sounds distorted or noisy
**Solution**: Ensure input audio is valid ULAW format and sample rate matches configuration

#### 2. Conversion Not Working
**Problem**: ULAW conversion doesn't seem to be applied
**Solution**: Verify `ulaw2lin=True` is set in both `prepare_input()` and `prepare_output()`

#### 3. Performance Issues
**Problem**: High CPU usage during audio processing
**Solution**: Check if conversion is being applied multiple times unnecessarily

### Debug Mode

Enable debug logging to monitor conversion:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Monitor conversion in connection.py
# Look for audioop.ulaw2lin() calls in logs
```

## Advanced Usage

### Custom Conversion

For advanced use cases, you can implement custom conversion logic:

```python
def custom_ulaw_conversion(audio_data):
    """Custom ULAW to Linear PCM conversion"""
    # Your custom implementation
    return converted_audio

# Use in connection handling
if self._asterisk_resample.ulaw2lin:
    audio = custom_ulaw_conversion(audio)
```

### Batch Processing

For processing large audio files:

```python
def process_audio_file(filename):
    with open(filename, 'rb') as f:
        audio_data = f.read()

    # Convert in chunks
    chunk_size = 320  # 20ms at 8kHz
    converted_chunks = []

    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i+chunk_size]
        converted_chunk = audioop.ulaw2lin(chunk, 2)
        converted_chunks.append(converted_chunk)

    return b''.join(converted_chunks)
```

## Related Documentation

- [Main README](../README.md) - Overview and setup instructions
- [API Reference](../README.md#api-reference) - Complete API documentation
- [Testing Guide](../README.md#testing) - How to test audio conversion
- [Troubleshooting](../README.md#troubleshooting) - Common issues and solutions

---

**Note**: This conversion feature is designed for telephony applications and is optimized for 8kHz sample rate audio processing. For high-fidelity audio applications, consider using higher sample rates and appropriate audio processing libraries.
