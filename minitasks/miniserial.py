import os
import re
import tty
import fcntl
import struct
import termios


DEFAULT_FILENAME = os.environ.get('USBTTY', '/dev/ttyUSB0')
DEFAULT_BAUD = 38400

BAUDS = {int(k[1:]): getattr(termios, k)
    for k in dir(termios) if k[0] == 'B' and k[1:].isdigit()}

# For passing NULL pointers to ioctl
UINT_ZERO = struct.pack('I', 0)


def open_serial(filename=DEFAULT_FILENAME, baud=DEFAULT_BAUD) -> int:
    fd = os.open(filename, os.O_RDWR | os.O_NOCTTY)
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(fd)
    ispeed = ospeed = BAUDS[baud]
    cflag |= termios.CS8 # 8 bit characters
    cflag &= ~termios.CSTOPB # 1 stop bit
    attr = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
    tty.cfmakeraw(attr) # raw mode
    termios.tcsetattr(fd, termios.TCSAFLUSH, attr)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


class Serial:

    def __init__(self, filename=DEFAULT_FILENAME, baud=DEFAULT_BAUD):
        self.filename = filename
        self.fd = open_serial(filename)

    @property
    def n_available(self) -> int:
        """Returns the number of bytes available in the read queue"""
        data = fcntl.ioctl(self.fd, termios.FIONREAD, UINT_ZERO)
        return struct.unpack('I', data)[0]

    def read(self, n=None):
        if n is None:
            n = self.n_available
        buf = bytearray()
        while len(buf) < n:
            data = os.read(self.fd, n - len(buf))
            if not data:
                break
            buf.extend(data)
        return bytes(buf)

    def write(self, data):
        n = len(data)
        sent = 0
        while sent < n:
            sent += os.write(self.fd, data[sent:])

    def flush(self):
        termios.tcdrain(self.fd)

    def close(self): os.close(self.fd)
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
