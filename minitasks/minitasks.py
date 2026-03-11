import time
import logging
import selectors

import serial as pyserial

import tasklang


DEFAULT_TTY = '/dev/ttyUSB0'
BAUD = 38400


class Client:
    def __init__(self, filename=DEFAULT_TTY):
        self.serial = pyserial.Serial(filename, BAUD)
        self.read = self.serial.read
        self.write = self.serial.write
        self.drain = self.serial.read_all

    def close(self): self.serial.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def send_ping(self, c=b'!'):
        self.write(b'\xff\x00' + c)
        return self.read(1)


def main():
    filename = DEFAULT_TTY
    serial = pyserial.Serial(filename, BAUD)
    time.sleep(1)
    print("OK")
    serial.write(b'ah')
    print(serial.read(22))
    return
    selector = selectors.DefaultSelector()
    selector.register(EVENT_READ|EVENT_WRITE)
    while True:
        try:
            pass
        except KeyboardInterrupt:
            cmd = input("Command: ")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
