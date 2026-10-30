"""Grade bug-fix receipts by building and running the paired KUnit suite in
the grade-fix worktree: seed the mutation, apply the agent's patch, run.
Outcomes: fixed | still-failing | compile-or-boot-fail | touched-tests |
no-change | abstained | operational. Grades are cached in
runs/fix_bug/grades.json keyed "model / effort / trial / id".

Usage: python3 grade.py --worktree DIR --build-dir DIR [--only GLOB]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import worktree as W  # noqa: E402

KUNITCONFIG = HERE / 'kunitconfig'


def grade_one(wt, build_dir, task, record):
    if record.get('operational_error'):
        return 'operational', record['operational_error']
    patch = record.get('patch') or ''
    text = (record.get('text') or '').strip()
    if not patch.strip():
        return ('abstained', '') if '"unknown"' in text else ('no-change', 'empty patch')
    touched = [p for p in record.get('changed_files', []) if W.is_test_path(p)]
    if touched:
        return 'touched-tests', ','.join(touched)
    W.reset(wt)
    W.seed_mutation(wt, task)
    try:
        apply = subprocess.run(['git', '-C', str(wt), 'apply', '--whitespace=nowarn', '-'],
                               input=patch, text=True, capture_output=True)
        if apply.returncode != 0:
            return 'compile-or-boot-fail', 'patch does not apply: ' + apply.stderr[-200:]
        result = W.run_suite(wt, build_dir, KUNITCONFIG, task['suite'])
        if result['passed']:
            return 'fixed', ''
        tail = result['output_tail']
        if '[FAILED]' in tail or '[PASSED]' in tail:
            return 'still-failing', ''
        return 'compile-or-boot-fail', tail[-300:]
    finally:
        W.reset(wt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worktree', type=Path, required=True)
    ap.add_argument('--build-dir', type=Path, required=True)
    ap.add_argument('--runs', type=Path, default=HERE.parents[1] / 'runs/fix_bug')
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    tasks = {t['id']: t for t in json.loads((HERE / 'tasks.json').read_text())['tasks']}
    grades_path = args.runs / 'grades.json'
    grades = json.loads(grades_path.read_text()) if grades_path.exists() else {}
    for f in sorted(args.runs.glob(f'runs-*{args.only}*.jsonl')):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            key = f"{r['model_requested']} / {r['effort']} / {r['trial']} / {r['id']}"
            if key in grades:
                continue
            outcome, detail = grade_one(args.worktree, args.build_dir, tasks[r['id']], r)
            grades[key] = {'outcome': outcome, 'detail': detail,
                           'patch_lines': len((r.get('patch') or '').splitlines())}
            grades_path.write_text(json.dumps(grades, indent=1))
            print(key, '->', outcome, detail[:80], flush=True)


if __name__ == '__main__':
    main()
