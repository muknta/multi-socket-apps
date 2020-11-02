import sys
import selectors
import json
import io
import struct
from string import (
    ascii_uppercase,
    ascii_lowercase,
    digits,
)
from random import choice, randint
import time

MAX_CHARS_NUM = 5
MAX_SLEEP_TIME = 5

def get_rand_chars():
    chars = f'{ascii_uppercase}{ascii_lowercase}{digits}'
    return ''.join(choice(chars) for _ in range(randint(1, MAX_CHARS_NUM)))


class Message:
    def __init__(self, selector, sock, addr, mode):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.mode = mode
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.symb_increment = 0
        self.sleep_time = 0

    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed")

    def _write(self):
        if self._send_buffer:
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                print(f'error: {e}')
            else:
                self._send_buffer = self._send_buffer[sent:]

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _create_message(self, *,
        content_bytes, content_type, content_encoding
    ):
        if self.mode == 'user':
            print(f"sending {content_bytes} to {self.addr}")
            
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message


    def _create_binary_response(self):
        self.sleep_time = randint(1, MAX_SLEEP_TIME)
        time.sleep(self.sleep_time)
        print(f'sleepy for a {self.sleep_time}',
            f'second{"" if self.sleep_time==1 else "s"}')

        chars = get_rand_chars()
        response = {
            "content_bytes": str.encode(chars),
            "content_type": "binary/custom-server-binary-type",
            "content_encoding": "binary",
        }
        self.symb_increment += len(chars)
        return response

    def _create_statistics_response(self):
        response = {
            "content_bytes": b"Statistics: "
                + str.encode(f'{self.symb_increment} symbols was delivered'),
            "content_type": "binary/custom-server-binary-type",
            "content_encoding": "binary",
        }
        self.symb_increment = 0
        return response

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.request is None:
                self.process_request()

    def write(self):
        if self.request is b"s":
            response = self._create_statistics_response()
            self.process_responce(response)

            self._jsonheader_len = None
            self.jsonheader = None
            self.request = None
        else:
            response = self._create_binary_response()
            self.process_responce(response)
        self._write()

    def close(self):
        print(f"closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print("error: selector.unregister() exception for",
                f"{self.addr}: {repr(e)}")
        try:
            self.sock.close()
        except OSError as e:
            print("error: socket.close() exception for",
                f"{self.addr}: {repr(e)}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def process_protoheader(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen])[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_jsonheader(self):
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f'Missing required header "{reqhdr}".')

    def process_request(self):
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        self.request = data
        if self.mode == 'debug':
            print(f'received {self.jsonheader["content-type"]}',
                f'request from {self.addr}')
        elif self.mode == 'user':
            print(f'received request from {self.addr}')

    def process_responce(self, response):
        message = self._create_message(**response)
        self._send_buffer += message
        if self.mode == 'debug':
            print(f"sending {repr(self._send_buffer)} to {self.addr}")
