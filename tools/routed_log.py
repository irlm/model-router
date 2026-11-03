"""What the router did on this machine, one line per rewritten Agent call, in
<CLAUDE_CONFIG_DIR or ~/.claude>/model-router/routed.jsonl (never in the repository). The widget appends;
tools/status.py reads it for the weekly slots and the routed count of the window.

  python3 tools/routed_log.py add <family> <agent> <from> <to> <decision> [--project KEY]
  python3 tools/routed_log.py list [--days 30]
"""
import argparse
import datetime
import json
import os
from pathlib import Path

LOG = Path(os.environ.get('CLAUDE_CONFIG_DIR') or (Path.home() / '.claude')) / 'model-router' / 'routed.jsonl'


def read(days=None):
    if not LOG.exists():
        return []
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M') if days else ''
    out = []
    for line in LOG.read_text(encoding='utf-8').splitlines():
        if line.strip():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get('at', '') >= cutoff:
                out.append(e)
    return out


def add(family, agent, src, dst, decision, project=''):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    e = {'at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'family': family, 'agent': agent,
         'from': src, 'to': dst, 'decision': decision, 'project': project}
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(e) + '\n')
    return e


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=['add', 'list'])
    ap.add_argument('words', nargs='*')
    ap.add_argument('--project', default='')
    ap.add_argument('--days', type=int, default=30)
    a = ap.parse_args()
    if a.verb == 'list':
        for e in read(a.days):
            print(f"{e['at']}  {e['family']:18} {e['agent']}: {e['from']} -> {e['to']}  {e['decision']}  {e.get('project', '')}")
    else:
        if len(a.words) != 5:
            raise SystemExit('add needs: <family> <agent> <from> <to> <decision>')
        print(json.dumps(add(*a.words, project=a.project)))


if __name__ == '__main__':
    main()
