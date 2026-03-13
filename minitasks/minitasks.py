import os
import sys
import tty
import time
import termios
import logging
import selectors

from functools import cached_property
from typing import Dict, List, Set, NamedTuple

from miniserial import Serial

from tasklang import BUILTINS, Compilation, compile


DEFAULT_TTY = '/dev/ttyUSB0'
DEFAULT_BAUD = 38400

def encode_uint16(i) -> bytes:
    return i.to_bytes(2, 'little')
def decode_uint16(data: bytes) -> int:
    return int.from_bytes(data, 'little')


# Must match enum message_type in minitasks.h
MESSAGE_PING                   = b'\x00'
MESSAGE_GET_OFFSETS            = b'\x01'
MESSAGE_GET_BUILTIN_LOCATIONS  = b'\x02'
MESSAGE_LOAD_TASK              = b'\x03'
MESSAGE_START_TASK             = b'\x04'
MESSAGE_STOP_TASK              = b'\x05'
MESSAGE_INSPECT_TASK           = b'\x06'
MESSAGE_KERNEL_LOG             = b'\x07'
MESSAGE_TASK_LOG               = b'\x08'
MESSAGE_TASK_STOPPED           = b'\x09'


class Offsets(NamedTuple):
    tasks_table_location: int
    max_tasks: int
    task_size: int
    heap_offset: int # actually offset of CODE + HEAP sections

    @property
    def fields_size(self) -> int:
        return self.heap_offset

    @property
    def heap_size(self) -> int:
        return self.task_size - self.heap_offset


class TaskMemory(NamedTuple):
    fields: bytes
    heap: bytes # CODE + HEAP + FREE + STACK


class Client:
    def __init__(self, filename=DEFAULT_TTY, baud=DEFAULT_BAUD):
        self.serial = Serial(filename, baud)
        self.read = self.serial.read
        self.write = self.serial.write
        self.fd = self.serial.fd

    def close(self): self.serial.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def read_uint16(self) -> int:
        return decode_uint16(self.read(2))

    def send_bytes(self, data: bytes):
        self.write(encode_uint16(len(data)))
        self.write(data)

    def send_task_id(self, task_id: int):
        if task_id < 0 or task_id >= self.offsets.task_size:
            raise Exception(f"Invalid task ID: {task_id}")
        self.write(task_id.to_bytes())

    def ping(self, c=b'!', check=True):
        self.write(b'\xff' + MESSAGE_PING + c)
        pong = self.read(1)
        if check and c != pong:
            raise Exception(f"Ping: sent {c!r}, got {pong!r}")

    def get_offsets(self) -> Offsets:
        self.write(b'\xff' + MESSAGE_GET_OFFSETS)
        data = self.read(8)
        return Offsets(
            decode_uint16(data[0:2]),
            decode_uint16(data[2:4]),
            decode_uint16(data[4:6]),
            decode_uint16(data[6:8]),
        )

    offsets = cached_property(get_offsets)

    def get_builtin_locations(self) -> List[int]:
        self.write(b'\xff' + MESSAGE_GET_BUILTIN_LOCATIONS)
        n = self.read_uint16()
        if n != len(BUILTINS):
            raise Exception(f"Client knows {len(BUILTINS)} builtins, OS knows {n}")
        return [self.read_uint16() for name in BUILTINS]

    builtin_locations = cached_property(get_builtin_locations)

    @cached_property
    def builtins_by_name(self) -> Dict[str, int]:
        return dict(zip(BUILTINS, self.builtin_locations))

    def compile_task(self, task_id: int, comp) -> bytes:
        """Produces the CODE + HEAP sections for a task, suitable for passing
        to self.load_task"""
        if not isinstance(comp, Compilation):
            comp = compile(comp)
        offsets = self.offsets # kick off GET_OFFSETS if needed
        builtin_locations = self.builtin_locations # kick off GET_BUILTIN_LOCATIONS if needed
        task_location = offsets.tasks_table_location + task_id * offsets.task_size
        code_location = task_location + offsets.heap_offset
        heap_location = code_location + len(comp.instructions)

        buf = bytearray()
        instructions = list(comp.instructions)
        for i in comp.code_locations:
            instructions[i] += code_location
        for i in comp.heap_locations:
            instructions[i] += heap_location
        for i in comp.builtin_locations:
            instructions[i] = builtin_locations[instructions[i]]
        for instruction in instructions:
            buf.extend(encode_uint16(instruction)) # CODE section
        buf.extend(comp.heap) # HEAP section
        return bytes(buf)

    def load_task(self, task_id: int, payload):
        offsets = self.offsets # kick off GET_OFFSETS if needed
        if isinstance(payload, str):
            payload = compile(payload)
        if isinstance(payload, Compilation):
            payload = self.compile_task(task_id, payload)
        if not isinstance(payload, bytes):
            raise Exception(f"Expected bytes, got {type(payload)}")
        if len(payload) > offsets.heap_size:
            raise Exception(f"Payload size {len(payload)} exceeds heap size {offsets.heap_size}")
        self.write(b'\xff\x03')
        self.send_task_id(task_id)
        self.send_bytes(payload)

    def start_task(self, task_id: int):
        self.write(b'\xff\x04')
        self.send_task_id(task_id)

    def run_task(self, task_id: int, payload):
        self.load_task(task_id, payload)
        self.start_task(task_id)

    def stop_task(self, task_id: int):
        self.write(b'\xff\x05')
        self.send_task_id(task_id)

    def inspect_task(self, task_id: int) -> TaskMemory:
        offsets = self.offsets # kick off GET_OFFSETS if needed
        self.write(b'\xff\x06')
        self.send_task_id(task_id)
        fields = self.read(offsets.fields_size)
        heap = self.read(offsets.heap_size)
        return TaskMemory(
            fields=fields,
            heap=heap,
        )


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
                        client.ping(c.encode('ascii'))
                    else:
                        print(f"Unrecognized command: {cmd!r}")
    finally:
        exit_cbreak()
    print("Bye!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
