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

def get_rand_chars():
    chars = f'{ascii_uppercase}{ascii_lowercase}{digits}'
    return ''.join(choice(chars) for _ in range(randint(1, MAX_CHARS_NUM)))


class Message:
    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.symb_increment = 0

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {repr(mode)}.")
        self.selector.modify(self.sock, events, data=self)

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
                raise RuntimeError("Peer closed.")

    def _write(self):
        if self._send_buffer:
            print("sending", repr(self._send_buffer), "to", self.addr)
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                # if sent and not self._send_buffer:
                #     self.close()

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _create_message(
        self, *, content_bytes, content_type, content_encoding
    ):
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

    # def _create_response_json_content(self):
    #     action = self.request.get("action")
    #     if action == "search":
    #         query = self.request.get("value")
    #         answer = request_search.get(query) or f'No match for "{query}".'
    #         content = {"result": answer}
    #     else:
    #         content = {"result": f'Error: invalid action "{action}".'}
    #     content_encoding = "utf-8"
    #     response = {
    #         "content_bytes": self._json_encode(content, content_encoding),
    #         "content_type": "text/json",
    #         "content_encoding": content_encoding,
    #     }
    #     return response

    # def _create_response_binary_content(self):
    #     response = {
    #         "content_bytes": b"First 10 bytes of request: "
    #         + self.request[:10],
    #         "content_type": "binary/custom-server-binary-type",
    #         "content_encoding": "binary",
    #     }
    #     return response

    def _create_binary_response(self):
        time.sleep(2)
        chars = get_rand_chars()
        response = {
            "content_bytes": str.encode(chars),
            "content_type": "binary/custom-server-binary-type",
            "content_encoding": "binary",
        }
        self.symb_increment += len(chars)
        return response

    def _create_statistics_response(self):
        # time.sleep(2)
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
        if self.request in (b"s", "s"):
            response = self._create_statistics_response()
            print(1111111111111111111)
            message = self._create_message(**response)
            self._send_buffer += message
            self.request = None
        else:
            print(22222222222222222222222)
            response = self._create_binary_response()
            message = self._create_message(**response)
            self._send_buffer += message
        self._write()

    def close(self):
        print(f"closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(f"error: selector.unregister() \
                exception for {self.addr}: {repr(e)}")

        try:
            self.sock.close()
        except OSError as e:
            print(f"error: socket.close() exception for \
                {self.addr}: {repr(e)}")
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
        print(f'received {self.jsonheader["content-type"]} \
                request from {self.addr}')
        self._set_selector_events_mask("rw")

    def process_responce(self, response):
        message = self._create_message(**response)
        self._send_buffer += message
