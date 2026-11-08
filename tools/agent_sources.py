"""Agent files that come from outside this repository: pinned to the commit they were taken from, updated only
after the diff was shown and the change was taken by name.

An agent file is instructions the model follows with your permissions, Bash included, so a change upstream
is treated like a code change: nothing here pulls one on its own. The registry (one per machine, in
<CLAUDE_CONFIG_DIR or ~/.claude>/model-router/agent-sources.json, with a copy of each pinned file beside it)
records, per source repository, the commit and the digest of each file as it came, and the digest of the
file on disk after the last write this repository made (pin, update, apply_agents.py). status.py reads the
registry only, never the network; `check` and `update` clone the source shallowly into a temporary folder.

  python3 tools/agent_sources.py pin --repo URL [--ref BRANCH]    record every agent file here that URL also has
  python3 tools/agent_sources.py check                             what changed upstream since the pin, with flags
  python3 tools/agent_sources.py update [FILE...] [--accept-flags] take the changes: all unflagged, or the named ones
  python3 tools/agent_sources.py list

A flag is a line the change adds that matches a pattern worth a second look (a URL, a shell download, a
secret's path or name, an instruction to hide something or to ignore earlier ones, invisible Unicode, a
`tools:` line that grants Bash or writing). A flag cannot clear or convict a change; it decides only that
`update` will not take the file unless it is named with --accept-flags.
"""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agent_files  # noqa: E402
import claude_home  # noqa: E402

SHIPPED = HERE.parent / 'agents'   # the agent files this repository ships: versioned with it, not pinned here
CHECK_DAYS = 30                    # a pin not checked for this long gets a "to check" line

FLAGS = [
    ('url', re.compile(r'https?://', re.I)),
    ('download or exec', re.compile(r'\b(curl|wget|base64|eval|atob|nc|ncat|chmod \+x|powershell|Invoke-WebRequest|Invoke-Expression|sudo|rm -rf)\b', re.I)),
    ('secret', re.compile(r'(~|\$HOME)?/\.(ssh|aws|gnupg|netrc)\b|\bid_rsa\b|\.env\b|\b(token|password|passwd|secret|api[_ -]?key|credential)s?\b|\b[A-Z_]*(TOKEN|SECRET|KEY)\b')),
    ('override', re.compile(r'\b(ignore|disregard|forget)\b.{0,20}\b(previous|prior|above|earlier|system)\b|do not (tell|inform|mention|reveal)|without (telling|asking|informing)|\b(secretly|covertly|hidden from|exfiltrat)', re.I)),
    ('invisible unicode', re.compile('[​-‏⁠-⁤﻿‪-‮⁦-⁩]')),
    ('tools grant', re.compile(r'^\s*tools:.*\b(Bash|Write|Edit|NotebookEdit|Agent)\b')),
]


def registry_dir():
    return claude_home.config_dir() / 'model-router'


def registry_path():
    return registry_dir() / 'agent-sources.json'


def pinned_copy(file):
    return registry_dir() / 'agent-sources' / file


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def read():
    p = registry_path()
    if not p.exists():
        return {'sources': {}}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except ValueError:
        return {'sources': {}}


def write(reg):
    registry_dir().mkdir(parents=True, exist_ok=True)
    registry_path().write_text(json.dumps(reg, indent=1, sort_keys=True) + '\n', encoding='utf-8')


def pinned_files(reg):
    """file name -> (source url, entry)."""
    out = {}
    for url, src in (reg.get('sources') or {}).items():
        for file, e in (src.get('files') or {}).items():
            out[file] = (url, e)
    return out


def outside_files(agents_dir):
    """The agent files on this machine that this repository does not ship: candidates for a pin."""
    agents_dir = Path(agents_dir)
    if not agents_dir.is_dir():
        return []
    return sorted(p for p in agents_dir.rglob('*.md') if agent_files.is_agent(p) and not (SHIPPED / p.name).exists())


