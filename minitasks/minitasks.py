import os
import sys
import tty
import time
import termios
import logging
import selectors

from miniserial import Serial

import tasklang


DEFAULT_TTY = '/dev/ttyUSB0'
DEFAULT_BAUD = 38400


class Client:
    def __init__(self, filename=DEFAULT_TTY, baud=DEFAULT_BAUD):
        self.serial = Serial(filename, baud)
        self.read = self.serial.read
        self.write = self.serial.write
        self.fd = self.serial.fd

    def close(self): self.serial.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def send_ping(self, c=b'!', check=True):
        self.write(b'\xff\x00' + c)
        c2 = self.read(1)
        if check and c != c2:
            raise Exception(f"Ping: sent {c!r}, got {c2!r}")


def main():

    # Get client
    filename = DEFAULT_TTY
    baud = DEFAULT_BAUD
    client = Client(filename, baud)

    stdin_fd = sys.stdin.fileno()
    stdout_fd = sys.stdout.fileno()

    def handle_client_read():
        data = client.read()
        buf = bytearray()
        for c in data:
            if (c < 0x20 and c not in b'\r\n') or c > 126:
                buf.extend(b'[' + hex(c).encode() + b']')
            else:
                buf.append(c)
        os.write(stdout_fd, buf)

    def handle_stdin_read():
        c = os.read(stdin_fd, 1)
        client.write(c)

    # Event selector for reads on stdin and client
    selector = selectors.DefaultSelector()
    selector.register(client.fd, selectors.EVENT_READ, handle_client_read)
    selector.register(stdin_fd, selectors.EVENT_READ, handle_stdin_read)

    # Helpers for entering/exiting cbreak mode on stdin
    stdin_attrs = None
    def enter_cbreak():
        nonlocal stdin_attrs
        if stdin_attrs:
            return
        stdin_attrs = tty.setcbreak(stdin_fd, termios.TCSAFLUSH)
        termios.tcflush(stdin_fd, termios.TCIOFLUSH)
    def exit_cbreak():
        nonlocal stdin_attrs
        if not stdin_attrs:
            return
        termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, stdin_attrs)
        termios.tcflush(stdin_fd, termios.TCIOFLUSH)
        stdin_attrs = None

    enter_cbreak()
    try:
        while True:
            try:
                for key, mask in selector.select():
                    # Handle read & write events
                    cb = key.data
                    cb()
            except KeyboardInterrupt:

                # Get a command from stdin
                exit_cbreak()
                try:
                    cmd = input("Command: ")
                except KeyboardInterrupt:
                    break
                finally:
                    enter_cbreak()

                # Handle command
                cmd = [s.strip() for s in cmd.split()]
                if cmd:
                    args = cmd[1:]
                    cmd = cmd[0]
                    if cmd == 'hex':
                        client.write(b''.join(
                            bytes.fromhex(arg) for arg in args))
                    elif cmd == 'ping':
                        c = args.pop(0) if args else '!'
                        client.send_ping(c.encode('ascii'))
                    else:
                        print(f"Unrecognized command: {cmd!r}")
    finally:
        exit_cbreak()
    print("Bye!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
