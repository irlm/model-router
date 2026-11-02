"""Grade K4 semantic runs (results/kernel-semantic/runs-*.jsonl).

Mechanical, no judge model. Outcomes match K1's vocabulary; two K4
subtags land in 'detail':
  callers — naming a candidate whose only occurrences are
  prototypes/definitions/comments is wrong with detail
  'lexical-confusion' (the overcount the packet invites); naming a
  zero-mention file is hallucination.
  dispatch — a non-truth answer is wrong if the named function occurs
  anywhere in the tree, hallucination if it does not.
"""
import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
import local  # noqa: E402

from grade import extract_json


def norm(path):
    return path.strip().lstrip('./')


def tree_has(tree, func):
    proc = subprocess.run(
        ['rg', '-l', '--fixed-strings', '--', func, '.'], cwd=tree,
        text=True, capture_output=True, stdin=subprocess.DEVNULL)
    return bool(proc.stdout.strip())


def grade_callers(task, answer):
    got = answer.get('calling')
    if got == 'unknown':
        return 'abstained', ''
    if not isinstance(got, list):
        return 'unparseable', 'calling is neither list nor unknown'
    got = {norm(p) for p in got if isinstance(p, str)}
    truth = set(task['truth']['calling'])
    if got == truth:
        return 'correct', ''
    sites = task['evidence']['sites']
    for p in sorted(got - truth):
        if p not in sites or not sites[p]:
            return 'hallucination', f'named zero-call-evidence file {p}'
        return 'wrong', f'lexical-confusion: {p} has only ' + ','.join(
            s['class'] for s in sites[p])
    return 'wrong', 'incomplete: missed ' + ','.join(sorted(truth - got))


def grade_dispatch(task, answer, tree):
    got = answer.get('function')
    if got == 'unknown':
        return 'abstained', ''
    if not isinstance(got, str):
        return 'unparseable', 'function is neither string nor unknown'
    got = got.strip().removesuffix('()').strip()
    if got == task['truth']['function']:
        return 'correct', ''
    if got and tree_has(tree, got):
        return 'wrong', f'existing but wrong function {got}'
    return 'hallucination', f'function {got!r} occurs nowhere in the tree'


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parents[2]
    ap.add_argument('--dir', type=Path,
                    default=here / 'results/kernel-semantic')
    args = ap.parse_args()
    spec = json.loads((args.dir / 'tasks.json').read_text())
    tree, tasks = local.resolve(spec['tree']), {t['id']: t for t in spec['tasks']}
    cells = defaultdict(lambda: defaultdict(int))
    details = []
    for runs in sorted(args.dir.glob('runs-*.jsonl')):
        for line in runs.read_text().splitlines():
            r = json.loads(line)
            cell = f"{r['endpoint']} / {r['model_requested']} / {r['arm']}"
            task = tasks[r['id']]
            if r.get('operational_error'):
                outcome, detail = 'operational', r['operational_error']
            else:
                try:
                    answer = extract_json(r['text'])
                    if task['family'] == 'callers':
                        outcome, detail = grade_callers(task, answer)
                    else:
                        outcome, detail = grade_dispatch(task, answer, tree)
                except (ValueError, json.JSONDecodeError) as e:
                    outcome, detail = 'unparseable', str(e)[:80]
            c = cells[cell]
            c['n'] += 1
            c[outcome] += 1
            key = task['family'] + (
                ':' + task['mechanism'] if task['family'] == 'dispatch' else '')
            c[f'{key} {outcome}'] += 1
            if detail.startswith('lexical-confusion'):
                c['lexical-confusion'] += 1
            details.append({'cell': cell, 'id': r['id'],
                            'outcome': outcome, 'detail': detail})
    out = {'cells': {k: dict(v) for k, v in sorted(cells.items())},
           'details': details}
    (args.dir / 'grades.json').write_text(json.dumps(out, indent=1))
    for cell, c in sorted(cells.items()):
        print(f"{cell:40s} n={c['n']:3d} correct={c['correct']:3d} "
              f"wrong={c['wrong']} abst={c['abstained']} "
              f"hall={c['hallucination']} lexconf={c['lexical-confusion']} "
              f"unp={c['unparseable']} op={c['operational']}")


if __name__ == '__main__':
    main()
