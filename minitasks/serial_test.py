import os
import tty
import termios


DEFAULT_TTY = '/dev/ttyUSB0'


def open_tty(filename=DEFAULT_TTY) -> int:
    fd = os.open(filename, os.O_RDWR | os.O_NOCTTY)
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(fd)
    ispeed = ospeed = termios.B38400 # set baud
    cflag |= termios.CS8 # 8 bit characters
    cflag &= ~termios.CSTOPB # 1 stop bit
    attr = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
    tty.cfmakeraw(attr) # raw mode
    termios.tcsetattr(fd, termios.TCSAFLUSH, attr)
    return fd


class Serial:
    def __init__(self, filename=DEFAULT_TTY):
        self.filename = filename
        self.fd = open_tty(filename)
    def read(self, n):
        data = b''
        while len(data) < n:
            b = os.read(self.fd, n - len(data))
            if not b:
                break
            data += b
        return data
    def write(self, data):
        n = len(data)
        sent = 0
        while sent < n:
            sent += os.write(self.fd, data[sent:])
            print(f"Sent: {sent}")
    def close(self): os.close(self.fd)
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
