"""KUnit build/run wrapper and mechanical function splicing.

The splicer is how K2 guarantees a model edit can only touch the one
target function: the model returns a complete C function, and we
replace exactly that function's span in the file. Brace matching uses
a small state machine aware of strings, chars and comments.
"""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
KUNITCONFIG = HERE / 'kunitconfig'
BUILD_DIR = '.kunit-k2'


def run_suite(tree, suite_glob, timeout=600, jobs=8):
    """Build + run one suite. Returns dict(passed, output_tail)."""
    proc = subprocess.run(
        ['python3', 'tools/testing/kunit/kunit.py', 'run',
         f'--kunitconfig={KUNITCONFIG}', f'--build_dir={BUILD_DIR}',
         f'--jobs={jobs}', suite_glob],
        cwd=tree, stdin=subprocess.DEVNULL, capture_output=True,
        text=True, timeout=timeout)
    tail = '\n'.join((proc.stdout + proc.stderr).splitlines()[-25:])
    return {'passed': proc.returncode == 0, 'output_tail': tail}


def _code_scan(text, start):
    """Yield (index, char) for code positions only (skips comments,
    string and char literals) beginning at `start`."""
    i, n = start, len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if c == '/' and nxt == '*':
            i = text.find('*/', i + 2)
            i = n if i == -1 else i + 2
            continue
        if c == '/' and nxt == '/':
            i = text.find('\n', i)
            i = n if i == -1 else i
            continue
        if c in ('"', "'"):
            quote, i = c, i + 1
            while i < n and text[i] != quote:
                i += 2 if text[i] == '\\' else 1
            i += 1
            continue
        yield i, c
        i += 1


def function_span(text, name):
    """(start, end) of the full definition of `name`, or None.
    Start is the beginning of the definition's first line; end is one
    past the closing brace. Prototypes (';' before '{') are skipped."""
    for match in re.finditer(r'^[A-Za-z_][^=;{}]*?\b%s\s*\(' % re.escape(name),
                             text, re.M):
        start = text.rfind('\n', 0, match.start()) + 1
        depth, body_open = 0, None
        for i, c in _code_scan(text, match.end() - 1):
            if c == ';' and depth == 0 and body_open is None:
                break  # prototype, try next match
            if c == '{':
                depth += 1
                if body_open is None:
                    body_open = i
            elif c == '}':
                depth -= 1
                if depth == 0 and body_open is not None:
                    return start, i + 1
            elif c == ')' and depth < 0:
                break
    return None


def splice_function(tree, path, name, replacement):
    """Replace `name`'s definition in tree/path with `replacement`.
    Returns the file's previous content (for restore), or None if the
    function was not found."""
    file = Path(tree) / path
    text = file.read_text()
    span = function_span(text, name)
    if span is None:
        return None
    file.write_text(text[:span[0]] + replacement.rstrip('\n') + '\n'
                    + text[span[1]:].lstrip('\n'))
    return text
