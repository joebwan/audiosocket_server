#!/usr/bin/env python3
"""
Performance Diagnostic Tool
Identifies bottlenecks causing audio frame timing delays and low frame rates.
"""

import time
import psutil
import threading
from collections import deque
from threading import Thread

from audiosocket import Audiosocket
from mylogging import ColouredLogger


class PerformanceDiagnostic:
    """Diagnoses performance issues affecting audio frame timing"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        
        # Don't set audio format - use defaults
        self.logger = ColouredLogger("performance_diagnostic")
        self.logger.info(f"Performance diagnostic started on {host}:{port}")
        
        # Performance tracking
        self.frame_timings = deque(maxlen=100)
        self.processing_times = deque(maxlen=100)
        self.system_stats = {}
        
        # Start system monitoring
        self.monitoring = True
        self.monitor_thread = Thread(target=self.monitor_system, daemon=True)
        self.monitor_thread.start()
        
    def monitor_system(self):
        """Monitor system resources in background"""
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Memory usage
                memory = psutil.virtual_memory()
                
                # Network I/O
                net_io = psutil.net_io_counters()
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                
                self.system_stats = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': memory.available / (1024**3),  # GB
                    'net_bytes_sent': net_io.bytes_sent,
                    'net_bytes_recv': net_io.bytes_recv,
                    'disk_read_bytes': disk_io.read_bytes if disk_io else 0,
                    'disk_write_bytes': disk_io.write_bytes if disk_io else 0,
                    'timestamp': time.time()
                }
                
                time.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                self.logger.error(f"System monitoring error: {e}")
                time.sleep(5)
    
    def analyze_performance(self):
        """Analyze performance data and identify bottlenecks"""
        if not self.frame_timings:
            return "No frame timing data available"
        
        # Calculate timing statistics
        intervals = list(self.frame_timings)
        processing_times = list(self.processing_times)
        
        avg_interval = sum(intervals) / len(intervals)
        min_interval = min(intervals)
        max_interval = max(intervals)
        
        avg_processing = sum(processing_times) / len(processing_times) if processing_times else 0
        max_processing = max(processing_times) if processing_times else 0
        
        # Calculate frame rate
        fps = 1.0 / avg_interval if avg_interval > 0 else 0
        
        # Identify bottlenecks
        bottlenecks = []
        
        if avg_interval > 0.05:  # More than 50ms
            bottlenecks.append("SEVERE: Frame intervals too slow (>50ms)")
        elif avg_interval > 0.03:  # More than 30ms
            bottlenecks.append("HIGH: Frame intervals slow (>30ms)")
        elif avg_interval > 0.025:  # More than 25ms
            bottlenecks.append("MEDIUM: Frame intervals above normal (>25ms)")
        
        if fps < 20:
            bottlenecks.append("SEVERE: Frame rate too low (<20 FPS)")
        elif fps < 30:
            bottlenecks.append("HIGH: Frame rate low (<30 FPS)")
        elif fps < 40:
            bottlenecks.append("MEDIUM: Frame rate below optimal (<40 FPS)")
        
        if max_processing > 0.01:  # More than 10ms processing time
            bottlenecks.append("HIGH: Processing time too slow (>10ms)")
        elif max_processing > 0.005:  # More than 5ms
            bottlenecks.append("MEDIUM: Processing time slow (>5ms)")
        
        # System resource analysis
        if self.system_stats:
            cpu = self.system_stats.get('cpu_percent', 0)
            memory = self.system_stats.get('memory_percent', 0)
            
            if cpu > 80:
                bottlenecks.append("SEVERE: CPU usage very high (>80%)")
            elif cpu > 60:
                bottlenecks.append("HIGH: CPU usage high (>60%)")
            
            if memory > 90:
                bottlenecks.append("SEVERE: Memory usage very high (>90%)")
            elif memory > 80:
                bottlenecks.append("HIGH: Memory usage high (>80%)")
        
        return {
            'avg_interval': avg_interval,
            'min_interval': min_interval,
            'max_interval': max_interval,
            'fps': fps,
            'avg_processing': avg_processing,
            'max_processing': max_processing,
            'bottlenecks': bottlenecks,
            'system_stats': self.system_stats
        }
    
    def handle_connection(self, call):
        """Handle connection with performance monitoring"""
        self.logger.info(f"New connection from {call.peer_addr}")
        
        frame_count = 0
        start_time = time.time()
        last_frame_time = start_time
        
        while call.connected and frame_count < 200:  # Monitor first 200 frames
            try:
                # Measure processing time
                process_start = time.time()
                
                # Read audio data
                audio_data = call.read()
                frame_size = len(audio_data)
                
                # Echo back
                call.write(audio_data)
                
                # Measure processing time
                process_end = time.time()
                processing_time = process_end - process_start
                
                frame_count += 1
                current_time = time.time()
                
                # Track timing
                if frame_count > 1:
                    interval = current_time - last_frame_time
                    self.frame_timings.append(interval)
                    self.processing_times.append(processing_time)
                
                last_frame_time = current_time
                
                # Log every 50 frames
                if frame_count % 50 == 0:
                    self.logger.info(f"Frame {frame_count}: {frame_size} bytes, "
                                   f"Interval: {interval*1000:.1f}ms, "
                                   f"Processing: {processing_time*1000:.1f}ms")
                
                # Add minimal delay
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Error in diagnostic loop: {e}")
                break
        
        # Final analysis
        self.logger.info("\n" + "="*60)
        self.logger.info("PERFORMANCE ANALYSIS")
        self.logger.info("="*60)
        
        analysis = self.analyze_performance()
        
        self.logger.info(f"Frame timing analysis:")
        self.logger.info(f"  Average interval: {analysis['avg_interval']*1000:.1f}ms")
        self.logger.info(f"  Min interval: {analysis['min_interval']*1000:.1f}ms")
        self.logger.info(f"  Max interval: {analysis['max_interval']*1000:.1f}ms")
        self.logger.info(f"  Frame rate: {analysis['fps']:.1f} FPS")
        
        self.logger.info(f"Processing time analysis:")
        self.logger.info(f"  Average processing: {analysis['avg_processing']*1000:.1f}ms")
        self.logger.info(f"  Max processing: {analysis['max_processing']*1000:.1f}ms")
        
        if analysis['system_stats']:
            stats = analysis['system_stats']
            self.logger.info(f"System resources:")
            self.logger.info(f"  CPU usage: {stats.get('cpu_percent', 0):.1f}%")
            self.logger.info(f"  Memory usage: {stats.get('memory_percent', 0):.1f}%")
            self.logger.info(f"  Available memory: {stats.get('memory_available', 0):.1f} GB")
        
        if analysis['bottlenecks']:
            self.logger.info(f"Identified bottlenecks:")
            for bottleneck in analysis['bottlenecks']:
                self.logger.info(f"  ⚠️  {bottleneck}")
        else:
            self.logger.info("✓ No performance bottlenecks detected")
        
        self.logger.info("="*60)
        
        # Continue normal echo operation
        self.logger.info("Switching to normal echo mode...")
        while call.connected:
            try:
                audio_data = call.read()
                call.write(audio_data)
                time.sleep(0.001)
            except Exception as e:
                self.logger.error(f"Error in echo loop: {e}")
                break
        
        self.logger.info(f"Connection ended. Total frames: {frame_count}")
    
    def start(self):
        """Start the performance diagnostic server"""
        while True:
            try:
                call = self.audiosocket.listen()
                thread = Thread(target=self.handle_connection, args=(call,))
                thread.daemon = True
                thread.start()
            except KeyboardInterrupt:
                self.monitoring = False
                self.logger.info("Diagnostic stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Performance Diagnostic Tool")
    print("==========================")
    print("This tool identifies performance bottlenecks affecting audio quality.")
    print("\nMonitors:")
    print("- Frame timing and intervals")
    print("- Processing time per frame")
    print("- CPU and memory usage")
    print("- Network and disk I/O")
    print("- System resource utilization")
    print("\nConnect your Asterisk AudioSocket and make a call.\n")
    
    diagnostic = PerformanceDiagnostic()
    diagnostic.start()


if __name__ == "__main__":
    main() 