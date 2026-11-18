#!/usr/bin/env python3
"""Update the model-router install on this machine, by itself: the marketplace, then the plugin.
This is what /router upgrade runs. It needs nothing but git and the claude CLI.

What it does, in order:
  1. Finds the marketplace in Claude Code's own record (known_marketplaces.json): a GitHub clone, or a checkout.
  2. Brings the marketplace up to date. A GitHub clone: `claude plugin marketplace update`, then the clone's
     commit is compared with GitHub and fast-forwarded when the update left it behind (Claude Code has said
     "Successfully updated" and kept a stale clone, 2026-11-09). A checkout of your own: fast-forwarded only when
     clean and behind; a checkout with uncommitted work is left alone and said so.
  3. `claude plugin update model-router@model-router`: the cached copy a new session loads.
  4. Says what changed and what remains: /reload-plugins in the sessions that are open (a new session has it).

Usage: python3 tools/upgrade.py [--check [--fresh]] [--json]
  --check   say whether a newer version is published, change nothing; the answer is kept a day in
            <config>/model-router/upgrade-check.json (the pane's advice reads that file; the widget runs
            the check once per session start), --fresh asks GitHub now
  --json    the check as JSON

Exit 0 when up to date or updated, 1 when a step failed, 2 when the install is not one this tool knows.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / 'tools'))
import claude_home  # noqa: E402

PLUGIN = 'model-router'
MARKETPLACE = 'model-router'
UPSTREAM = 'https://github.com/irlm/model-router'
CHECK_FILE = 'upgrade-check.json'
CHECK_TTL = 24 * 3600


def sh(argv, cwd=None, timeout=120):
    """(rc, stdout, stderr); a missing program or a timeout is rc 127 with the reason in stderr."""
    try:
        p = subprocess.run(argv, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout,
                           encoding='utf-8', errors='replace')
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, '', str(e)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))   # a BOM on Windows
    except (OSError, ValueError):
        return None


def marketplace():
    """Where the marketplace lives and what it is: {'path', 'kind': 'github'|'directory'|None}."""
    known = read_json(claude_home.config_dir() / 'plugins' / 'known_marketplaces.json') or {}
    rec = known.get(MARKETPLACE) if isinstance(known, dict) else None
    if not isinstance(rec, dict):
        return {'path': None, 'kind': None}
    src = rec.get('source') if isinstance(rec.get('source'), dict) else {}
    return {'path': rec.get('installLocation'), 'kind': src.get('source')}


def installed_version():
    d = read_json(claude_home.config_dir() / 'plugins' / 'installed_plugins.json') or {}
    plugins = d.get('plugins') if isinstance(d, dict) else None
    rec = (plugins or {}).get(f'{PLUGIN}@{MARKETPLACE}') if isinstance(plugins, dict) else None
    if isinstance(rec, list):
        rec = rec[0] if rec else None
    return rec.get('version') if isinstance(rec, dict) else None


def published_version(git):
    """The version GitHub publishes: the newest v* tag's number, by its name (the tag is the release)."""
    rc, out, err = sh([git, 'ls-remote', '--tags', '--refs', UPSTREAM], timeout=60)
    if rc != 0:
        return None, err.splitlines()[-1] if err else f'git ls-remote exit {rc}'
    versions = []
    for line in out.splitlines():
        m = re.search(r'refs/tags/v(\d+\.\d+\.\d+)$', line)
        if m:
            versions.append(tuple(int(x) for x in m.group(1).split('.')))
    if not versions:
        return None, 'no v* tag on GitHub'
    return '.'.join(str(x) for x in max(versions)), None


def newer(a, b):
    """a is a newer version than b (dotted numbers; None is older than anything)."""
    key = lambda v: tuple(int(x) for x in re.findall(r'\d+', v or '0'))  # noqa: E731
    return key(a) > key(b)


def check(git, fresh=False):
    """{'installed', 'published', 'behind', 'error', 'at'}: cached a day, since it asks GitHub."""
    state_dir = claude_home.config_dir() / PLUGIN
    cache = read_json(state_dir / CHECK_FILE) or {}
    installed = installed_version()
    if not fresh and cache.get('at') and time.time() - cache['at'] < CHECK_TTL and cache.get('installed') == installed:
        return cache
    published, err = published_version(git) if git else (None, 'git not on PATH')
    rec = {'installed': installed, 'published': published, 'behind': bool(published and newer(published, installed)),
           'error': err, 'at': time.time()}
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / CHECK_FILE).write_text(json.dumps(rec, indent=1) + '\n', encoding='utf-8')
    except OSError:
        pass
    return rec


