import os
import sys
import tty
import time
import termios
import logging
import selectors

from functools import cached_property
from typing import Dict, List, Set, Tuple, NamedTuple

from miniserial import Serial

from tasklang import BUILTINS, Compilation, compile


def encode_uint16(i) -> bytes:
    return i.to_bytes(2, 'little')
def decode_uint16(data: bytes) -> int:
    return int.from_bytes(data, 'little')

def parse_ints(data: bytes) -> List[int]:
    values = []
    for i in range(0, len(data), 2):
        values.append(decode_uint16(data[i:i+2]))
    return values


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
MESSAGE_GET_MEMORY             = b'\x0a'
MESSAGE_SET_MEMORY             = b'\x0b'


class Offsets(NamedTuple):
    ram_start: int # RAMSTART from <avr/iom328p.h>
    ram_end: int # 1 + RAMEND from <avr/iom328p.h>
    tasks_table_location: int # TASKS in minitasks.h
    max_tasks: int # MAX_TASKS in minitasks.h
    task_size: int # TASK_SIZE in minitasks.h, i.e. sizeof(task_t)
    task_mem_offset: int # offset of task_t's mem field

    @property
    def ram_size(self) -> int:
        return self.ram_end - self.ram_start

    @property
    def fields_size(self) -> int:
        # size of FIELDS
        return self.task_mem_offset

    @property
    def mem_size(self) -> int:
        # size of CODE + HEAP + FREE + STACK
        return self.task_size - self.task_mem_offset

    def get_task_loc(self, task_id: int) -> int:
        return self.tasks_table_location + self.task_size * task_id


class Memory(NamedTuple):
    loc: int
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    def __add__(self, other: 'Memory') -> 'Memory':
        if other.loc != self.loc + self.size:
            raise Exception(f"Not contiguous: {other.loc} != {self.loc + self.size}")
        return Memory(
            loc=self.loc,
            data=self.data + other.data,
        )

    def part(self, i: int, size: int) -> 'Memory':
        return Memory(
            loc=self.loc + i,
            data=self.data[i:i + size],
        )

    def print(self, style='x', w=32):
        i = 0
        loc = self.loc
        size = self.size
        while i < size:
            line = self.data[i:i+w]
            if style == 'x':
                sline = line.hex(' ')
            elif style == 'i':
                sline = ' '.join(map(str, parse_ints(line)))
            elif style == 'c':
                sline = ''.join(c if c.isprintable() else '�'
                    for c in line.decode('ascii', 'replace'))
            elif style == 'r':
                sline = repr(line)
            else:
                raise Exception(f"Got bad style {style!r}, expected one of 'x', 'i', 'c', 'r'")
            print(f'0x{hex(loc + i)[2:].rjust(4, "0")}: {sline}')
            i += w


class TaskMemory(NamedTuple):
    fields: Memory
    code: Memory
    heap: Memory
    rest: Memory # FREE + STACK

    @property
    def mem(self) -> Memory:
        return self.code + self.heap + self.rest

    def print(self, *args, **kwargs):
        print(f"=== Fields:")
        self.fields.print(*args, **kwargs)
        print(f"=== Code:")
        self.code.print(*args, **kwargs)
        print(f"=== Heap:")
        self.heap.print(*args, **kwargs)
        print(f"=== Rest:")
        self.rest.print(*args, **kwargs)


