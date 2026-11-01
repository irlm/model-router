#!/usr/bin/env python3
"""Re-check the routing on this machine: regress.py on every decided family whose
fixtures exist here (tools/status.py says which), then commit and push the new
ledger/regress-*.md with its receipts. This is what /router update runs.

Refuses to start when the checkout is behind origin (the push would fail);
pull first. --plan prints what would run and stops.

Usage: python3 tools/update.py [--sample 6] [--families a,b] [--plan] [--no-commit]
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / 'tools'))
import status  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=6)
    ap.add_argument('--families', default='', help='comma list; default: every decided family that can run here')
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--no-commit', action='store_true')
    args = ap.parse_args()
    s = status.collect(fetch=True)
    if not s['claude']:
        sys.exit('claude CLI not found on PATH')
    if s['repo'].get('behind'):
        sys.exit(f"checkout is {s['repo']['behind']} commit(s) behind origin: pull first (/router pull)")
    fams = [f.strip() for f in args.families.split(',') if f.strip()] or [f['name'] for f in s['families'] if f['can_run']]
    skipped = [(f['name'], f['why']) for f in s['families'] if not f['can_run'] and f['status'] == 'decided']
    print(f"Claude Code {s['claude']} on {s['platform']} ({s['host']}); last check {(s['ledger']['regress_last'] or {}).get('date')} "
          f"on {(s['ledger']['regress_last'] or {}).get('claude')}")
    print('families here:', ', '.join(fams) or 'none')
    for name, why in skipped:
        print(f'  skip {name}: {why}')
    if not fams:
        sys.exit('nothing can run on this machine')
    if args.plan:
        return
    t0 = time.time()
    cmd = [sys.executable, str(HERE / 'regress.py'), '--families', ','.join(fams), '--sample', str(args.sample)]
    print('run', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=HERE)
    new = [p for p in HERE.glob('ledger/regress-*.md') if p.stat().st_mtime >= t0]
    if r.returncode != 0 or not new:
        sys.exit(f'regress.py exit {r.returncode}, new entries: {[p.name for p in new]}')
    entry = new[-1]
    print()
    print(entry.read_text())
    if args.no_commit:
        return
    git = shutil.which('git') or 'git'
    subprocess.run([git, 'add', 'ledger', 'runs/regress'], cwd=HERE, check=True)
    c = subprocess.run([git, 'commit', '-qm', f'regress: {entry.stem[len("regress-"):]}'], cwd=HERE, capture_output=True, text=True)
    if c.returncode != 0:
        print('nothing new to commit' if 'nothing to commit' in c.stdout + c.stderr else c.stderr.strip())
        return
    subprocess.run([git, 'push', '-q'], cwd=HERE, check=True)
    print(f'committed and pushed {entry.name}')


if __name__ == '__main__':
    main()
