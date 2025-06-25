# Audio Quality Testing and Troubleshooting Guide

This guide helps diagnose and fix audio quality issues in the Asterisk AudioSocket Server.

## Common Audio Quality Issues

### 1. Choppy/Fast Audio
**Symptoms**: Audio plays too fast, sounds robotic, or has gaps
**Causes**: 
- Incorrect sample rate configuration
- Frame timing issues
- Buffer overflow/underflow

### 2. Poor Sound Quality
**Symptoms**: Audio sounds distorted, muffled, or unclear
**Causes**:
- Wrong audio format (ULAW vs PCM)
- Incorrect channel configuration
- Sample rate mismatches

### 3. Echo Issues
**Symptoms**: No echo, delayed echo, or distorted echo
**Causes**:
- Processing delays
- Frame size mismatches
- Audio format conversion problems

## Quick Fix: Use Improved Echo Server

The most common issue is incorrect audio configuration. Use the improved echo server:

```bash
# Stop the current server (Ctrl+C)
# Then run the improved version:
python example_echo_quality.py
```

**Key improvements**:
- ✅ 8kHz sample rate (telephony standard)
- ✅ Mono channels (not stereo)
- ✅ ULAW to PCM conversion enabled
- ✅ Proper frame timing
- ✅ Audio quality monitoring

## Audio Quality Test Suite

Run comprehensive audio quality tests:

```bash
python test_echo_quality.py
```

This will test:
- Audio configuration compatibility
- Processing speed and timing
- Frame timing accuracy
- Create test audio files

## Configuration Comparison

### ❌ Problematic Configuration (Original)
```python
# This causes audio quality issues
self.audiosocket.prepare_output(outrate=44000, channels=2)
self.audiosocket.prepare_input(inrate=44000, channels=2)
```

**Issues**:
- 44kHz is too high for telephony
- Stero channels cause format mismatches
- No ULAW conversion

### ✅ Correct Configuration (Fixed)
```python
# This provides good audio quality
self.audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)
self.audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
```

**Benefits**:
- 8kHz is telephony standard
- Mono channels match Asterisk expectations
- ULAW conversion handles format differences

## Testing Audio Quality Locally

### 1. Basic Echo Test
```bash
# Start the improved echo server
python example_echo_quality.py

# In another terminal, check the logs
tail -f audiosocket.log
```

**Expected Output**:
```
Audio Configuration: 8kHz, mono, 16-bit PCM with ULAW conversion
New connection from (IP, PORT)
Audio Stats: Frames=250, FPS=50.0, Elapsed=5.0s, FrameErrors=0
```

### 2. Frame Size Monitoring
The server monitors frame sizes. Look for:
- **Good**: Frame size = 320 bytes (20ms at 8kHz)
- **Bad**: Frame size ≠ 320 bytes (indicates format issues)

### 3. Frame Rate Monitoring
- **Good**: ~50 FPS (50 frames per second)
- **Bad**: < 40 FPS or > 60 FPS (timing issues)

## Advanced Testing

### 1. Audio Format Test
```bash
# Test different audio configurations
python test_echo_quality.py
```

### 2. Create Test Audio File
```bash
# This creates a 1kHz test tone
python test_echo_quality.py
# Look for: test_audio_1khz.wav
```

### 3. Performance Testing
```bash
# Test processing speed
python -c "
import time
start = time.time()
for i in range(1000):
    time.sleep(0.001)  # 1ms delay
end = time.time()
print(f'Processing speed: {(end-start)*1000:.2f}ms for 1000 frames')
"
```

## Troubleshooting Steps

### Step 1: Check Configuration
```python
# Verify your configuration matches this:
audiosocket.prepare_input(inrate=8000, channels=1, ulaw2lin=True)
audiosocket.prepare_output(outrate=8000, channels=1, ulaw2lin=True)
```

### Step 2: Monitor Frame Sizes
Look for this in the logs:
```
Unexpected frame size: 640 bytes (expected 320)
```
If you see this, there's a format mismatch.

### Step 3: Check Frame Rate
Look for this in the logs:
```
Audio Stats: Frames=250, FPS=50.0, Elapsed=5.0s
```
FPS should be around 50 (50 frames per second).

### Step 4: Test with Different Configurations
Try these configurations in order:

1. **Telephony Standard** (Recommended):
   ```python
   inrate=8000, channels=1, ulaw2lin=True
   outrate=8000, channels=1, ulaw2lin=True
   ```

2. **High Quality**:
   ```python
   inrate=16000, channels=1, ulaw2lin=True
   outrate=16000, channels=1, ulaw2lin=True
   ```

3. **Basic PCM**:
   ```python
   inrate=8000, channels=1, ulaw2lin=False
   outrate=8000, channels=1, ulaw2lin=False
   ```

## Performance Optimization

### 1. Minimize Processing Delays
```python
# Add minimal delay to prevent overwhelming
time.sleep(0.001)  # 1ms delay
```

### 2. Monitor Resource Usage
```bash
# Check CPU and memory usage
top -p $(pgrep -f "python.*echo")

# Check network usage
netstat -i
```

### 3. Buffer Management
- Ensure frame size is exactly 320 bytes
- Monitor for buffer overflow/underflow
- Add proper error handling

## Production Recommendations

### 1. Use Proper Configuration
Always use telephony-standard settings:
- Sample rate: 8kHz
- Channels: Mono
- Format: 16-bit PCM
- ULAW conversion: Enabled

### 2. Monitor Audio Quality
- Log frame sizes and timing
- Monitor frame rate consistency
- Track audio processing errors

### 3. Handle Errors Gracefully
- Catch and log audio processing errors
- Implement fallback mechanisms
- Monitor system resources

## Common Error Messages

### "Unexpected frame size"
**Cause**: Audio format mismatch
**Solution**: Check sample rate and channel configuration

### "Processing speed may cause audio issues"
**Cause**: System overload or timing issues
**Solution**: Add processing delays or optimize code

### "Frame timing may cause audio issues"
**Cause**: Inconsistent frame timing
**Solution**: Check system load and add timing controls

## Testing Checklist

Before deploying to production:

- [ ] Run audio quality tests: `python test_echo_quality.py`
- [ ] Test with improved echo server: `python example_echo_quality.py`
- [ ] Verify frame sizes are 320 bytes
- [ ] Confirm frame rate is ~50 FPS
- [ ] Test with actual phone calls
- [ ] Monitor logs for errors
- [ ] Check audio quality subjectively

## Getting Help

If you continue to experience audio quality issues:

1. **Check the logs**: Look for frame size and timing errors
2. **Run quality tests**: Use the provided test suite
3. **Try different configurations**: Test various sample rates and formats
4. **Monitor system resources**: Check CPU, memory, and network usage
5. **Use the improved echo server**: It has better error handling and monitoring

## Related Documentation

- [Audio Conversion Guide](audio_conversion.md)
- [VAD Troubleshooting Guide](vad_troubleshooting.md)
- [Installation Guide](../README.md) 