import sys
import selectors
import json
import io
import struct


class Message:
    def __init__(self, selector, sock, addr, mode):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.mode = mode
        self.request = None
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._jsonheader_len = None
        self.jsonheader = None
        self.response = None

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
            if self.mode == 'debug':
                print(f"sending {repr(self._send_buffer)} to {self.addr}")
            elif self.mode == 'user':
                print((f"sending {self.request['content']} to {self.addr}"))
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError as e:
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


    def _process_binary_response(self):
        content = self.response
        print(f"got response: {repr(content)}")


    def set_request(self, content):
        self.request = dict(
            type="binary/custom-client-binary-type",
            encoding="binary",
            content=content,
        )

    def read(self):
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.response is None:
                self.process_response()

    def write(self):
        if not self._request_queued:
            self.queue_request()

        self._write()

        if self._request_queued:
            if not self._send_buffer:
                self._request_queued = False


    def close(self):
        print("closing connection to", self.addr)
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

    def queue_request(self):
        req = {
            "content_bytes": self.request["content"],
            "content_type": self.request["type"],
            "content_encoding": self.request["encoding"],
        }
        message = self._create_message(**req)
        self._send_buffer += message
        self._request_queued = True

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

    def process_response(self):
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        # binary response
        self.response = data
        if self.mode == 'debug':
            print(f'received {self.jsonheader["content-type"]} response from {self.addr}')
        self._process_binary_response()
        
        self._jsonheader_len = None
        self.jsonheader = None
        self.response = None
