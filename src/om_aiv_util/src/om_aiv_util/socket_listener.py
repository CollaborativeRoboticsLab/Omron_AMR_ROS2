import io
import selectors2 as selectors
import socket
import traceback
import time
import threading
from collections import deque, defaultdict

RECV_BUFFER = 4096

"""A driver class to handle all input and output communication with ARCL server.

"""
class SocketListener(object):
    def __init__(self, addr, port):
        self.selector = None
        self.sock = None
        self.addr = str(addr)
        self.port = int(port)
        self.responses = defaultdict(list)
        self._recv_buffer = b""
        self.lock = threading.Lock()

        self.goal_f = False

    
    """Given the event mask from selectors, do read or write accordingly.

    param mask:
    The mask to use to decide which event can be executed.
    
    """
    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        
        self.sort_data()

    """
    Read incoming bytes from the socket and save into receive buffer.
    If there are data received, append into the receiver buffer.
    
    """
    def _read(self):
        try:
            recv_data = self.sock.recv(RECV_BUFFER)
        except io.BlockingIOError:
            pass
        else:
            self._recv_buffer += recv_data

    """
    Read incoming bytes and generate the correct responses.
    
    """
    def read(self):
        self._read()

    """
    Extracts the required string to find from the receive buffer.
    
    Returns:
        str -- The extracted string.
    """
    def sort_data(self):
        while True:
            try:
                newline_char = self._recv_buffer.index("\r\n")
            except ValueError:
                return # There is no complete line anymore in buffer, return from here.

            # Extract interested line from receive buffer.
            line = self._recv_buffer[:newline_char]
            self._recv_buffer = self._recv_buffer[newline_char+2:]
            
            try:
                colon = line.index(":")
            except ValueError:
                key = line
                value = None
                self.store(key, value)
            else:
                key = line[:colon]
                value = line[colon+1:].strip()
                self.store(key, value)
    def store(self, key, value):
            
        if key == "Goal":
            if self.goal_f:
                self.responses[key].append(value)
            else:
                self.responses[key] = [value]
                self.goal_f = True
        elif key == "End of goals":
            self.goal_f = False
        else:
            self.responses[key] = [value]
            
    """
    Retrieve the response associated with the given identifier integer.

    param identifier:
    The identifier integer associated with returned response.
    
    Returns:
        str -- The response string associated with the identifier integer.
    """
    def get_response(self, key):
        return self.responses[key]

    """
    # TODO: Add check for failed connection
    Connects the driver to the given address and port.

    param addr:
    Address to connect to.

    param port:
    Port number to connect to.

    """
    def begin(self):
        print "Attempt to listen for incoming on", self.addr, "at port", self.port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        incoming = (self.addr, self.port)
        sock.bind(incoming)
        sock.listen(1)
        (connection, address) = sock.accept()
        sock.shutdown(socket.SHUT_RDWR)
        sock.close() # Close the initial socket.
        print "Listening to new socket on", address[0], "at port", address[1]
        self.sock = connection
        self.sock.setblocking(False)
        events = selectors.EVENT_READ
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, events, data=self)

    def close(self):
        self.selector.unregister(self.sock)
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()


