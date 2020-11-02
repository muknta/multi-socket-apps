#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
# package with Message class
import lib_server

sel = selectors.DefaultSelector()


def accept_wrapper(sock, mode):
    conn, addr = sock.accept()  # Should be ready to read
    print("accepted connection from", addr)
    conn.setblocking(False)

    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = lib_server.Message(sel, conn, addr, mode)
    sel.register(conn, events, data=message)


if len(sys.argv) != 4:
    print("usage:", sys.argv[0], "<host> <port> <mode>")
    print("<mode> equal to 'user' or 'debug'")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
mode = sys.argv[3]

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print("listening on", (host, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj, mode)
            else:
                message = key.data
                try:
                    message.process_events(mask)
                except Exception as e:
                    if mode == 'debug':
                        print("main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}")
                    elif mode == 'user':
                        print(f'error: {e}')
                    message.close()
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()
