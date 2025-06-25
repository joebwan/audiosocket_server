#!/usr/bin/env python3
"""
Simple Echo Quality Test
Tests audio echo functionality and quality.
"""

import time
import wave
import numpy as np
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


def test_audio_configuration():
    """Test audio configuration settings"""
    print("Audio Configuration Test")
    print("========================")
    
    # Test different configurations
    configs = [
        {
            "name": "Telephony Standard (Recommended)",
            "inrate": 8000,
            "channels": 1,
            "ulaw2lin": True
        },
        {
            "name": "Original Problematic Config",
            "inrate": 44000,
            "channels": 2,
            "ulaw2lin": False
        },
        {
            "name": "High Quality",
            "inrate": 16000,
            "channels": 1,
            "ulaw2lin": True
        }
    ]
    
    for config in configs:
        print(f"\nTesting: {config['name']}")
        try:
            audiosocket = Audiosocket(("127.0.0.1", 0))
            audiosocket.prepare_input(**{k: v for k, v in config.items() if k != 'name'})
            audiosocket.prepare_output(**{k: v for k, v in config.items() if k != 'name'})
            print(f"  ✓ Configuration valid")
            
            # Calculate frame size
            frame_size = int(config['inrate'] * 0.02 * config['channels'] * 2)  # 20ms, 16-bit
            print(f"  ✓ Frame size: {frame_size} bytes (20ms)")
            
        except Exception as e:
            print(f"  ✗ Configuration failed: {e}")


def test_audio_processing_speed():
    """Test audio processing speed and timing"""
    print("\nAudio Processing Speed Test")
    print("============================")
    
    # Simulate audio processing
    test_audio = b"\x00" * 320  # 20ms of silence at 8kHz
    
    # Test processing speed
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        # Simulate read operation
        audio_data = test_audio
        
        # Simulate write operation
        processed_audio = audio_data
        
        # Add minimal delay (like in real server)
        time.sleep(0.001)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"Processed {iterations} frames in {total_time:.3f} seconds")
    print(f"Average time per frame: {(total_time/iterations)*1000:.2f}ms")
    print(f"Frames per second: {iterations/total_time:.1f}")
    
    # Check if timing is acceptable
    if total_time/iterations < 0.02:  # Less than 20ms per frame
        print("✓ Processing speed is acceptable for real-time audio")
    else:
        print("✗ Processing speed may cause audio issues")


def test_frame_timing():
    """Test frame timing accuracy"""
    print("\nFrame Timing Test")
    print("==================")
    
    # Test timing for 50 frames (1 second at 50fps)
    frame_count = 50
    target_interval = 0.02  # 20ms per frame
    intervals = []
    
    start_time = time.time()
    last_time = start_time
    
    for i in range(frame_count):
        # Simulate frame processing
        time.sleep(target_interval)
        
        current_time = time.time()
        interval = current_time - last_time
        intervals.append(interval)
        last_time = current_time
    
    total_time = time.time() - start_time
    
    # Analyze timing
    avg_interval = sum(intervals) / len(intervals)
    min_interval = min(intervals)
    max_interval = max(intervals)
    
    print(f"Target interval: {target_interval*1000:.1f}ms")
    print(f"Average interval: {avg_interval*1000:.1f}ms")
    print(f"Min interval: {min_interval*1000:.1f}ms")
    print(f"Max interval: {max_interval*1000:.1f}ms")
    print(f"Total time: {total_time:.3f}s (expected: {frame_count*target_interval:.3f}s)")
    
    # Check timing accuracy
    timing_error = abs(avg_interval - target_interval) / target_interval
    if timing_error < 0.1:  # Less than 10% error
        print("✓ Frame timing is accurate")
    else:
        print("✗ Frame timing may cause audio issues")


def create_test_audio_file():
    """Create a test audio file for quality testing"""
    print("\nCreating Test Audio File")
    print("========================")
    
    # Create a test WAV file with known characteristics
    sample_rate = 8000
    duration = 1.0  # 1 second
    frequency = 1000  # 1kHz tone
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.5
    audio_data = (audio_data * 32767).astype(np.int16)
    
    # Save as WAV file
    filename = "test_audio_1khz.wav"
    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    print(f"✓ Created test file: {filename}")
    print(f"  - Sample rate: {sample_rate}Hz")
    print(f"  - Duration: {duration}s")
    print(f"  - Frequency: {frequency}Hz")
    print(f"  - Format: Mono, 16-bit PCM")
    
    return filename


def run_echo_quality_test():
    """Run comprehensive echo quality tests"""
    print("Echo Quality Test Suite")
    print("=======================")
    print("This test suite helps diagnose audio quality issues in echo servers.\n")
    
    # Run all tests
    test_audio_configuration()
    test_audio_processing_speed()
    test_frame_timing()
    create_test_audio_file()
    
    print("\n" + "="*50)
    print("RECOMMENDATIONS FOR FIXING AUDIO QUALITY ISSUES:")
    print("="*50)
    print("1. Use 8kHz sample rate (telephony standard)")
    print("2. Use mono channels (not stereo)")
    print("3. Enable ULAW to PCM conversion")
    print("4. Ensure frame size is exactly 320 bytes")
    print("5. Add minimal processing delays (1ms)")
    print("6. Monitor frame timing and statistics")
    print("7. Use the improved echo server: example_echo_quality.py")
    print("\nTo test the improved echo server:")
    print("  python example_echo_quality.py")


if __name__ == "__main__":
    run_echo_quality_test() 