# Standard library imports
import socket
from dataclasses import dataclass
from threading import Thread
from time import sleep

# Local imports
from connection_fixed import ConnectionFixed


@dataclass
class AudioOpStruct:
    ratecv_state: None
    rate: int
    channels: int
    ulaw2lin: bool


class AudiosocketFixed:
    """AudioSocket server with proper variable-length frame parsing"""
    
    def __init__(self, bind_info, timeout=None):
        # By default, features of audioop (for example: resampling
        # or re-mixng input/output) are disabled
        self.user_resample = None
        self.asterisk_resample = None

        if not isinstance(bind_info, tuple):
            raise TypeError(
                "Expected tuple (addr, port), received", type(bind_info)
            )

        self.addr, self.port = bind_info

        self.initial_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.initial_sock.bind((self.addr, self.port))
        self.initial_sock.settimeout(timeout)
        self.initial_sock.listen(1)

        # If the user didn't specify a port, the one that the operating system
        # chose is available in this attribute
        self.port = self.initial_sock.getsockname()[1]

    # Optionally prepares audio sent by the user to
    # the specifications needed by audiosocket (16-bit, 8KHz mono LE PCM).
    # Audio sent in must be in PCM or ULAW format
    def prepare_input(self, inrate=44000, channels=2, ulaw2lin=False):
        self.user_resample = AudioOpStruct(
            rate=inrate,
            channels=channels,
            ulaw2lin=ulaw2lin,
            ratecv_state=None,
        )

    def get_uuid(self):
        data_types = TypesStruct()
        return data_types.uuid

    # Optionally prepares audio sent by audiosocket to
    # the specifications of the user
    def prepare_output(self, outrate=44000, channels=2, ulaw2lin=False):
        self.asterisk_resample = AudioOpStruct(
            rate=outrate,
            channels=channels,
            ulaw2lin=ulaw2lin,
            ratecv_state=None,
        )

    def listen(self):
        conn, peer_addr = self.initial_sock.accept()
        connection = ConnectionFixed(
            conn,
            peer_addr,
            self.user_resample,
            self.asterisk_resample,
        )

        connection_thread = Thread(target=connection._process, args=())
        connection_thread.start()

        return connection


# Backward compatibility - create alias for existing code
Audiosocket = AudiosocketFixed 