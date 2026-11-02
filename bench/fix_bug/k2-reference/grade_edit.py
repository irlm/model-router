"""Grade K2 responses by actually building and running KUnit.

Per response: write the mutated file, splice the model's function
over the mutated span, build + run the paired suite, restore the
pristine file. Outcomes: fixed | still-failing | compile-or-boot-fail
| abstained | unparseable | operational. The splice guarantees the
model's edit touches only the target function.
Usage: python3 grade_edit.py [--dir DIR] [--only ENDPOINT-GLOB]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'common'))
import local  # noqa: E402
import kunit_lab
from run_edit import extract_function


def grade_response(tree, task, text):
    function = extract_function(text or '')
    if function == 'unknown':
        return 'abstained'
    if not function:
        return 'unparseable'
    file = Path(tree) / task['file']
    pristine = file.read_text()
    span = kunit_lab.function_span(pristine, task['function'])
    mutated_file = (pristine[:span[0]] + task['mutated_function']
                    + pristine[span[1]:])
    file.write_text(mutated_file)
    try:
        if kunit_lab.splice_function(tree, task['file'], task['function'],
                                     function) is None:
            return 'unparseable'
        result = kunit_lab.run_suite(tree, task['suite'])
        if result['passed']:
            return 'fixed'
        tail = result['output_tail']
        if '[FAILED]' in tail or '[PASSED]' in tail:
            return 'still-failing'
        return 'compile-or-boot-fail'
    finally:
        file.write_text(pristine)


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parents[2]
    ap.add_argument('--dir', type=Path, default=here / 'results/kernel-edit')
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    spec = json.loads((args.dir / 'tasks.json').read_text())
    tasks = {t['id']: t for t in spec['tasks']}
    graded_path = args.dir / 'grades.json'
    graded = json.loads(graded_path.read_text()) if graded_path.exists() else {}
    for run_file in sorted(args.dir.glob(f'runs-*{args.only}*.jsonl')):
        for line in run_file.read_text().splitlines():
            r = json.loads(line)
            key = f"{r['endpoint']} / {r['model_requested']} / {r['arm']} / {r['id']}"
            if key in graded:
                continue
            if r.get('operational_error'):
                graded[key] = 'operational'
            else:
                graded[key] = grade_response(local.resolve(spec['tree']), tasks[r['id']],
                                             r['text'])
            print(key, '->', graded[key], flush=True)
            graded_path.write_text(json.dumps(graded, indent=1))
    summary = {}
    for key, outcome in graded.items():
        cell = ' / '.join(key.split(' / ')[:3])
        summary.setdefault(cell, {}).setdefault(outcome, 0)
        summary[cell][outcome] += 1
    (args.dir / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