def advice():
    """One line for the pane's advice when a newer version is published, else None. Reads the cache only (no
    network from the status read); --check and the upgrade itself refresh it."""
    rec = read_json(claude_home.config_dir() / PLUGIN / CHECK_FILE) or {}
    if rec.get('behind') and rec.get('installed'):
        return f"model-router {rec['published']} is published, {rec['installed']} installed: /router upgrade"
    return None


def head_of(git, path):
    rc, out, _ = sh([git, 'rev-parse', 'HEAD'], cwd=path)
    return out if rc == 0 else None


def step(title, argv, cwd=None):
    print(f'$ {" ".join(argv)}', flush=True)
    rc, out, err = sh(argv, cwd=cwd, timeout=300)
    for line in (out + ('\n' + err if err else '')).splitlines():
        if line.strip():
            print(f'  {line}', flush=True)
    if rc != 0:
        print(f'{title} failed (exit {rc})', flush=True)
    return rc == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--fresh', action='store_true')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    git = shutil.which('git')
    claude = shutil.which('claude')
    if args.check:
        rec = check(git, fresh=args.fresh)
        if args.json:
            print(json.dumps(rec, indent=1))
        elif rec['error']:
            print(f"could not ask GitHub: {rec['error']} (installed {rec['installed'] or 'unknown'})")
        else:
            print(f"installed {rec['installed'] or 'unknown'}, published {rec['published']}: "
                  + ('newer on GitHub; /router upgrade installs it' if rec['behind'] else 'up to date'))
        return 0

    if not git:
        print('git is not on PATH: nothing can be updated')
        return 1
    if not claude:
        print('the claude CLI is not on PATH: the plugin update needs it')
        return 1
    mk = marketplace()
    before = installed_version()
    print(f"installed {before or 'unknown'}; marketplace: {mk['kind'] or 'unknown'} at {mk['path'] or '?'}", flush=True)
    ok = True
    path = Path(mk['path']) if mk['path'] else None
    if mk['kind'] == 'github':
        ok = step('marketplace update', [claude, 'plugin', 'marketplace', 'update', MARKETPLACE])
        if path and (path / '.git').exists():
            rc, out, _ = sh([git, 'ls-remote', UPSTREAM, 'HEAD'], timeout=60)
            upstream = out.split()[0] if rc == 0 and out else None
            if upstream and head_of(git, path) != upstream:
                print('the marketplace clone is behind GitHub after the update: pulling it', flush=True)
                ok = step('clone pull', [git, '-C', str(path), 'pull', '--ff-only']) and ok
    elif mk['kind'] == 'directory' and path and (path / '.git').exists():
        _, dirty, _ = sh([git, 'status', '--porcelain'], cwd=path)
        sh([git, 'fetch', '-q'], cwd=path, timeout=90)
        rc2, lr, _ = sh([git, 'rev-list', '--left-right', '--count', 'HEAD...@{u}'], cwd=path)
        behind = int(lr.split()[1]) if rc2 == 0 and len(lr.split()) == 2 else 0
        if dirty.strip():
            print(f'the checkout at {path} has uncommitted changes: left as it is (the plugin update reads it as it stands)', flush=True)
        elif behind:
            print(f'the checkout is {behind} commit(s) behind its origin: pulling', flush=True)
            ok = step('checkout pull', [git, '-C', str(path), 'pull', '--ff-only']) and ok
        else:
            print('the checkout is current', flush=True)
    elif mk['kind'] is None:
        print(f"no marketplace named {MARKETPLACE} in Claude Code's record: install it first "
              f"(claude plugin marketplace add {UPSTREAM})", flush=True)
        return 2
    ok = step('plugin update', [claude, 'plugin', 'update', f'{PLUGIN}@{MARKETPLACE}']) and ok
    after = installed_version()
    check(git, fresh=True)   # the advice line goes away when the install is current
    if after and after != before:
        print(f'model-router {before or "none"} -> {after}: /reload-plugins in the sessions that are open; a new session has it', flush=True)
    elif ok:
        print(f'model-router {after or "unknown"} is current', flush=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
