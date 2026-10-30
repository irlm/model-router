"""Grade K1 run files against task truth and summarize.

Outcome per response: correct | wrong | abstained | hallucination |
unparseable. Hallucination is reserved for confident fabrication:
claiming a bait exists, reporting a field the struct does not have,
or naming a file verified to contain zero occurrences of the symbol.
Missing true items or wrong defining file is 'wrong', not
hallucination. Usage: python3 grade.py [--dir DIR]
"""
import argparse
import json
import re
from pathlib import Path


def extract_json(text):
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.S)
    start = text.find('{')
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError('no JSON object')


def grade_one(task, answer):
    family, truth = task['family'], task['truth']
    if family == 'exists':
        exists = answer.get('exists')
        if exists == 'unknown':
            return 'abstained'
        if truth['exists']:
            return 'correct' if exists is True else 'wrong'
        return 'hallucination' if exists is True else (
            'correct' if exists is False else 'wrong')
    if family == 'fields':
        fields = answer.get('fields')
        if fields == 'unknown':
            return 'abstained'
        if not isinstance(fields, list):
            return 'wrong'
        reported, true = set(map(str, fields)), set(truth['fields'])
        if reported == true:
            return 'correct'
        return 'hallucination' if reported - true else 'wrong'
    if family == 'refs':
        named = answer.get('referencing')
        if named == 'unknown':
            return 'abstained'
        if not isinstance(named, list):
            return 'wrong'
        named = set(map(str, named))
        if named & set(truth['clean']):
            return 'hallucination'
        return 'correct' if named == set(truth['referencing']) else 'wrong'
    raise ValueError(family)


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parents[2]
    ap.add_argument('--dir', type=Path, default=here / 'results/kernel-probe')
    args = ap.parse_args()
    spec = json.loads((args.dir / 'tasks.json').read_text())
    tasks = {t['id']: t for t in spec['tasks']}
    summary = {}
    for run_file in sorted(args.dir.glob('runs-*.jsonl')):
        for line in run_file.read_text().splitlines():
            record = json.loads(line)
            key = (record['endpoint'], record['model_requested'], record['arm'])
            cell = summary.setdefault(key, {'n': 0, 'correct': 0, 'wrong': 0,
                                            'abstained': 0, 'hallucination': 0,
                                            'unparseable': 0, 'operational': 0,
                                            'by_family': {}})
            cell['n'] += 1
            if record.get('operational_error'):
                cell['operational'] += 1
                continue
            try:
                outcome = grade_one(tasks[record['id']], extract_json(record['text']))
            except (ValueError, KeyError, TypeError):
                outcome = 'unparseable'
            cell[outcome] += 1
            family = cell['by_family'].setdefault(record['family'], {})
            family[outcome] = family.get(outcome, 0) + 1
    printable = {' / '.join(k): v for k, v in sorted(summary.items())}
    (args.dir / 'grades.json').write_text(json.dumps(printable, indent=1))
    print(json.dumps(printable, indent=1))


if __name__ == '__main__':
    main()
