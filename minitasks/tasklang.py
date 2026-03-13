import re
from typing import NamedTuple, List, Dict, Set


class Compilation(NamedTuple):
    """Result of compiling some code"""

    # Maps string literals to heap offsets
    strings: Dict[str, int]

    # Maps global variable names to heap offsets
    vars: Dict[str, int]

    instructions: List[int]

    # Marks indexes of self.instructions which are indexes into task's
    # CODE section
    code_locations: Set[int]

    # Marks indexes of self.instructions which are indexes into task's
    # HEAP section
    heap_locations: Set[int]

    # Marks indexes of self.instructions which are indexes into BUILTINS
    builtin_locations: Set[int]

    @property
    def heap_size(self) -> int:
        return (
            sum(len(s) for s in self.strings) # the string bytes
            + len(self.strings) # the NUL terminators
            + 2 * len(self.vars) # 2 bytes per variable
        )

    @property
    def heap(self) -> bytes:
        """The heap (not including instructions)"""
        size = self.heap_size
        buf = bytearray(size)
        for value, loc in self.strings.items():
            buf[loc:loc + len(value)] = value.encode()
        return bytes(buf)

    def print_instructions(self):
        for loc, i in enumerate(self.instructions):
            if loc in self.builtin_locations:
                i = BUILTINS[i]
            print(f"{loc:03}: {i}")

    def print(self):
        print("vars:")
        for var, loc in self.vars.items():
            print(f"  {var}: {loc}")
        print(f"heap: {self.heap}")
        print("instructions:")
        self.print_instructions()


TOKEN_RE = re.compile(r' +|#.*|"([^"]|\\.)*"|\'\\?.\'|[^ ]+')
NAME_RE = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*')


BLOCK_TOKENS = ('if', 'loop', 'atomic')
BLOCK_TAGS = BLOCK_TOKENS + ('block',)


# Maps tasklang symbols to names of OS builtin functions
OPERATORS = {
    '+': 'add',
    '-': 'sub',
    '*': 'mul',
    '/': 'div',
    '%': 'mod',
    '<<': 'lshift',
    '>>': 'rshift',
    '==': 'eq',
    '!=': 'ne',
    '<': 'lt',
    '>': 'gt',
    '<=': 'le',
    '>=': 'ge',
    '!': 'not',
    '~': 'bitnot',
    '&': 'bitand',
    '|': 'bitor',
    '^': 'bitxor',
    '$': 'getptr',
    '$c': 'getptrc',
    '=$': 'setptr',
    '=$c': 'setptrc',
}

# OS builtin functions which can't be used directly
PRIVATE_BUILTINS = {
    '_literal': None,
    '_store': None,
    '_load': None,
    '_jump': None,
    '_jumpif': None,
    '_jumpifnot': None,
    '_atomic': None,
    '_end_atomic': None,
}

# OS builtin functions which can be used directly
PUBLIC_BUILTINS = {
    'dup': None,
    'swap': None,
    'drop': None,
    'heap': None,
    'hpush': None,
    'hpop': None,
    'hdrop': None,
    'hpushc': None,
    'hpopc': None,
    'hdropc': None,
    'assert': None,
    'error': None,
    'set_led': None,
    'sleep': None,
    'getc': None,
    'putc': None,
    'logs': None,
    'logc': None,
    'logi': None,
    'logp': None,
    'halt': None,

    # like 'halt', but increments instruction pointer, so task can be started
    # from there, i.e. 'pause' is a debugging breakpoint
    'pause': None,
}

# Maps builtin names to their index in the OS builtins table
# NOTE: this list of builtins must be in the same order as that of _BUILTINS
# in minitasks.h!.. the names don't need to match up exactly, but the order
# must be the same.
BUILTINS = (
    list(OPERATORS.values())
    + list(PRIVATE_BUILTINS)
    + list(PUBLIC_BUILTINS))
BUILTIN_INDEXES = {name: i for i, name in enumerate(BUILTINS)}