class Client:
    def __init__(self, serial: Serial = None):
        self.serial = serial or Serial()
        self.read = self.serial.read
        self.write = self.serial.write
        self.fd = self.serial.fd

    def close(self): self.serial.close()
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    def read_uint16(self) -> int:
        return decode_uint16(self.read(2))

    def write_uint16(self, i: int):
        self.write(encode_uint16(i))

    def send_bytes(self, data: bytes):
        self.write_uint16(len(data))
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
        data = self.read(12)
        return Offsets(
            decode_uint16(data[0:2]),
            decode_uint16(data[2:4]),
            decode_uint16(data[4:6]),
            decode_uint16(data[6:8]),
            decode_uint16(data[8:10]),
            decode_uint16(data[10:12]),
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
    def builtin_locations_by_name(self) -> Dict[str, int]:
        return dict(zip(BUILTINS, self.builtin_locations))

    @cached_property
    def builtin_names_by_location(self) -> Dict[int, str]:
        return dict(zip(self.builtin_locations, BUILTINS))

    def compile_task(self, task_id: int, comp) -> Tuple[bytes, bytes]:
        """Produces the CODE + HEAP sections for a task, suitable for passing
        to self.load_task"""
        if not isinstance(comp, Compilation):
            comp = compile(comp)

        offsets = self.offsets # kick off GET_OFFSETS if needed
        builtin_locations = self.builtin_locations # kick off GET_BUILTIN_LOCATIONS if needed
        task_location = offsets.tasks_table_location + task_id * offsets.task_size
        code_location = task_location + offsets.task_mem_offset
        heap_location = code_location + len(comp.instructions)

        # Generate CODE
        buf = bytearray()
        instructions = list(comp.instructions)
        for i in comp.code_locations:
            instructions[i] += code_location
        for i in comp.heap_locations:
            instructions[i] += heap_location
        for i in comp.builtin_locations:
            instructions[i] = builtin_locations[instructions[i]]
        for instruction in instructions:
            buf.extend(encode_uint16(instruction))
        code = bytes(buf)

        return code, comp.heap # CODE + HEAP

    def load_task(self, task_id: int, comp):
        offsets = self.offsets # kick off GET_OFFSETS if needed
        if isinstance(comp, str):
            comp = compile(comp)
        code, heap = self.compile_task(task_id, comp)
        size = len(code) + len(heap)
        if size > offsets.mem_size:
            raise Exception(f"Task payload too big: {size} > {offsets.mem_size}")
        self.write(b'\xff' + MESSAGE_LOAD_TASK)
        self.send_task_id(task_id)
        self.write_uint16(len(code))
        self.write_uint16(len(heap))
        self.write(code)
        self.write(heap)

    def start_task(self, task_id: int):
        self.write(b'\xff' + MESSAGE_START_TASK)
        self.send_task_id(task_id)

    def run_task(self, task_id: int, payload):
        self.load_task(task_id, payload)
        self.start_task(task_id)

    def stop_task(self, task_id: int):
        self.write(b'\xff' + MESSAGE_STOP_TASK)
        self.send_task_id(task_id)

    def inspect_task(self, task_id: int) -> TaskMemory:
        offsets = self.offsets # kick off GET_OFFSETS if needed
        self.write(b'\xff' + MESSAGE_INSPECT_TASK)
        self.send_task_id(task_id)

        # Read sizes
        code_size = self.read_uint16()
        heap_size = self.read_uint16()
        rest_size = offsets.mem_size - code_size - heap_size
        assert offsets.fields_size + code_size + heap_size + rest_size == offsets.task_size

        # Read data
        fields = self.read(offsets.fields_size)
        code = self.read(code_size)
        heap = self.read(heap_size)
        rest = self.read(rest_size)

        # Return TaskMemory
        task_loc = offsets.get_task_loc(task_id)
        code_loc = task_loc + offsets.fields_size
        heap_loc = code_loc + code_size
        rest_loc = heap_loc + heap_size
        return TaskMemory(
            fields=Memory(task_loc, fields),
            code=Memory(code_loc, code),
            heap=Memory(heap_loc, heap),
            rest=Memory(rest_loc, rest),
        )

    def dump_ram(self) -> Memory:
        return self.get_memory(self.offsets.ram_start, self.offsets.ram_size)

    def get_memory(self, loc: int, size: int = None, type='b') -> Memory:
        if type == 'b':
            if size is None:
                size = 1
        elif type == 'i':
            if size not in (None, 1):
                raise Exception("Bad size, should be 1 or unspecified")
            size = 2
        elif type == 'ii':
            if size is None:
                size = 2
            else:
                size *= 2
        else:
            raise Exception(f"Expected one of 'b', 'i', 'ii', got: {type!r}")
        self.write(b'\xff' + MESSAGE_GET_MEMORY)
        self.write_uint16(loc)
        self.write_uint16(size)
        data = self.read(size)
        if type == 'i':
            return decode_uint16(data)
        elif type == 'ii':
            return parse_ints(data)
        else:
            return Memory(loc, data)

    def set_memory(self, loc: int, data: bytes):
        if isinstance(data, int):
            data = encode_uint16(data)
        elif isinstance(data, (list, tuple)):
            buf = bytearray()
            for d in data:
                if isinstance(d, int):
                    d = encode_uint16(d)
                buf.extend(d)
            data = bytes(buf)
        self.write(b'\xff' + MESSAGE_SET_MEMORY)
        self.write_uint16(loc)
        self.send_bytes(data)


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
