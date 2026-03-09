import re


TOKEN_RE = re.compile(r' +|#.*|"([^"]|\\.)*"|\'\\?.\'|[^ ]+')
NAME_RE = re.compile(r'(?:_|[a-zA-Z0-9])[a-zA-Z0-9]*')

OPERATORS = {
    '+',
    '-',
    '*',
    '/',
    '%',
    '<<',
    '>>',
    '==',
    '!=',
    '<',
    '>',
    '<=',
    '>=',
    '!',
    '&',
    '|',
    '^',
    '$',
    '$c',
    '=$',
    '=$c',
}


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
                yield ('op', token)
            elif token[0] == '#':
                pass
            elif token == '}':
                if expected != '}':
                    raise Exception("Unexpected '}'")
                else:
                    return
            elif token in ('if', 'loop'):
                expect('{')
                body = _parse(tokens, '}')
                yield (token, body)
            elif token[0] == "'":
                c = _escaped(token[2]) if token[1] == '\\' else token[1]
                yield ('char', c)
            elif token[0] == '"':
                s = _parse_string(token)
                yield ('string', s)
            elif token.isdigit() or token[0] == '-' and token[1:].isdigit():
                i = int(token)
                yield ('int', i)
            elif token[0] == '=' and NAME_RE.fullmatch(token[1:]):
                yield ('assign', token[1:])
            elif NAME_RE.fullmatch(token):
                yield ('name', token)
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
        if t in ('if', 'loop'):
            print(indent + f'{t}:')
            ppt(v, depth + 1)
        else:
            print(indent + f'{t}: {v!r}')


def parse(lines):
    r"""

        >>> ppt(parse('0 =i loop { i 3 < ! if { break } i 1 - =i }'))
        int: 0
        assign: 'i'
        loop:
          name: 'i'
          int: 3
          op: '<'
          op: '!'
          if:
            name: 'break'
          name: 'i'
          int: 1
          op: '-'
          assign: 'i'

    """
    if isinstance(lines, str):
        lines = lines.splitlines()
    def get_tokens():
        for line_i, line in enumerate(lines):
            for token in tokenize(line):
                yield line_i, token
    yield from _parse(get_tokens())
