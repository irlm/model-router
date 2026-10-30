"""Build a mechanical evidence packet WITHOUT the answer key (K3 arm M).

The builder is handed only what the question itself states — family,
symbol name, candidate list — never a task's truth fields. It runs
blind rg searches over the pinned tree and reports results with
provenance and explicit coverage statements, so the model can answer
(or honestly abstain) from the packet alone.
"""
import re
import subprocess
from pathlib import Path

BUDGET_CHARS = 8000


def rg(args, cwd, timeout=120):
    """rg with the K1 traps closed: stdin never a pipe, paths explicit
    in args (rc 1 = no matches, which is a valid result)."""
    proc = subprocess.run(['rg', *args], cwd=cwd, text=True,
                          capture_output=True, stdin=subprocess.DEVNULL,
                          timeout=timeout)
    if proc.returncode > 1:
        raise RuntimeError(f'rg failed: {proc.stderr[:200]}')
    return proc.stdout


def _exists(tree, name, budget):
    out = rg(['-n', '--no-heading', '--fixed-strings', '--', name, '.'], tree)
    lines = [l.removeprefix('./') for l in out.splitlines() if l]
    files = {l.split(':', 1)[0] for l in lines}
    head = (f"Mechanical search report: rg --fixed-strings '{name}' over "
            f"the ENTIRE v6.12 tree.\nResult: {len(lines)} matching lines "
            f"in {len(files)} files.")
    if not lines:
        return head + ('\nThe search was exhaustive: this string occurs '
                       'nowhere in the tree.')
    shown, used = [], 0
    for line in lines:
        if used + len(line) > budget:
            shown.append(f'... truncated: {len(lines) - len(shown)} more '
                         'matching lines not shown.')
            break
        shown.append(line)
        used += len(line) + 1
    return head + '\nMatches (path:line:content):\n' + '\n'.join(shown)


def _struct_body(tree, path, lineno):
    lines = (Path(tree) / path).read_text(errors='replace').splitlines()
    depth, taken = 0, []
    for line in lines[lineno - 1:]:
        taken.append(line)
        depth += line.count('{') - line.count('}')
        if depth <= 0 and '{' in ''.join(taken):
            break
    return '\n'.join(taken)


def _fields(tree, name, budget):
    pattern = r'^struct\s+' + re.escape(name) + r'\s*\{'
    out = rg(['-n', '--no-heading', pattern, '.'], tree)
    hits = [l.removeprefix('./') for l in out.splitlines() if l][:2]
    head = (f"Mechanical search report: rg '{pattern}' over the ENTIRE "
            f"v6.12 tree.\nResult: {len(hits)} definition site(s) shown.")
    if not hits:
        return head + ('\nNo top-level definition of this struct was '
                       'found by this search.')
    blocks = []
    for hit in hits:
        path, lineno = hit.split(':', 2)[:2]
        body = _struct_body(tree, path, int(lineno))[:budget // len(hits)]
        blocks.append(f'=== {path}:{lineno} ===\n{body}')
    return head + '\n' + '\n\n'.join(blocks)


def _refs(tree, name, candidates, budget):
    pattern = r'\b' + re.escape(name) + r'\s*\('
    rows = []
    for path in candidates:
        out = rg(['-c', pattern, '--', path], tree).strip()
        rows.append(f'{path}: {out or 0} line(s) with a call-shaped '
                    f'occurrence `{name}(`')
    head = (f"Mechanical search report: rg '{pattern}' run separately on "
            f"each of the {len(candidates)} candidate files (full file "
            'scan each).')
    return (head + '\n' + '\n'.join(rows))[:budget]


def _dispatch(tree, name, budget):
    """K4: name is a user-visible path like /proc/sys/vm/drop_caches.
    Mechanical rule, no semantics: search the full literal, then the
    final path component, and show matching lines under the budget in
    rg traversal order (no relevance ranking — by design)."""
    sections = []
    for label, needle in [('full literal', name),
                          ('final component', name.rstrip('/').rsplit('/', 1)[-1])]:
        out = rg(['-n', '--no-heading', '--fixed-strings', '--', needle, '.'], tree)
        lines = [l.removeprefix('./') for l in out.splitlines() if l]
        head = (f"Search ({label}): rg --fixed-strings '{needle}' over the "
                f"ENTIRE v6.12 tree.\nResult: {len(lines)} matching lines.")
        if not lines:
            sections.append(head + '\nThis string occurs nowhere in the tree.')
            continue
        shown, used = [], 0
        for line in lines:
            if used + len(line) > budget // 2:
                shown.append(f'... truncated: {len(lines) - len(shown)} more '
                             'matching lines not shown.')
                break
            shown.append(line)
            used += len(line) + 1
        sections.append(head + '\nMatches (path:line:content):\n' + '\n'.join(shown))
    return ('Mechanical search report for the question subject '
            f"'{name}':\n\n" + '\n\n'.join(sections))


def build_packet(tree, family, name, candidates=None, budget=BUDGET_CHARS):
    if family == 'exists':
        return _exists(tree, name, budget)
    if family == 'fields':
        return _fields(tree, name, budget)
    # callers deliberately reuses the refs view: per-candidate counts of
    # call-SHAPED occurrences. Whether models treat shape as proof of a
    # call is the K4 hypothesis under test.
    if family in ('refs', 'callers'):
        return _refs(tree, name, candidates or [], budget)
    if family == 'dispatch':
        return _dispatch(tree, name, budget)
    raise ValueError(family)