def tokenize(line):
    r"""

        >>> list(tokenize(r' 0 =i "Hello\nworld" { } # The rest is a comment'))
        ['0', '=i', '"Hello\\nworld"', '{', '}', '# The rest is a comment']

        >>> list(tokenize(r" 'x' '\0' "))
        ["'x'", "'\\0'"]

    """
    for match in TOKEN_RE.finditer(line):
        token = match.group(0)
        if token and token.count(' ') != len(token):
            yield token


def _escaped(c):
    return {
        '\\': '\\',
        'n': '\n',
        '0': '\0',
    }[c]


def _parse_string(token):
    cc = []
    escaping = False
    for c in token[1:-1]:
        if escaping:
            cc.append(_escaped(c))
            escaping = False
        elif c == '\\':
            escaping = True
        else:
            cc.append(c)
    return ''.join(cc)


def _parse(tokens, expected=None):
    def expect(expected):
        line_i, token = next(tokens)
        if token != expected:
            raise Exception(f"Expected {expected!r}, got {token!r}")
    for line_i, token in tokens:
        try:
            if token in OPERATORS:
                yield ('builtin', OPERATORS[token])
            elif token[0] == '#':
                # Comment
                pass
            elif token in '()':
                # Parentheses can be used as a visual aid, to indicate
                # expected stack effects, e.g. "( 1 2 f ) ( 3 4 g ) h"
                # may be a bit clearer than "1 2 f 3 4 g h"
                pass
            elif token == '}':
                if expected != '}':
                    raise Exception("Unexpected '}'")
                else:
                    return
            elif token in BLOCK_TOKENS:
                expect('{')
                body = _parse(tokens, '}')
                yield (token, body)
            elif token == '{':
                body = _parse(tokens, '}')
                yield ('block', body)
            elif token in ('while', 'continue', 'break'):
                yield (token, None)
            elif token[0] == "'":
                c = _escaped(token[2]) if token[1] == '\\' else token[1]
                yield ('int', ord(c))
            elif token[0] == '"':
                s = _parse_string(token)
                yield ('string', s)
            elif token.isdigit() or token[0] == '-' and token[1:].isdigit():
                i = int(token)
                yield ('int', i)
            elif token[0] == '=' and NAME_RE.fullmatch(token[1:]):
                yield ('store', token[1:])
            elif NAME_RE.fullmatch(token):
                if token in PUBLIC_BUILTINS:
                    yield ('builtin', token)
                else:
                    yield ('load', token)
            else:
                raise Exception("Unrecognized token")
        except Exception as ex:
            if expected is None:
                raise Exception(f"At line {line_i + 1}, token {token!r}: {ex.__class__.__name__}: {ex}")
            else:
                raise
    if expected is not None:
        raise Exception(f"Expected: {expected!r}")


def ppt(parsed, depth=0):
    """Print parse tree, for debugging"""
    indent = '  ' * depth
    for t, v in parsed:
        if t in BLOCK_TAGS:
            print(indent + f'{t}:')
            ppt(v, depth + 1)
        else:
            print(indent + f'{t}: {v!r}')


def parse(lines):
    r"""

        >>> ppt(parse('0 =i loop { i 3 < ! if { break } i logi i 1 - =i }'))
        int: 0
        store: 'i'
        loop:
          load: 'i'
          int: 3
          builtin: 'lt'
          builtin: 'not'
          if:
            break: None
          load: 'i'
          builtin: 'logi'
          load: 'i'
          int: 1
          builtin: 'sub'
          store: 'i'

    """
    if isinstance(lines, str):
        lines = lines.splitlines()
    def get_tokens():
        for line_i, line in enumerate(lines):
            for token in tokenize(line):
                yield line_i, token
    yield from _parse(get_tokens())


