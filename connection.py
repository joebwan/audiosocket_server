# Standard library imports
try:
    import audioop
except ImportError:
    # Fallback for Python 3.13+ where audioop was removed
    import audioop_compat as audioop

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Lock
from time import sleep


# A sort of imitation struct that holds all of the possible
# AudioSocket message types
@dataclass(frozen=True)
class TypesStruct:
    uuid: bytes = (
        b"\x01"  # Message payload contains UUID set in Asterisk Dialplan
    )
    audio: bytes = (
        b"\x10"  # Message payload contains 8Khz 16-bit mono LE PCM audio
    )
    silence: bytes = b"\x02"  # Message payload contains silence
    hangup: bytes = b"\x00"  # Tell Asterisk to hangup the call
    error: bytes = b"\xff"  # Message payload contains an error from Asterisk


types = TypesStruct()


# The size of 20ms of 8KHz 16-bit mono LE PCM represented as a
# 16 bit (2 byte, size of length header) unsigned BE integer
# This amount of the audio data mentioned above is equal
# to 320 bytes, which is the required payload size when
# sending audio back to AudioSocket for playback on the
# bridged channel. Sending more or less data will result in distorted sound
PCM_SIZE = (320).to_bytes(2, "big")


# Similar to one above, this holds all the possible
# AudioSocket related error codes Asterisk can send us
@dataclass(frozen=True)
class ErrorsStruct:
    none: bytes = b"\x00"
    hangup: bytes = b"\x01"
    frame: bytes = b"\x02"
    memory: bytes = b"\x04"


errors = ErrorsStruct()


