"""Grade repo_fix receipts in the grade worktree: seed the task's mutation,
apply the agent's patch, run the suite. Outcomes: fixed | still-failing |
compile-fail | touched-tests | no-change | abstained | operational. The detail
also says whether the type check (repos/<name>.json typecheck_cmd) passes on
the fixed tree. Cached in runs/<bench>/grades.json keyed
"model / effort[+variant] / trial / id".

Usage: python3 grade.py --repo <name> [--slot grade] [--bench repo_fix] [--only GLOB]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import repo as R  # noqa: E402


def typecheck(wt, cfg):
    if not cfg.get('typecheck_cmd'):
        return None
    p = subprocess.run(cfg['typecheck_cmd'], cwd=str(wt), capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
    return p.returncode == 0


def grade_one(wt, cfg, task, record):
    if record.get('operational_error'):
        return 'operational', record['operational_error']
    patch = record.get('patch') or ''
    text = (record.get('text') or '').strip()
    if not patch.strip():
        return ('abstained', '') if '"unknown"' in text else ('no-change', 'empty patch')
    touched = [p for p in record.get('changed_files', []) if R.is_test_path(p)]
    if touched:
        return 'touched-tests', ','.join(touched)
    R.reset(wt, cfg['base'])
    R.seed(wt, task)
    try:
        apply = subprocess.run(['git', '-C', str(wt), 'apply', '--whitespace=nowarn', '-'], input=patch, text=True, capture_output=True)
        if apply.returncode != 0:
            return 'compile-fail', 'patch does not apply: ' + apply.stderr[-200:]
        res = R.run_tests(wt, cfg)
        if not res['complete']:
            return 'compile-fail', 'no test report: ' + res.get('stderr_tail', '')[-200:]
        if res['crashed_files']:
            return 'compile-fail', 'suite crashed: ' + res['crashed_files'][0]['message'][:200]
        if res['failed'] == 0 and res['passed'] > 0:
            types = typecheck(wt, cfg)
            return 'fixed', '' if types is None else ('types ok' if types else 'tests pass but the type check fails')
        again = R.run_tests(wt, cfg)  # a failure must repeat: one flaky run under load is not a verdict
        if again['complete'] and again['failed'] == 0 and again['passed'] > 0:
            types = typecheck(wt, cfg)
            return 'fixed', ('flaky first run; ' + ('types ok' if types else 'tests pass but the type check fails')) if types is not None else 'flaky first run'
        names = sorted({f['name'] for f in res['failures']} & {f['name'] for f in again['failures']}) or sorted({f['name'] for f in res['failures']})
        return 'still-failing', f"{res['failed']} failed | {res['passed']} passed; {names[0][:90] if names else ''}"
    finally:
        R.reset(wt, cfg['base'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--slot', default='grade')
    ap.add_argument('--bench', default='repo_fix')
    ap.add_argument('--tasks', type=Path, default=HERE / 'tasks.json')
    ap.add_argument('--only', default='')
    ap.add_argument('--runs', type=Path, default=None, help='receipts and grades.json live here (default runs/<bench>)')
    args = ap.parse_args()
    cfg = R.load_repo(args.repo)
    wt = cfg['worktrees'] / args.slot
    tasks = {t['id']: t for t in json.loads(args.tasks.read_text())['tasks']}
    runs = args.runs or HERE.parents[1] / 'runs' / args.bench
    grades_path = runs / 'grades.json'
    grades = json.loads(grades_path.read_text()) if grades_path.exists() else {}
    for f in sorted(runs.glob(f'runs-*{args.only}*.jsonl')):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:  # a receipt still being written by a runner
                continue
            variant = r.get('variant', 'noexec')
            effort = r['effort'] + ('' if variant == 'noexec' else '+' + variant)
            key = f"{r['model_requested']} / {effort} / {r['trial']} / {r['id']}"
            if key in grades or r['id'] not in tasks:
                continue
            outcome, detail = grade_one(wt, cfg, tasks[r['id']], r)
            grades[key] = {'outcome': outcome, 'detail': detail, 'patch_lines': len((r.get('patch') or '').splitlines())}
            grades_path.write_text(json.dumps(grades, indent=1))
            print(key, '->', outcome, detail[:80], flush=True)


if __name__ == '__main__':
    main()
