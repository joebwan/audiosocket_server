#!/usr/bin/env python3
"""
Simple Handshake Server
Establishes AudioSocket connection, logs headers, and immediately hangs up.
Used to isolate network latency issues.
"""

import time
from audiosocket import Audiosocket
from mylogging import ColouredLogger


class SimpleHandshakeServer:
    """Simple server that just handles the AudioSocket handshake"""
    
    def __init__(self, host="0.0.0.0", port=6050):
        self.audiosocket = Audiosocket((host, port))
        self.host = host
        self.port = port
        self.logger = ColouredLogger("handshake")
        
        self.logger.info(f"Simple Handshake Server started on {host}:{port}")
        self.logger.info("This server will:")
        self.logger.info("1. Accept AudioSocket connections")
        self.logger.info("2. Log connection details and headers")
        self.logger.info("3. Send hangup message immediately")
        self.logger.info("4. Close connection")
        self.logger.info("")
        
    def handle_connection(self, call):
        """Handle AudioSocket connection - just log and hangup"""
        self.logger.info("=" * 50)
        self.logger.info("NEW CONNECTION")
        self.logger.info("=" * 50)
        
        # Log connection details
        self.logger.info(f"Peer address: {call.peer_addr}")
        self.logger.info(f"Call UUID: {getattr(call, 'uuid', 'Not set')}")
        self.logger.info(f"Connection time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Wait a moment for any initial frames
        time.sleep(0.1)
        
        # Log connection state
        self.logger.info(f"Connection state: connected={call.connected}")
        
        # Send hangup message
        self.logger.info("Sending hangup message...")
        try:
            call.hangup()
            self.logger.info("✅ Hangup message sent successfully")
        except Exception as e:
            self.logger.error(f"❌ Error sending hangup: {e}")
        
        # Wait a moment for hangup to process
        time.sleep(0.2)
        
        # Log final state
        self.logger.info(f"Final connection state: connected={call.connected}")
        self.logger.info("Connection handling complete")
        self.logger.info("=" * 50)
        self.logger.info("")
    
    def start(self):
        """Start the simple handshake server"""
        self.logger.info("Simple Handshake Server is running...")
        self.logger.info("Waiting for AudioSocket connections...")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("")
        
        connection_count = 0
        
        try:
            while True:
                # Accept connections
                call = self.audiosocket.listen()
                connection_count += 1
                
                self.logger.info(f"Connection #{connection_count} accepted")
                
                # Handle connection (this will block until connection ends)
                self.handle_connection(call)
                
        except KeyboardInterrupt:
            self.logger.info("")
            self.logger.info("Simple Handshake Server stopped by user")
            self.logger.info(f"Total connections handled: {connection_count}")
        except Exception as e:
            self.logger.error(f"Server error: {e}")


def main():
    """Main function"""
    print("Simple Handshake Server")
    print("======================")
    print("This server establishes AudioSocket connections and immediately hangs up.")
    print("Use this to test network connectivity and isolate latency issues.")
    print("\nFeatures:")
    print("- Accepts AudioSocket connections")
    print("- Logs connection details and headers")
    print("- Sends hangup message immediately")
    print("- No audio processing or buffering")
    print("\nThis should help identify if the issue is:")
    print("- Network connectivity")
    print("- AudioSocket protocol handshake")
    print("- Connection establishment timing")
    print("\nPress Ctrl+C to stop the server.\n")
    
    server = SimpleHandshakeServer()
    server.start()


if __name__ == "__main__":
    main() 