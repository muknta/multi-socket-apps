# multi-socket-apps on Python

This project consists of server application and client application. Server supports work with multiple clients.

## Functionality
After connection of client to server
- server generates random amount of chars and sends it to client. Each generation is separated by random time interval.
- client can press 'q' to quit program or 's' to get statistics. "Statistics" - number of delivered symbols from server to client. Each press of 's' resets a symbol counter.


## Structure
* app_server.py - main server script
* lib_server.py - package with Message class for server
* app_client.py - main client script
* lib_client.py - package with Message class for client

## Using
```bash
~/$ git clone https://github.com/heknt/multi-socket-apps.git
~/$ cd multi-socket-apps
```
Setting of a virtual environment:
```bash
~/multi-socket-apps$ virtualenv sock
~/multi-socket-apps$ source sock/bin/activate
(sock) ~/multi-socket-apps$ pip install -r requirements.txt
```
Running of a server app:
```bash
(sock) ~/multi-socket-apps$ ./app_server.py
usage: ./app_server.py <host> <port> <mode>
<mode> must equal to 'user' or 'debug'
(sock) ~/multi-socket-apps$ ./app_server.py localhost 65432 user
```
The *mode* option is for printing. *Debug mode* is more extensive than *user mode*.

The same with a client app in a different terminal window:
```bash
(sock) ~/multi-socket-apps$ ./app_client.py
usage: ./app_client.py <host> <port> <mode>
<mode> must equal to 'user' or 'debug'
(sock) ~/multi-socket-apps$ ./app_client.py localhost 65432 user
```
After running server will generate symbols:
```bash
listening on ('localhost', 65432)
accepted connection from ('127.0.0.1', 60174)
sleepy for a 3 seconds
sending b'td3kk' to ('127.0.0.1', 60174)
sleepy for a 2 seconds
sending b'yA' to ('127.0.0.1', 60174)
...
```
Responses in client app:
```bash
starting connection to ('localhost', 65432)
Press 's' for statistics or 'q' to quit.
sleepy for a 3 seconds
got response: b'td3kk'
sleepy for a 2 seconds
got response: b'yA'
...
```

Example of statistics response from a server by pressing 's':

*server window*
```bash
...
received request from ('127.0.0.1', 60220)
sending b'Statistics: 8 symbols was delivered' to ('127.0.0.1', 60220)
...
```
*client window*
```bash
...
got response: b'Statistics: 8 symbols was delivered'
...
```
By pressing 'q' in client window:

*client window*
```bash
...
closing connection to ('localhost', 65432)
```
*server window*
```bash
...
error: Peer closed
closing connection to ('127.0.0.1', 60220)
```

