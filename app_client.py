#!/usr/bin/env python3

import sys
import socket
import selectors
from threading import Thread
import traceback
# package with Message class
import lib_client

import platform
sys_name = platform.system()

if sys_name == 'Windows':
    import msvcrt as inp_lib
else:
    import getch as inp_lib

sel = selectors.DefaultSelector()

quit_key_pressed = False
stat_key_pressed = False

def press_key():
    print("Press 's' for statistics or 'q' to quit.")
    return inp_lib.getche()

def detect_key_press():
    global quit_key_pressed, stat_key_pressed

    print('first, im hereeee')
    char = press_key()
    while char is not 'q':
        print('SEC, im hereeee')
        char = press_key()
        if char is 's':
            print('THI, stat_key_pressed = True')
            stat_key_pressed = True
    print('THI, quit_key_pressedquit_key_pressedquit_key_pressed')
    quit_key_pressed = True


def get_traceback(message):
    print(f"main: error: exception for \
        {message.addr}:\n{traceback.format_exc()}")


def start_connection(host, port):
    addr = (host, port)
    print("starting connection to", addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = lib_client.Message(sel, sock, addr)
    sel.register(sock, events, data=message)


if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
# mode = sys.argv[3] # user or debug
start_connection(host, port)

try:
    getch_thread = Thread(target=detect_key_press)
    getch_thread.start()
    message = None

    while not quit_key_pressed:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            try:
                if mask:
                    if stat_key_pressed:
                        message.set_request(content=b"s")
                        print('UNDER stat_key_pressed stat_key_pressed')
                        message.write()
                        stat_key_pressed = False

                    print('FREEeeeeeeeeeeeeee')
                    message.read()
            except Exception:
                get_traceback(message)
                message.close()
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    try:
        message.close()
    except Exception:
        get_traceback(message)
    sel.close()