class Connection:
    def __init__(self, conn, peer_addr, user_resample, asterisk_resample):
        self.conn = conn
        self.peer_addr = peer_addr
        self.uuid = None
        self.connected = (
            True  # An instance gets created because a connection occurred
        )
        self._user_resample = user_resample
        self._asterisk_resample = asterisk_resample

        # Underlying Queue objects for passing incoming/outgoing audio between threads
        self._rx_q = Queue(500)
        self._tx_q = Queue(500)
        self._lock = Lock()

        # Header logging
        self._header_logged = False
        self._frame_count = 0

    # Splits data sent by AudioSocket into three different pieces
    def _split_data(self, data):
        if len(data) < 3:
            print(
                "[AUDIOSOCKET WARNING] The data received was less than 3 bytes, "
                "the minimum length data from Asterisk AudioSocket should be."
            )
            print(f"[AUDIOSOCKET DEBUG] Received data: {data!r}")
            return b"\x00", 0, bytes(320)
        else:
            # type      length                            payload
            msg_type = data[:1]
            msg_length = int.from_bytes(data[1:3], "big")
            payload = data[3:]
            
            # Log header information for first few frames
            if not self._header_logged or self._frame_count < 10:
                print(f"[AUDIOSOCKET DEBUG] Frame {self._frame_count + 1}: Type={msg_type!r}, Length={msg_length}, Payload size={len(payload)}")
                if self._frame_count == 0:
                    print(f"[AUDIOSOCKET DEBUG] First frame data: {data!r}")
                    self._header_logged = True
            
            self._frame_count += 1
            return msg_type, msg_length, payload

    # If the type of message received was an error, this
    # prints an explanation of the specific one that occurred
    def _decode_error(self, payload):
        if payload == errors.none:
            print("[ASTERISK ERROR] No error code present")
        elif payload == errors.hangup:
            print("[ASTERISK ERROR] The called party hungup")
        elif payload == errors.frame:
            print("[ASTERISK ERROR] Failed to forward frame")
        elif payload == errors.memory:
            print("[ASTERISK ERROR] Memory allocation error")
        return

    # Gets AudioSocket audio from the rx queue
    def read(self):
        try:
            # FIXED: Use non-blocking get() instead of blocking with timeout
            # This eliminates the 64ms delay that was causing choppy audio
            audio = self._rx_q.get_nowait()

            # If for some reason we receive less than 320 bytes
            # of audio, add silence (padding) to the end. This prevents
            # audioop related errors that are caused by the current frame
            # not being the same size as the last
            if len(audio) != 320:
                audio += bytes(320 - len(audio))

        except Empty:
            # Return silence immediately if no audio is available
            # This prevents blocking and maintains real-time performance
            return bytes(320)

        if self._asterisk_resample:
            # If AudioSocket is bridged with a channel
            # using the ULAW audio codec, the user can specify
            # to have it converted to linear encoding upon reading.
            if self._asterisk_resample.ulaw2lin:
                audio = audioop.ulaw2lin(audio, 2)

            # If the user requested an outrate different
            # from the default, then resample it to the rate they specified
            if self._asterisk_resample.rate != 8000:
                audio, self._asterisk_resample.ratecv_state = audioop.ratecv(
                    audio,
                    2,
                    1,
                    8000,
                    self._asterisk_resample.rate,
                    self._asterisk_resample.ratecv_state,
                )

            # If the user requested the output be in stereo,
            # then convert it from mono
            if self._asterisk_resample.channels == 2:
                audio = audioop.tostereo(audio, 2, 1, 1)

        return audio

    # Puts user supplied audio into the tx queue
    def write(self, audio):
        if self._user_resample:
            # The user can also specify to have ULAW encoded source audio
            # converted to linear encoding upon being written.
            if self._user_resample.ulaw2lin:
                # Possibly skip downsampling if this was triggered, as
                # while ULAW encoded audio can be sampled at rates other
                # than 8KHz, since this is telephony related, it's unlikely.
                audio = audioop.ulaw2lin(audio, 2)

            # If the audio isn't already sampled at 8KHz,
            # then it needs to be downsampled first
            if self._user_resample.rate != 8000:
                audio, self._user_resample.ratecv_state = audioop.ratecv(
                    audio,
                    2,
                    self._user_resample.channels,
                    self._user_resample.rate,
                    8000,
                    self._user_resample.ratecv_state,
                )

            # If the audio isn't already in mono, then
            # it needs to be downmixed as well
            if self._user_resample.channels == 2:
                audio = audioop.tomono(audio, 2, 1, 1)

        self._tx_q.put(audio)

    # Tells Asterisk to hangup the call from it's end.
    # Although after the call is hungup, the socket on Asterisk's end
    # closes the connection via an abrupt RST packet, resulting in a "Connection reset by peer"
    # error on our end. Unfortunately, using try and except around self.conn.recv() is as
    # clean as I think it can be right now
    def hangup(self):
        # Three bytes of 0 indicate a hangup message
        with self._lock:
            self.conn.send(types.hangup * 3)

        sleep(0.2)
        return

    def _process(self):
        print(f"[AUDIOSOCKET INFO] Starting _process loop for {self.peer_addr}")
        first_audio_sent = False
        
        while True:
            data = None

            try:
                with self._lock:
                    data = self.conn.recv(323)

            except ConnectionResetError:
                print("[AUDIOSOCKET INFO] Connection reset by peer")
                break

            if not data:
                print("[AUDIOSOCKET INFO] No data received, connection closed")
                self.connected = False
                self.conn.close()
                return

            if self._frame_count < 5:
                print(f"[AUDIOSOCKET DEBUG] Raw data received: {len(data)} bytes, first 10 bytes: {data[:10]!r}")

            type, length, payload = self._split_data(data)

            if type == types.audio:
                if self._rx_q.full():
                    print(
                        "[AUDIOSOCKET WARNING] The inbound audio queue is full! "
                        "This most likely occurred because the read() method is "
                        "not being called, skipping frame"
                    )
                else:
                    self._rx_q.put(payload)
                    if self._frame_count <= 5:
                        print(f"[AUDIOSOCKET DEBUG] Added {len(payload)} bytes to rx queue")

                txq_size = self._tx_q.qsize()
                rxq_size = self._rx_q.qsize() if hasattr(self, '_rx_q') else -1
                print(f"[AUDIOSOCKET DEBUG] Before send: tx_q size={txq_size}, rx_q size={rxq_size}")
                if not first_audio_sent:
                    # For the first frame, send silence since client hasn't had chance to write yet
                    silence_response = types.audio + PCM_SIZE + bytes(320)
                    with self._lock:
                        self.conn.send(silence_response)
                    print(f"[AUDIOSOCKET DEBUG] Sent first frame (silence): {len(silence_response)} bytes")
                    first_audio_sent = True
                else:
                    if self._tx_q.empty():
                        silence_response = types.audio + PCM_SIZE + bytes(320)
                        with self._lock:
                            self.conn.send(silence_response)
                        print(f"[AUDIOSOCKET DEBUG] Sent silence response: {len(silence_response)} bytes (tx_q empty, size={txq_size})")
                    else:
                    audio_data = self._tx_q.get()[:320]
                        response = types.audio + len(audio_data).to_bytes(2, "big") + audio_data
                    with self._lock:
                            self.conn.send(response)
                        print(f"[AUDIOSOCKET DEBUG] Sent audio response: {len(response)} bytes (tx_q size after get={self._tx_q.qsize()})")

            elif type == types.error:
                self._decode_error(payload)

            elif type == types.uuid:
                self.uuid = payload.hex()
                print(f"[AUDIOSOCKET INFO] Received UUID: {self.uuid}")

            elif type == types.silence:
                print("[AUDIOSOCKET INFO] Received silence frame")
                if not self._rx_q.full():
                    self._rx_q.put(bytes(320))

            elif type == types.hangup:
                print("[AUDIOSOCKET INFO] Received hangup request")
                self.connected = False
                self.conn.close()
                return

            else:
                print(f"[AUDIOSOCKET WARNING] Unknown message type: {type!r}")
        
        print(f"[AUDIOSOCKET INFO] _process loop ended for {self.peer_addr}")
        self.connected = False
        self.conn.close()
