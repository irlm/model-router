#!/usr/bin/env python3
"""Monthly usage ledger: what this machine actually ran, from the local Claude
Code transcripts (tools/usage_scan.py): subagent calls by type, tokens and
catalog-priced cost by model. Writes ledger/usage-<date>.md; with --commit it
also commits and pushes it. Python so it runs on Linux, macOS and Windows;
tools/ledger.sh wraps it for the systemd timer.

Usage: python3 tools/ledger.py [--commit]
"""
import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def claude_version():
    exe = shutil.which('claude')
    if not exe:
        return 'not found'
    try:
        return subprocess.run([exe, '--version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30).stdout.strip().splitlines()[0]
    except (OSError, IndexError, subprocess.TimeoutExpired):
        return 'unknown'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', action='store_true', help='git add, commit and push the entry')
    args = ap.parse_args()
    today = datetime.date.today().isoformat()
    (HERE / 'ledger').mkdir(exist_ok=True)
    out = HERE / f'ledger/usage-{today}.md'
    scan = subprocess.run([sys.executable, str(HERE / 'tools/usage_scan.py')], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=HERE)
    if scan.returncode != 0:
        sys.exit(f'usage_scan failed:\n{scan.stderr}')
    window = subprocess.run([sys.executable, str(HERE / 'tools/consumption.py')], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=HERE)
    out.write_text(f"# Usage ledger, {today}\n\nClaude Code {claude_version()}. Catalog-equivalent prices (catalog/models.json); "
                   "on a subscription they measure rate-limit headroom, not a bill.\n\n```\n" + scan.stdout + "```\n\n"
                   "## Last 30 days by model and effort\n\n```\n" + (window.stdout if window.returncode == 0 else window.stderr) + "```\n", encoding='utf-8')
    print(f'wrote {out.relative_to(HERE)}')
    if args.commit:
        git = shutil.which('git') or 'git'
        subprocess.run([git, 'add', str(out)], cwd=HERE, check=True)
        c = subprocess.run([git, 'commit', '-qm', f'ledger: usage {today}'], cwd=HERE, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if c.returncode != 0:
            print('nothing new to commit' if 'nothing to commit' in c.stdout + c.stderr else c.stderr.strip())
            return
        subprocess.run([git, 'push', '-q'], cwd=HERE, check=True)
        print('committed')


if __name__ == '__main__':
    main()
