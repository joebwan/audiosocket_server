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
import socket


# AudioSocket message types according to official specification
@dataclass(frozen=True)
class TypesStruct:
    hangup: bytes = b"\x00"   # Terminate the connection
    uuid: bytes = b"\x01"     # Payload contains UUID (16-byte binary)
    dtmf: bytes = b"\x03"     # Payload is 1 byte (ascii) DTMF digit
    audio: bytes = b"\x10"    # Payload is signed linear, 16-bit, 8kHz, mono PCM (little-endian)
    error: bytes = b"\xff"    # An error has occurred; payload is optional error code


types = TypesStruct()


# AudioSocket error codes according to official specification
@dataclass(frozen=True)
class ErrorsStruct:
    none: bytes = b"\x00"
    hangup: bytes = b"\x01"
    frame: bytes = b"\x02"
    memory: bytes = b"\x04"


errors = ErrorsStruct()


class ConnectionFixed:
    """AudioSocket connection with proper variable-length frame parsing"""
    
    def __init__(self, conn, peer_addr, user_resample, asterisk_resample):
        self.conn = conn
        self.peer_addr = peer_addr
        self.uuid = None
        self.connected = True
        self._user_resample = user_resample
        self._asterisk_resample = asterisk_resample

        # Underlying Queue objects for passing incoming/outgoing audio between threads
        self._rx_q = Queue(500)
        self._tx_q = Queue(500)
        self._lock = Lock()
        
        # Frame parsing state
        self._frame_count = 0
        self._total_bytes_received = 0
        self._total_frames_parsed = 0
        
        # Buffer for incomplete frames
        self._read_buffer = b""
        
        # Statistics
        self._start_time = None
        self._last_frame_time = None

    def _read_exact(self, num_bytes):
        """Read exactly num_bytes from the socket"""
        data = b""
        while len(data) < num_bytes:
            chunk = self.conn.recv(num_bytes - len(data))
            if not chunk:
                raise ConnectionError("Connection closed by peer")
            data += chunk
        return data

    def _read_frame_header(self):
        """Read and parse a frame header (3 bytes: type + length)"""
        try:
            header_data = self._read_exact(3)
            if len(header_data) != 3:
                raise ValueError(f"Incomplete header: {len(header_data)} bytes")
            
            frame_type = header_data[0:1]
            frame_length = int.from_bytes(header_data[1:3], "big")
            
            return frame_type, frame_length
            
        except Exception as e:
            print(f"[AUDIOSOCKET ERROR] Failed to read frame header: {e}")
            raise

    def _read_frame_payload(self, length):
        """Read exactly length bytes for the frame payload"""
        try:
            payload = self._read_exact(length)
            if len(payload) != length:
                raise ValueError(f"Incomplete payload: expected {length}, got {len(payload)}")
            return payload
            
        except Exception as e:
            print(f"[AUDIOSOCKET ERROR] Failed to read frame payload: {e}")
            raise

    def _parse_frame(self):
        """Parse a complete AudioSocket frame with proper variable-length handling"""
        try:
            # Read frame header
            frame_type, frame_length = self._read_frame_header()
            
            # Read frame payload
            payload = self._read_frame_payload(frame_length)
            
            # Update statistics
            self._frame_count += 1
            self._total_bytes_received += 3 + frame_length  # header + payload
            self._total_frames_parsed += 1
            
            # Log first few frames for debugging
            if self._frame_count <= 5:
                print(f"[AUDIOSOCKET DEBUG] Frame {self._frame_count}: Type=0x{frame_type.hex()}, Length={frame_length}, Payload size={len(payload)}")
                if self._frame_count == 1:
                    print(f"[AUDIOSOCKET DEBUG] First frame: type=0x{frame_type.hex()}, length={frame_length}, payload={payload[:16].hex()}")
            
            return frame_type, payload
            
        except Exception as e:
            print(f"[AUDIOSOCKET ERROR] Frame parsing failed: {e}")
            raise

    def _decode_error(self, payload):
        """Decode AudioSocket error messages"""
        if payload == errors.none:
            print("[ASTERISK ERROR] No error code present")
        elif payload == errors.hangup:
            print("[ASTERISK ERROR] The called party hungup")
        elif payload == errors.frame:
            print("[ASTERISK ERROR] Failed to forward frame")
        elif payload == errors.memory:
            print("[ASTERISK ERROR] Memory allocation error")
        else:
            print(f"[ASTERISK ERROR] Unknown error code: {payload.hex()}")

    def _send_frame(self, frame_type, payload):
        """Send a properly formatted AudioSocket frame"""
        try:
            length = len(payload)
            frame = frame_type + length.to_bytes(2, "big") + payload
            
            with self._lock:
                self.conn.send(frame)
            
            return len(frame)
            
        except Exception as e:
            print(f"[AUDIOSOCKET ERROR] Failed to send frame: {e}")
            raise

    def read(self):
        """Get audio from the receive queue"""
        try:
            # Non-blocking get to maintain real-time performance
            audio = self._rx_q.get_nowait()
            
            # Ensure consistent frame size for audio processing
            if len(audio) != 320:
                audio += bytes(320 - len(audio))
                
        except Empty:
            # Return silence if no audio available
            return bytes(320)

        # Apply audio resampling if configured
        if self._asterisk_resample:
            if self._asterisk_resample.ulaw2lin:
                audio = audioop.ulaw2lin(audio, 2)

            if self._asterisk_resample.rate != 8000:
                audio, self._asterisk_resample.ratecv_state = audioop.ratecv(
                    audio,
                    2,
                    1,
                    8000,
                    self._asterisk_resample.rate,
                    self._asterisk_resample.ratecv_state,
                )

            if self._asterisk_resample.channels == 2:
                audio = audioop.tostereo(audio, 2, 1, 1)

        return audio

    def write(self, audio):
        """Put audio into the transmit queue"""
        if self._user_resample:
            if self._user_resample.ulaw2lin:
                audio = audioop.ulaw2lin(audio, 2)

            if self._user_resample.rate != 8000:
                audio, self._user_resample.ratecv_state = audioop.ratecv(
                    audio,
                    2,
                    self._user_resample.channels,
                    self._user_resample.rate,
                    8000,
                    self._user_resample.ratecv_state,
                )

            if self._user_resample.channels == 2:
                audio = audioop.tomono(audio, 2, 1, 1)

        self._tx_q.put(audio)

    def hangup(self):
        """Send hangup message according to AudioSocket spec"""
        try:
            # Send hangup frame: 0x00 + 0x0000 (type + zero length)
            hangup_frame = types.hangup + b"\x00\x00"
            
            with self._lock:
                self.conn.send(hangup_frame)
            
            print("[AUDIOSOCKET INFO] Hangup message sent")
            sleep(0.2)
            
        except Exception as e:
            print(f"[AUDIOSOCKET ERROR] Failed to send hangup: {e}")

    def _process(self):
        """Main processing loop with proper frame parsing"""
        print(f"[AUDIOSOCKET INFO] Starting _process loop for {self.peer_addr}")
        self._start_time = time.time()
        self._last_frame_time = self._start_time
        
        first_audio_sent = False
        
        try:
            while self.connected:
                # Parse frame with proper variable-length handling
                frame_type, payload = self._parse_frame()
                
                current_time = time.time()
                
                # Log frame timing every 100 frames
                if self._frame_count % 100 == 0:
                    elapsed = current_time - self._start_time
                    fps = self._frame_count / elapsed if elapsed > 0 else 0
                    print(f"[AUDIOSOCKET INFO] Frame {self._frame_count}: FPS={fps:.1f}, Total bytes={self._total_bytes_received}")
                
                # Process frame based on type
                if frame_type == types.audio:
                    # Audio frame - add to receive queue
                    if self._rx_q.full():
                        print("[AUDIOSOCKET WARNING] Receive queue full, dropping frame")
                    else:
                        self._rx_q.put(payload)
                    
                    # Send response (echo or silence)
                    if not first_audio_sent:
                        # Send silence for first frame
                        self._send_frame(types.audio, bytes(320))
                        print("[AUDIOSOCKET DEBUG] Sent first frame (silence)")
                        first_audio_sent = True
                    else:
                        # Send audio from transmit queue or silence
                        if self._tx_q.empty():
                            self._send_frame(types.audio, bytes(320))
                        else:
                            audio_data = self._tx_q.get()
                            self._send_frame(types.audio, audio_data)
                
                elif frame_type == types.uuid:
                    # UUID frame - store UUID
                    self.uuid = payload.hex()
                    print(f"[AUDIOSOCKET INFO] Received UUID: {self.uuid}")
                
                elif frame_type == types.dtmf:
                    # DTMF frame - log DTMF digit
                    dtmf_digit = payload.decode('ascii', errors='ignore') if payload else '?'
                    print(f"[AUDIOSOCKET INFO] Received DTMF: {dtmf_digit}")
                
                elif frame_type == types.error:
                    # Error frame - decode and log error
                    self._decode_error(payload)
                
                elif frame_type == types.hangup:
                    # Hangup frame - close connection
                    print("[AUDIOSOCKET INFO] Received hangup request")
                    self.connected = False
                    break
                
                else:
                    # Unknown frame type
                    print(f"[AUDIOSOCKET WARNING] Unknown frame type: 0x{frame_type.hex()}")
                
                self._last_frame_time = current_time
                
        except ConnectionError as e:
            print(f"[AUDIOSOCKET INFO] Connection closed: {e}")
        except Exception as e:
            print(f"[AUDIOSOCKET ERROR] Processing error: {e}")
        finally:
            self.connected = False
            self.conn.close()
            
            # Final statistics
            if self._start_time:
                total_time = time.time() - self._start_time
                avg_fps = self._frame_count / total_time if total_time > 0 else 0
                print(f"[AUDIOSOCKET INFO] Connection ended:")
                print(f"  Total frames: {self._frame_count}")
                print(f"  Total bytes: {self._total_bytes_received}")
                print(f"  Total time: {total_time:.3f}s")
                print(f"  Average FPS: {avg_fps:.1f}")
                print(f"  Expected FPS: 50.0 (20ms intervals)")
                
                if avg_fps > 0:
                    speed_ratio = avg_fps / 50.0
                    if abs(speed_ratio - 1.0) < 0.1:
                        print(f"  ✅ Frame rate is correct ({speed_ratio:.1f}x)")
                    else:
                        print(f"  ⚠️  Frame rate is {speed_ratio:.1f}x expected")
            
            print(f"[AUDIOSOCKET INFO] _process loop ended for {self.peer_addr}")


# Import time for statistics
import time 