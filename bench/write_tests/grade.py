"""Grade write-tests receipts in the grade-tests worktree:
  1. wiring + the agent's lib/agent_kunit.c on the pristine function -> the
     suite must build and pass with at least one test case;
  2. then seed the hidden K2 mutation of that function -> the suite must fail.
Outcomes: catches-bug | misses-bug | fails-on-correct-code | compile-fail |
empty-suite | touched-other-files | abstained | operational.
Totals are parsed from kunit.py's 'Testing complete. Ran N tests: ...' line,
which is printed whether or not anything failed.
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
SUMMARY_RE = re.compile(r'Testing complete\. Ran (\d+) tests?:([^\n]*)')


def run_totals(output):
    """(passed, failed, skipped, total) from kunit.py's summary line.
    'failed' includes crashed cases. (0, 0, 0, 0) when nothing ran."""
    m = SUMMARY_RE.search(output)
    if not m:
        return (0, 0, 0, 0)
    total = int(m.group(1))
    parts = dict(re.findall(r'(passed|failed|crashed|skipped): (\d+)', m.group(2)))
    return (int(parts.get('passed', 0)),
            int(parts.get('failed', 0)) + int(parts.get('crashed', 0)),
            int(parts.get('skipped', 0)), total)


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
        c_pass, c_fail, c_skip, ran = run_totals(clean['output'])
        if ran == 0:
            if not clean['passed'] and ('error' in clean['output_tail'].lower()
                                        and '0 tests run' not in clean['output_tail']):
                errors = [l.strip() for l in clean['output'].splitlines() if 'error:' in l][:3]
                return 'compile-fail', ' | '.join(errors)[:400] or clean['output_tail'][-400:]
            return 'empty-suite', 'built but ran 0 cases'
        if c_fail:
            # Not deliverable as written, but record whether the suite
            # still has bug-detecting power: more failures on the bug.
            W.seed_mutation(wt, task)
            buggy = W.run_suite(wt, build_dir, KUNITCONFIG)
            b_fail = run_totals(buggy['output'])[1]
            return 'fails-on-correct-code', (f'cases={ran} clean_fail={c_fail} '
                                             f'bug_fail={b_fail} detects={b_fail > c_fail}')
        if not clean['passed']:
            errors = [l.strip() for l in clean['output'].splitlines() if 'error:' in l][:3]
            return 'compile-fail', ' | '.join(errors)[:400] or clean['output_tail'][-400:]
        W.seed_mutation(wt, task)
        buggy = W.run_suite(wt, build_dir, KUNITCONFIG)
        b_pass, b_fail, b_skip, b_ran = run_totals(buggy['output'])
        if b_fail:
            return 'catches-bug', f'cases={ran} failing_on_bug={b_fail}'
        if not buggy['passed']:
            return 'catches-bug', f'cases={ran} (kernel crashed on bug: {buggy["output_tail"][-120:]!r})'
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
            variant = r.get('variant', 'noexec')
            label = r['effort'] + ('' if variant == 'noexec' else '+' + variant)
            key = f"{r['model_requested']} / {label} / {r['trial']} / {r['id']}"
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
