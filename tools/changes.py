"""The change log of this machine: when a routing change was made here, so the widget can measure what
the transcripts saved after it (tools/status.py, realized_savings). One JSON object per line, UTC to
the minute, in <CLAUDE_CONFIG_DIR or ~/.claude>/model-router/changes.jsonl: never in the repository.

  python3 tools/changes.py add <kind> <detail...> [--projected DOLLARS]   kinds: apply, revert, routing, mark
  python3 tools/changes.py list
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

import claude_home  # the one resolver of <CLAUDE_CONFIG_DIR or ~/.claude>

LOG = claude_home.config_dir() / 'model-router' / 'changes.jsonl'


def read():
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text(encoding='utf-8').splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return sorted(out, key=lambda e: e.get('at', ''))


def add(kind, detail, projected=None):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    e = {'at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'kind': kind, 'detail': detail}
    if projected is not None:
        e['projected'] = round(float(projected), 2)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(e) + '\n')
    return e


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=['add', 'list'])
    ap.add_argument('words', nargs='*')
    ap.add_argument('--projected', type=float, default=None)
    a = ap.parse_args()
    if a.verb == 'list':
        for e in read():
            print(f"{e['at']}  {e['kind']:8} {e['detail']}" + (f"  (projected ${e['projected']})" if e.get('projected') is not None else ''))
    elif len(a.words) < 2:
        sys.exit('add needs a kind and a detail')
    else:
        print(json.dumps(add(a.words[0], ' '.join(a.words[1:]), a.projected)))


if __name__ == '__main__':
    main()
