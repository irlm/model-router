"""Grade every receipt in runs/ and report, per model x effort x trial:
outcomes, API-equivalent cost per correct task, tail cost, turns, time.

Usage: python3 report.py [--runs runs] [--out results/<cell>]
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'bench/find_feature'))
import grade  # noqa: E402  (grade_one, extract_json)
import grade_semantic  # noqa: E402  (grade_callers, grade_dispatch)

TASK_FILES = [HERE / 'bench/find_feature/tasks/lexical.json',
              HERE / 'bench/find_feature/tasks/semantic.json']


def load_tasks():
    tree, tasks = None, {}
    for f in TASK_FILES:
        spec = json.loads(f.read_text())
        tree = tree or spec['tree']
        tasks.update({t['id']: t for t in spec['tasks']})
    return tree, tasks


def outcome_for(task, record, tree):
    if record.get('operational_error'):
        return 'operational', record['operational_error']
    try:
        answer = grade.extract_json(record['text'])
    except (ValueError, json.JSONDecodeError) as e:
        return 'unparseable', str(e)[:80]
    fam = task['family']
    try:
        if fam == 'callers':
            return grade_semantic.grade_callers(task, answer)
        if fam == 'dispatch':
            return grade_semantic.grade_dispatch(task, answer, tree)
        return grade.grade_one(task, answer), ''
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        return 'unparseable', str(e)[:80]


def pct(values, p):
    if not values:
        return None
    s = sorted(values)
    k = max(0, min(len(s) - 1, round(p * (len(s) - 1))))
    return s[k]


def fmt(x, nd=3):
    return '-' if x is None else f'{x:.{nd}f}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, default=HERE / 'runs')
    ap.add_argument('--out', type=Path, default=None)
    args = ap.parse_args()
    tree, tasks = load_tasks()
    cells = defaultdict(list)
    for f in sorted(args.runs.glob('runs-*.jsonl')):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            task = tasks[r['id']]
            outcome, detail = outcome_for(task, r, tree)
            cells[(r['model_requested'], r['effort'], r['trial'])].append(
                {'id': r['id'], 'family': task['family'], 'outcome': outcome,
                 'detail': detail, 'cost': r.get('cost_usd'),
                 'turns': r.get('num_turns'), 'wall': r.get('wall_seconds'),
                 'model_used': r.get('model_used')})

    def summarize(rows):
        n = len(rows)
        counts = {k: sum(1 for x in rows if x['outcome'] == k)
                  for k in ('correct', 'wrong', 'abstained', 'hallucination',
                            'unparseable', 'operational')}
        costs = [x['cost'] for x in rows if x['cost'] is not None]
        turns = [x['turns'] for x in rows if x['turns'] is not None]
        walls = [x['wall'] for x in rows if x['wall'] is not None]
        total = sum(costs) if costs else None
        cpc = (total / counts['correct']) if (total is not None and counts['correct']) else None
        return {'n': n, **counts, 'cost_total': total,
                'cost_per_correct': cpc,
                'cost_mean': statistics.mean(costs) if costs else None,
                'cost_p90': pct(costs, 0.9), 'cost_max': max(costs) if costs else None,
                'turns_mean': statistics.mean(turns) if turns else None,
                'turns_max': max(turns) if turns else None,
                'wall_mean': statistics.mean(walls) if walls else None,
                'wall_total': sum(walls) if walls else None}

    lines = []
    lines.append('## Overall, per model x effort x trial\n')
    lines.append('| Model | Effort | Trial | n | correct | wrong | abst | hall | unp | op | cost total $ | cost / correct $ | cost p90 $ | cost max $ | turns mean | turns max | wall mean s | wall total s |')
    lines.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    out = {'cells': {}, 'by_family': {}, 'misses': []}
    for key in sorted(cells):
        s = summarize(cells[key])
        out['cells'][' / '.join(map(str, key))] = s
        m, e, t = key
        lines.append(f"| {m} | {e} | {t} | {s['n']} | {s['correct']} | {s['wrong']} | {s['abstained']} | {s['hallucination']} | {s['unparseable']} | {s['operational']} | {fmt(s['cost_total'],2)} | {fmt(s['cost_per_correct'],4)} | {fmt(s['cost_p90'],4)} | {fmt(s['cost_max'],4)} | {fmt(s['turns_mean'],1)} | {s['turns_max'] if s['turns_max'] is not None else '-'} | {fmt(s['wall_mean'],1)} | {fmt(s['wall_total'],0)} |")
    lines.append('\n## Per family\n')
    lines.append('| Model | Effort | Trial | Family | n | correct | wrong | abst | hall | unp | op | cost / correct $ | cost p90 $ | turns mean | wall mean s |')
    lines.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for key in sorted(cells):
        fams = defaultdict(list)
        for x in cells[key]:
            fams[x['family']].append(x)
        for fam in sorted(fams):
            s = summarize(fams[fam])
            out['by_family'][' / '.join(map(str, key)) + ' / ' + fam] = s
            m, e, t = key
            lines.append(f"| {m} | {e} | {t} | {fam} | {s['n']} | {s['correct']} | {s['wrong']} | {s['abstained']} | {s['hallucination']} | {s['unparseable']} | {s['operational']} | {fmt(s['cost_per_correct'],4)} | {fmt(s['cost_p90'],4)} | {fmt(s['turns_mean'],1)} | {fmt(s['wall_mean'],1)} |")
    lines.append('\n## Every non-correct response\n')
    lines.append('| Model | Effort | Trial | Task | Outcome | Detail |')
    lines.append('|---|---|---|---|---|---|')
    for key in sorted(cells):
        for x in cells[key]:
            if x['outcome'] != 'correct':
                out['misses'].append({'cell': key, **x})
                m, e, t = key
                lines.append(f"| {m} | {e} | {t} | {x['id']} | {x['outcome']} | {x['detail']} |")
    text = '\n'.join(lines) + '\n'
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / 'grades.json').write_text(json.dumps(out, indent=1, default=str))
        (args.out / 'tables.md').write_text(text)


if __name__ == '__main__':
    main()
