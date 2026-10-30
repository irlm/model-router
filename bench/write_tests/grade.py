"""Grade write-tests receipts in the grade-tests worktree:
  1. wiring + the agent's lib/agent_kunit.c on the pristine function -> the
     suite must build and pass with at least one test case;
  2. then seed the hidden K2 mutation of that function -> the suite must fail.
Outcomes: catches-bug | misses-bug | fails-on-correct-code | compile-fail |
empty-suite | touched-other-files | abstained | operational.
Grades cached in runs/write_tests/grades.json.

Usage: python3 grade.py --worktree DIR --build-dir DIR [--only GLOB]
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
sys.path.insert(0, str(HERE))
import worktree as W  # noqa: E402
import wiring  # noqa: E402

KUNITCONFIG = HERE / 'kunitconfig'
TOTAL_RE = re.compile(r'# (\S+): pass:(\d+) fail:(\d+) skip:(\d+) total:(\d+)')


def suite_totals(output):
    """{suite: (pass, fail, skip, total)} from kunit.py output."""
    return {m.group(1): tuple(int(x) for x in m.groups()[1:]) for m in TOTAL_RE.finditer(output)}


def grade_one(wt, build_dir, task, record):
    if record.get('operational_error'):
        return 'operational', record['operational_error']
    other = [p for p in record.get('changed_files', []) if p != 'lib/agent_kunit.c']
    if other:
        return 'touched-other-files', ','.join(other)
    test_file = record.get('test_file') or ''
    if 'KUNIT_CASE' not in test_file:
        return ('abstained', '') if '"unknown"' in (record.get('text') or '') else ('empty-suite', 'no KUNIT_CASE')
    W.reset(wt)
    try:
        wiring.apply(wt)
        (Path(wt) / 'lib/agent_kunit.c').write_text(test_file)
        clean = W.run_suite(wt, build_dir, KUNITCONFIG)
        totals = suite_totals(clean['output'])
        ran = sum(t[3] for t in totals.values())
        if not clean['passed']:
            if totals and any(t[1] for t in totals.values()):
                return 'fails-on-correct-code', json.dumps(totals)
            return 'compile-fail', clean['output_tail'][-400:]
        if ran == 0:
            return 'empty-suite', 'built but ran 0 cases'
        W.seed_mutation(wt, task)
        buggy = W.run_suite(wt, build_dir, KUNITCONFIG)
        btot = suite_totals(buggy['output'])
        if not buggy['passed'] and any(t[1] for t in btot.values()):
            return 'catches-bug', f'cases={ran} failing_on_bug={sum(t[1] for t in btot.values())}'
        if not buggy['passed']:
            return 'catches-bug', f'cases={ran} (suite crashed on bug: {buggy["output_tail"][-120:]!r})'
        return 'misses-bug', f'cases={ran}'
    finally:
        W.reset(wt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worktree', type=Path, required=True)
    ap.add_argument('--build-dir', type=Path, required=True)
    ap.add_argument('--runs', type=Path, default=HERE.parents[1] / 'runs/write_tests')
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
            cases = len(re.findall(r'KUNIT_CASE\w*\(', r.get('test_file') or ''))
            grades[key] = {'outcome': outcome, 'detail': detail, 'kunit_cases': cases,
                           'test_bytes': len(r.get('test_file') or '')}
            grades_path.write_text(json.dumps(grades, indent=1))
            print(key, '->', outcome, detail[:100], flush=True)


if __name__ == '__main__':
    main()