def compile(parsed) -> Compilation:
    r"""

        >>> comp = compile(parse('''0 =i loop {
        ...     i 3 < ! if { break }
        ...     atomic { "hello " logs i logi " world" logi }
        ...     i 1 - =i
        ... }'''))

        >>> comp.strings
        {'hello ': 2, ' world': 9}

        >>> comp.vars
        {'i': 0}

        Heap contains two bytes at the start for variable 'i', then the
        two strings with NUL terminators:
        >>> comp.heap
        b'\x00\x00hello \x00 world\x00'

        >>> comp.print_instructions()
        000: _literal
        001: 0
        002: _store
        003: 0
        004: _load
        005: 0
        006: _literal
        007: 3
        008: lt
        009: not
        010: _jumpif
        011: 14
        012: _jump
        013: 32
        014: _atomic
        015: _literal
        016: 2
        017: logs
        018: _load
        019: 0
        020: logi
        021: _literal
        022: 9
        023: logi
        024: _end_atomic
        025: _load
        026: 0
        027: _literal
        028: 1
        029: sub
        030: _store
        031: 0
        032: _jump
        033: 4
        034: halt

    """

    strings: Dict[str, int] = {}
    vars: Dict[str, int] = {}
    instructions: List[int] = []
    code_locations: Set[int] = set()
    heap_locations: Set[int] = set()
    builtin_locations: Set[int] = set()

    heap_offset = 0

    def getvar(name: str) -> int:
        nonlocal heap_offset
        if name not in vars:
            vars[name] = heap_offset
            heap_offset += 2
        return vars[name]

    def get_string(value: str) -> int:
        nonlocal heap_offset
        if value not in strings:
            strings[value] = heap_offset
            heap_offset += len(value) + 1 # plus one for NUL terminator
        return strings[value]

    def push_code_location(value: int):
        code_locations.add(len(instructions))
        instructions.append(value)

    def push_heap_location(value: int):
        heap_locations.add(len(instructions))
        instructions.append(value)

    def push_builtin(builtin: str):
        builtin_locations.add(len(instructions))
        instructions.append(BUILTIN_INDEXES[builtin])

    def push_value(value: int):
        instructions.append(value)

    def _process(parsed, strong_block=True, start_of_block=None, update_with_end_of_block=None):
        if strong_block:
            start_of_block = len(instructions)
            update_with_end_of_block = []
        for tag, data in parsed:
            if tag == 'builtin':
                push_builtin(data)
            elif tag == 'if':
                push_builtin('_jumpif')
                i = len(instructions)
                push_code_location(None) # jump location, updated below
                _process(data, False, start_of_block, update_with_end_of_block)
                instructions[i] = len(instructions) # update jump location
            elif tag == 'loop':
                i = len(instructions)
                _process(data)
                push_builtin('_jump')
                push_code_location(i)
            elif tag == 'atomic':
                push_builtin('_atomic')
                _process(data, False, start_of_block, update_with_end_of_block)
                push_builtin('_end_atomic')
            elif tag == 'block':
                _process(data)
            elif tag == 'while':
                push_builtin('_jumpifnot')
                update_with_end_of_block.append(len(instructions))
                # jump location, updated below (via update_with_end_of_block)
                push_code_location(None)
            elif tag == 'continue':
                push_builtin('_jump')
                push_code_location(start_of_block)
            elif tag == 'break':
                push_builtin('_jump')
                update_with_end_of_block.append(len(instructions))
                # jump location, updated below (via update_with_end_of_block)
                push_code_location(None)
            elif tag == 'int':
                push_builtin('_literal')
                push_value(data)
            elif tag == 'string':
                push_builtin('_literal')
                push_heap_location(get_string(data))
            elif tag == 'store':
                push_builtin('_store')
                push_heap_location(getvar(data))
            elif tag == 'load':
                push_builtin('_load')
                push_heap_location(getvar(data))
            else:
                raise Exception("Unrecognized tag: {tag!r}")

        if strong_block:
            # Update any instructions, e.g. break, which needed to know the
            # location of the end of the block
            end_of_block = len(instructions)
            for i in update_with_end_of_block:
                instructions[i] = end_of_block

    # Recursively process the parse tree
    _process(parsed)
    push_builtin('halt')

    return Compilation(
        strings=strings,
        vars=vars,
        instructions=instructions,
        code_locations=code_locations,
        heap_locations=heap_locations,
        builtin_locations=builtin_locations,
    )
