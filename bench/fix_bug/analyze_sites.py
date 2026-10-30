"""For two-site (multi) hard tasks: which of the two seeded sites did each
agent patch actually restore? Seeds the task in the grading worktree, applies
the patch, and compares each site's function text with the pristine one.
Writes runs/fix_bug_hard/sites.json and prints a table.

Usage: python3 analyze_sites.py --worktree DIR [--runs DIR --tasks F]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import kunit_lab  # noqa: E402
import worktree as W  # noqa: E402


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worktree', type=Path, required=True)
    ap.add_argument('--runs', type=Path, default=HERE.parents[1] / 'runs/fix_bug_hard')
    ap.add_argument('--tasks', type=Path, default=HERE / 'tasks-hard.json')
    args = ap.parse_args()
    tasks = {t['id']: t for t in json.loads(args.tasks.read_text())['tasks']}
    grades = json.loads((args.runs / 'grades.json').read_text())
    out = {}
    for f in sorted(args.runs.glob('runs-*.jsonl')):
        for line in f.read_text().splitlines():
            r = json.loads(line)
            task = tasks[r['id']]
            if task['kind'] != 'multi':
                continue
            variant = r.get('variant', 'noexec')
            effort = r['effort'] + ('' if variant == 'noexec' else '+' + variant)
            key = f"{r['model_requested']} / {effort} / {r['trial']} / {r['id']}"
            W.reset(args.worktree)
            W.seed_mutation(args.worktree, task)
            applied = subprocess.run(['git', '-C', str(args.worktree), 'apply', '--whitespace=nowarn', '-'],
                                     input=r.get('patch') or '', text=True, capture_output=True).returncode == 0
            restored = []
            for site in task['sites']:
                text = (args.worktree / site['file']).read_text()
                span = kunit_lab.function_span(text, site['function'])
                now = text[span[0]:span[1]] if span else ''
                restored.append(norm(now) == norm(site['original_function']))
            W.reset(args.worktree)
            touched = [any(s['file'] in p for p in r.get('changed_files', [])) for s in task['sites']]
            out[key] = {'outcome': grades.get(key, {}).get('outcome'), 'applied': applied,
                        'restored': restored, 'files_touched': touched,
                        'summary': (r.get('text') or '')[:200]}
            print(f"{key:95} {out[key]['outcome']:14} restored={restored}", flush=True)
    (args.runs / 'sites.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
