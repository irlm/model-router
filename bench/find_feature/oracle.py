"""Mechanical ground truth from a pinned Linux tree. Stdlib + ripgrep.

Every fact this module emits is string-verifiable against the tree:
- a REAL function: we extracted its definition line and the symbol
  occurs in the tree; a BAIT name: zero occurrences of the whole word
  anywhere in the tree (any mention at all disqualifies the bait).
- struct fields come only from structs whose entire body our parser
  understands (no preprocessor lines, no nested braces); anything else
  is rejected rather than half-parsed.
- "references" are whole-word occurrences followed by '('; negatives
  are files with zero occurrences of the symbol string at all.
"""
import re
import subprocess
from pathlib import Path

DEF_LINE = re.compile(
    r'^(?:static\s+)?(?:inline\s+)?(?:__\w+\s+)*'
    r'[a-zA-Z_][\w\s\*]*?\b([a-z_][a-z0-9_]{7,})\s*\(')
FIELD_PATTERNS = [
    re.compile(r'^.*\(\s*\*\s*([a-zA-Z_]\w*)\s*\)\s*\(.*\)$'),      # fn ptr
    re.compile(r'^[\w\s\*]+?\*?\s*([a-zA-Z_]\w*)\s*\[[^\]]*\]$'),   # array
    re.compile(r'^[\w\s\*]+?\*?\s*([a-zA-Z_]\w*)\s*(?::\s*\d+)?$'), # plain/bitfield
]
KEYWORDS = {'return', 'sizeof', 'struct', 'union', 'enum', 'const', 'unsigned',
            'signed', 'volatile', 'static', 'inline', 'void', 'int', 'char',
            'long', 'short', 'bool', 'if', 'for', 'while', 'switch', 'else',
            'do', 'goto', 'u8', 'u16', 'u32', 'u64', 's8', 's16', 's32', 's64'}


def rg(args, tree, check=False):
    # stdin must be closed and a search path explicit: with a pipe for
    # stdin and no path, rg reads stdin instead of the tree (hangs in
    # background shells, or silently matches nothing against /dev/null
    # - which would falsely "verify" baits as absent).
    proc = subprocess.run(['rg', '--no-messages'] + args, cwd=tree,
                          stdin=subprocess.DEVNULL,
                          capture_output=True, text=True)
    if check and proc.returncode > 1:
        raise RuntimeError(proc.stderr[:500])
    return proc.stdout


def word_occurrences(tree, name):
    """Files containing the whole word; empty list proves a bait."""
    out = rg(['-l', '-w', '--fixed-strings', name, '.'], tree)
    return sorted(line.removeprefix('./') for line in out.splitlines() if line)


def is_absent(tree, name):
    return not word_occurrences(tree, name)


def definition_sites(tree, subdirs):
    """(name, file) pairs for lines that look like C function definitions
    in .c files: a DEF_LINE match whose statement opens a brace rather
    than ending in ';' (declaration). Conservative; misses are fine."""
    sites = {}
    out = rg(['-n', '--type', 'c', r'^[a-zA-Z_].*\(', *subdirs], tree)
    files = {}
    for line in out.splitlines():
        path, number, text = line.split(':', 2)
        if not path.endswith('.c'):
            continue
        match = DEF_LINE.match(text)
        if not match or match.group(1) in KEYWORDS:
            continue
        files.setdefault(path, []).append((int(number), match.group(1)))
    for path, hits in files.items():
        lines = (Path(tree) / path).read_text(errors='replace').splitlines()
        for number, name in hits:
            window = ' '.join(lines[number - 1:number + 2])
            head = window.split('{')[0]
            if '{' in window and ';' not in head and '=' not in head:
                sites.setdefault(name, set()).add(path)
    return {n: sorted(p) for n, p in sites.items()}


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    return re.sub(r'//[^\n]*', ' ', text)


def parse_struct(tree, path, name):
    """Field names of `struct name` in path, or None when any part of
    the body is outside what we can parse with certainty."""
    text = strip_comments((Path(tree) / path).read_text(errors='replace'))
    match = re.search(r'^struct\s+%s\s*\{' % re.escape(name), text, re.M)
    if not match:
        return None
    depth, i = 1, match.end()
    while depth and i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1
    body = text[match.end():i - 1]
    if depth or '{' in body or '#' in body or not body.strip():
        return None
    fields = []
    for declaration in body.split(';'):
        declaration = ' '.join(declaration.split())
        if not declaration:
            continue
        for pattern in FIELD_PATTERNS:
            found = pattern.match(declaration)
            if found and found.group(1) not in KEYWORDS:
                fields.append(found.group(1))
                break
        else:
            return None
    return fields if len(fields) >= 4 else None


def struct_candidates(tree, subdirs):
    out = rg(['-n', r'^struct\s+([a-z_][a-z0-9_]{4,})\s*\{', '--type', 'h',
              '-o', '--replace', '$1', *subdirs], tree)
    pairs = set()
    for line in out.splitlines():
        path, _, name = line.split(':', 2)
        pairs.add((path, name))
    return sorted(pairs)


def referencing_files(tree, name, exclude):
    """Small .c files with a call-shaped reference `name(`."""
    out = rg(['-l', '--type', 'c', r'\b' + re.escape(name) + r'\s*\(', '.'], tree)
    result = []
    for path in sorted({line.removeprefix('./') for line in out.splitlines()}):
        if path and path not in exclude and (Path(tree) / path).stat().st_size <= 15000:
            result.append(path)
    return result


def clean_negatives(tree, name, near, count):
    """Small .c files near `near` with ZERO occurrences of name."""
    pool = sorted((Path(tree) / near).parent.glob('*.c'))
    negatives = []
    for path in pool:
        rel = str(path.relative_to(tree))
        if path.stat().st_size <= 15000 and name not in path.read_text(errors='replace'):
            negatives.append(rel)
        if len(negatives) == count:
            break
    return negatives