def source_hint(agents_dir):
    """A repository URL a collection names in a README or CONTRIBUTING beside its agents, if any."""
    agents_dir = Path(agents_dir)
    for name in ('README.md', 'CONTRIBUTING.md'):
        p = agents_dir / name
        if p.exists():
            m = re.search(r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?(?=[\s/)\]"\'>]|$)', p.read_text(encoding='utf-8', errors='replace'))
            if m:
                return f"https://github.com/{m.group(1)}"
    return None


def clone(url, ref=None):
    """A shallow clone of the source in a temporary folder: (folder, commit). The caller removes the folder."""
    git = shutil.which('git')
    if not git:
        raise RuntimeError('git not found on PATH')
    folder = Path(tempfile.mkdtemp(prefix='agent-source-'))
    argv = [git, 'clone', '--quiet', '--depth', '1', *(['--branch', ref] if ref else []), url, str(folder)]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        shutil.rmtree(folder, ignore_errors=True)
        raise RuntimeError(f"clone of {url} failed: {(r.stderr or r.stdout).strip()}")
    commit = subprocess.run([git, 'rev-parse', 'HEAD'], cwd=folder, capture_output=True, text=True).stdout.strip()
    return folder, commit


def find_in(folder, file):
    """The file with this name in the clone (a collection keeps its agents in folders by category)."""
    found = sorted(p for p in Path(folder).rglob(file) if '.git' not in p.parts)
    return found[0] if found else None


def flags_in(diff_lines):
    """(flag, added line) for every added line of a unified diff that matches a pattern."""
    out = []
    for line in diff_lines:
        if not line.startswith('+') or line.startswith('+++'):
            continue
        body = line[1:]
        for name, rx in FLAGS:
            if rx.search(body):
                out.append((name, body.rstrip()))
                break
    return out


def unified(before, after, file):
    return list(difflib.unified_diff(before.splitlines(), after.splitlines(), f"{file} (pinned)", f"{file} (upstream)", lineterm='', n=2))


def local_state(agents_dir, reg):
    """Per pinned file, whether the copy on disk is the one this repository last wrote."""
    out = {}
    for file, (url, e) in pinned_files(reg).items():
        p = agent_files.locate(agents_dir, file)
        if p is None:
            out[file] = 'gone'
        else:
            out[file] = 'same' if digest(p.read_text(encoding='utf-8', errors='replace')) == e.get('local_digest') else 'changed'
    return out


def note_written(path):
    """apply_agents.py wrote this file: its digest is the one this repository last wrote. Silent when not pinned."""
    reg = read()
    name = Path(path).name
    for src in (reg.get('sources') or {}).values():
        e = (src.get('files') or {}).get(name)
        if e is not None:
            e['local_digest'] = digest(Path(path).read_text(encoding='utf-8', errors='replace'))
            write(reg)
            return True
    return False


def notes(agents_dir, today=None):
    """The "to check" lines for status.py, from the registry alone (no network)."""
    reg = read()
    pinned = pinned_files(reg)
    out = []
    unpinned = [p.name for p in outside_files(agents_dir) if p.name not in pinned]
    if unpinned:
        hint = source_hint(agents_dir)
        shown = ', '.join(unpinned[:4]) + (f" and {len(unpinned) - 4} more" if len(unpinned) > 4 else '')
        out.append(f"{len(unpinned)} agent file{'s' if len(unpinned) != 1 else ''} from outside this repository not pinned ({shown}): "
                   f"/router agents pin {hint or '<repository url>'} records the source so a change there is reviewed before it lands")
    for file, state in local_state(agents_dir, reg).items():
        if state == 'changed':
            out.append(f"agent {file} changed on disk since this repository last wrote it (not by apply or update): /router agents check shows the diff against the pin")
    today = today or datetime.date.today()
    for url, src in (reg.get('sources') or {}).items():
        pend = src.get('pending') or []
        if pend:
            flagged = sum(1 for p in pend if p.get('flags'))
            out.append(f"{len(pend)} pinned agent file{'s' if len(pend) != 1 else ''} changed upstream ({url}){f', {flagged} flagged' if flagged else ''}: "
                       f"/router agents check shows the diff; /router agents update <file> takes a change")
        checked = (src.get('checked') or src.get('pinned') or '')[:10]
        try:
            age = (today - datetime.date.fromisoformat(checked)).days if checked else None
        except ValueError:
            age = None
        if age is not None and age > CHECK_DAYS and not pend:
            out.append(f"pinned agent source {url} last checked {age} days ago: /router agents check")
    return out


def cmd_pin(args):
    agents_dir = Path(args.agents_dir)
    reg = read()
    folder, commit = clone(args.repo, args.ref)
    try:
        src = reg['sources'].setdefault(args.repo, {'files': {}})
        src.update({'commit': commit, 'ref': args.ref, 'pinned': now(), 'checked': now(), 'pending': []})
        found, missing = [], []
        for p in outside_files(agents_dir):
            up = find_in(folder, p.name)
            if up is None:
                missing.append(p.name)
                continue
            text = up.read_text(encoding='utf-8', errors='replace')
            pinned_copy(p.name).parent.mkdir(parents=True, exist_ok=True)
            pinned_copy(p.name).write_text(text, encoding='utf-8')
            src['files'][p.name] = {'path': str(up.relative_to(folder)).replace('\\', '/'), 'upstream_digest': digest(text),
                                    'local_digest': digest(p.read_text(encoding='utf-8', errors='replace'))}
            found.append(p.name)
        write(reg)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print(f"pinned {len(found)} agent file(s) to {args.repo} @ {commit[:12]}: {', '.join(found) or '-'}")
    if missing:
        print(f"not in that repository ({len(missing)}): {', '.join(missing)}")
    print('registry:', registry_path())
    return 0


def check_source(url, src, agents_dir):
    """Clone the source, compare every pinned file; returns the pending list and prints the diffs."""
    folder, commit = clone(url, src.get('ref'))
    pending = []
    try:
        for file, e in sorted(src['files'].items()):
            up = find_in(folder, file)
            if up is None:
                print(f"{file}: no longer in {url}")
                pending.append({'file': file, 'gone': True, 'flags': []})
                continue
            text = up.read_text(encoding='utf-8', errors='replace')
            if digest(text) == e['upstream_digest']:
                continue
            before = pinned_copy(file).read_text(encoding='utf-8', errors='replace') if pinned_copy(file).exists() else ''
            diff = unified(before, text, file)
            flags = flags_in(diff)
            pending.append({'file': file, 'flags': [f"{n}: {l}" for n, l in flags], 'added': sum(1 for l in diff if l.startswith('+') and not l.startswith('+++')),
                            'removed': sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))})
            print(f"\n{file}: changed upstream (+{pending[-1]['added']} -{pending[-1]['removed']} lines){' FLAGGED' if flags else ''}")
            for n, l in flags:
                print(f"  flag [{n}]: {l}")
            for line in diff:
                print('  ' + line)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    src['checked'] = now()
    src['upstream_commit'] = commit
    src['pending'] = pending
    return pending


