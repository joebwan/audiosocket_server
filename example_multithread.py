# Standard library imports
from threading import (  # Python's threading module - similar to java.lang.Thread or Node.js worker_threads
    Thread,
)

# Local imports
from audiosocket import (  # Custom library for handling audio socket connections
    Audiosocket,
)


class AudiosocketServer:
    """
    Multithreaded audio server that handles real-time audio connections.
    Similar to a WebSocket server in Node.js or SocketServer in Java, but designed for audio streaming.
    """

    def __init__(self):
        """
        Constructor method (similar to Java constructor or JavaScript constructor).
        Sets up the audio socket server with configuration.
        """
        # Create a globally accessible audiosocket instance
        self.audiosocket = Audiosocket(("0.0.0.0", 6050))

        # FIXED: Use 16kHz to match Asterisk configuration (based on diagnostic results)
        # Asterisk is sending 16kHz, mono, 16-bit PCM with 640-byte frames
        self.audiosocket.prepare_output(outrate=16000, channels=1, ulaw2lin=True)
        self.audiosocket.prepare_input(inrate=16000, channels=1, ulaw2lin=True)

        print(
            "Listening for new connections from Asterisk on port {}".format(
                self.audiosocket.port
            )
        )
        print("Audio Configuration: 16kHz, mono, 16-bit PCM with ULAW conversion (matches Asterisk)")

    def handle_connection(self, call):
        """
        Worker thread method that handles individual audio connections.
        This method runs in its own thread for each client connection.
        """
        cntr = 0

        print(f"Received connection from {call.peer_addr}")

        # Main audio processing loop - runs while connection is active
        while call.connected:
            # Read audio data from the client
            audio_data = call.read()

            # Echo the audio data back to the client (simple audio relay)
            call.write(audio_data)

            # Hangup the call after receiving 1000 audio frames
            # This is a simple way to limit the connection duration for testing
            if cntr == 1000:
                call.hangup()

            cntr += 1

        print(f"Connection with {call.peer_addr} is now over")

    def start(self):
        """
        Main server loop that accepts connections and spawns worker threads.
        This runs in the main thread and follows the thread-per-connection pattern.
        """
        while True:
            # Accept a new connection (blocking call)
            call = self.audiosocket.listen()

            # Create a new thread for this connection
            # Thread(target=function, args=(arg1, arg2)) - creates thread with target function and arguments
            call_thread = Thread(target=self.handle_connection, args=(call,))

            # Start the worker thread and continue listening for more connections
            call_thread.start()


# Create an instance of the AudiosocketServer class and start the server
server = AudiosocketServer()
server.start()
