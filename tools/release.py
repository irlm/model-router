"""Tag the widget's version: a release is a git tag v<version>, where <version> is mod/.claude-plugin/plugin.json.

The checks before the tag: the version is the newest entry in CHANGELOG.md, the working tree is clean, and the
tag does not exist yet. The tag is local until `git push --tags`; the directory publishes a version when the
number rises, and a machine that wants to stay on a version checks it out (`git checkout v0.12.0`).

  python3 tools/release.py           check and tag HEAD
  python3 tools/release.py --check   checks only (the tests run this)
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def version():
    return json.loads((ROOT / 'mod' / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))['version']


def changelog_top(text=None):
    """The newest version heading in CHANGELOG.md."""
    text = text if text is not None else (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    m = re.search(r'^## (\d+\.\d+\.\d+)', text, re.M)
    return m.group(1) if m else None


def loaded_version():
    """The WIDGET_VERSION constant in mod/hooks/register.tsx: what a loaded widget says it is."""
    m = re.search(r"const WIDGET_VERSION = '([^']+)'", (ROOT / 'mod' / 'hooks' / 'register.tsx').read_text(encoding='utf-8'))
    return m.group(1) if m else None


def problems(ver=None, top=None, dirty=None, tags=None, loaded=None):
    """What stands between HEAD and a tag; empty when nothing does. Arguments are for the tests; default: this checkout."""
    git = shutil.which('git')
    ver = ver if ver is not None else version()
    top = top if top is not None else changelog_top()
    if dirty is None:
        dirty = subprocess.run([git, 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout.strip() if git else ''
    if tags is None:
        tags = subprocess.run([git, 'tag', '--list'], cwd=ROOT, capture_output=True, text=True).stdout.split() if git else []
    out = []
    loaded = loaded if loaded is not None else loaded_version()
    if top != ver:
        out.append(f"plugin.json says {ver} but the newest CHANGELOG.md entry is {top}: add the entry or fix the version")
    if loaded != ver:
        out.append(f"plugin.json says {ver} but WIDGET_VERSION in mod/hooks/register.tsx is {loaded}: the loaded widget must name its version")
    if dirty:
        out.append(f"{len(dirty.splitlines())} uncommitted change(s): commit first, the tag names a commit")
    if f'v{ver}' in tags:
        out.append(f"v{ver} exists already: bump the version for a new release")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)
    ver = version()
    probs = problems(ver)
    for p in probs:
        print('not yet:', p)
    if probs:
        return 1
    print(f"v{ver}: {'ready to tag' if args.check else 'tagging'} (CHANGELOG entry present, tree clean)")
    if args.check:
        return 0
    subprocess.run([shutil.which('git'), 'tag', '-a', f'v{ver}', '-m', f'widget {ver}'], cwd=ROOT, check=True)
    print(f"tagged v{ver}; git push --tags publishes it")
    return 0


if __name__ == '__main__':
    sys.exit(main())