def cmd_check(args):
    reg = read()
    if not reg['sources']:
        print('no pinned agent source; /router agents pin <repository url> records one')
        return 0
    agents_dir = Path(args.agents_dir)
    total = 0
    for url, src in reg['sources'].items():
        print(f"{url} @ {src.get('commit', '')[:12]}: {len(src.get('files') or {})} pinned file(s)")
        pending = check_source(url, src, agents_dir)
        total += len(pending)
        if not pending:
            print('  unchanged upstream')
    write(reg)
    for file, state in local_state(agents_dir, reg).items():
        if state != 'same':
            print(f"{file}: {'missing on disk' if state == 'gone' else 'changed on disk since this repository last wrote it'}")
    if total:
        flagged = sum(1 for s in reg['sources'].values() for p in s.get('pending') or [] if p.get('flags'))
        print(f"\n{total} file(s) changed upstream, {flagged} flagged. python3 tools/agent_sources.py update takes the unflagged ones; "
              f"update <file> --accept-flags takes a flagged one you have read")
    return 0


def cmd_update(args):
    reg = read()
    agents_dir = Path(args.agents_dir)
    taken, refused = [], []
    for url, src in reg['sources'].items():
        pend = {p['file']: p for p in src.get('pending') or []}
        wanted = [f for f in (args.files or list(pend)) if f in src['files']]
        if not wanted:
            continue
        folder, commit = clone(url, src.get('ref'))
        try:
            for file in wanted:
                p = pend.get(file)
                if p is None and not args.files:
                    continue
                if p and p.get('gone'):
                    refused.append(f"{file}: gone upstream; nothing to take")
                    continue
                if p and p.get('flags') and not (args.files and args.accept_flags):
                    refused.append(f"{file}: flagged ({len(p['flags'])}); name it with --accept-flags once you have read the diff")
                    continue
                up = find_in(folder, file)
                if up is None:
                    refused.append(f"{file}: not in the clone")
                    continue
                text = up.read_text(encoding='utf-8', errors='replace')
                dest = agent_files.locate(agents_dir, file) or (agents_dir / src['files'][file]['path'])
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding='utf-8')
                pinned_copy(file).parent.mkdir(parents=True, exist_ok=True)
                pinned_copy(file).write_text(text, encoding='utf-8')
                src['files'][file].update({'upstream_digest': digest(text), 'local_digest': digest(text)})
                pend.pop(file, None)
                taken.append(file)
        finally:
            shutil.rmtree(folder, ignore_errors=True)
        src['pending'] = list(pend.values())
        if not pend:
            src['commit'] = commit
    write(reg)
    print(f"taken {len(taken)}: {', '.join(taken) or '-'}")
    for r in refused:
        print('refused', r)
    if taken:
        print('routed files among them get their model and effort back with: python3 apply_agents.py (/router apply)')
    return 0 if not refused or taken else 1


def cmd_list(args):
    reg = read()
    if not reg['sources']:
        print('no pinned agent source')
        return 0
    for url, src in reg['sources'].items():
        print(f"{url} @ {src.get('commit', '')[:12]} pinned {src.get('pinned', '')} checked {src.get('checked', '')}")
        for file, e in sorted(src['files'].items()):
            print(f"  {file}  ({e['path']})")
        for p in src.get('pending') or []:
            print(f"  pending: {p['file']}{' FLAGGED' if p.get('flags') else ''}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--agents-dir', type=Path, default=claude_home.agents_dir())
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('pin'); p.add_argument('--repo', required=True); p.add_argument('--ref', default=None); p.set_defaults(fn=cmd_pin)
    p = sub.add_parser('check'); p.set_defaults(fn=cmd_check)
    p = sub.add_parser('update'); p.add_argument('files', nargs='*'); p.add_argument('--accept-flags', action='store_true'); p.set_defaults(fn=cmd_update)
    p = sub.add_parser('list'); p.set_defaults(fn=cmd_list)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
