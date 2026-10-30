"""Grade every receipt and report per bench x model x effort x trial:
success rate, outcome breakdown, API-equivalent cost per success, tail cost,
turns and time. find_feature is graded inline (string-verified truth);
fix_bug and write_tests read the cached KUnit grades their grade.py wrote.

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
import grade  # noqa: E402
import grade_semantic  # noqa: E402

FF_TASK_FILES = [HERE / 'bench/find_feature/tasks/lexical.json',
                 HERE / 'bench/find_feature/tasks/semantic.json']
SUCCESS = {'find_feature': {'correct'}, 'fix_bug': {'fixed'}, 'write_tests': {'catches-bug'}}


def load_ff_tasks():
    tree, tasks = None, {}
    for f in FF_TASK_FILES:
        spec = json.loads(f.read_text())
        tree = tree or spec['tree']
        tasks.update({t['id']: t for t in spec['tasks']})
    return tree, tasks


def grade_ff(task, record, tree):
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
    return s[max(0, min(len(s) - 1, round(p * (len(s) - 1))))]


def fmt(x, nd=3):
    return '-' if x is None else f'{x:.{nd}f}'


def summarize(rows, bench):
    n = len(rows)
    outcomes = defaultdict(int)
    for x in rows:
        outcomes[x['outcome']] += 1
    success = sum(1 for x in rows if x['outcome'] in SUCCESS[bench])
    costs = [x['cost'] for x in rows if x['cost'] is not None]
    turns = [x['turns'] for x in rows if x['turns'] is not None]
    walls = [x['wall'] for x in rows if x['wall'] is not None]
    total = sum(costs) if costs else None
    return {'n': n, 'success': success, 'outcomes': dict(sorted(outcomes.items())),
            'cost_total': total,
            'cost_per_success': (total / success) if (total is not None and success) else None,
            'cost_mean': statistics.mean(costs) if costs else None,
            'cost_p90': pct(costs, 0.9), 'cost_max': max(costs) if costs else None,
            'turns_mean': statistics.mean(turns) if turns else None,
            'turns_max': max(turns) if turns else None,
            'wall_mean': statistics.mean(walls) if walls else None,
            'wall_total': sum(walls) if walls else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, default=HERE / 'runs')
    ap.add_argument('--out', type=Path, default=None)
    args = ap.parse_args()
    tree, ff_tasks = load_ff_tasks()
    cached = {}
    for bench in ('fix_bug', 'write_tests'):
        gp = args.runs / bench / 'grades.json'
        cached[bench] = json.loads(gp.read_text()) if gp.exists() else {}
    cells = defaultdict(list)
    files = sorted(args.runs.glob('runs-*.jsonl')) + sorted(args.runs.glob('*/runs-*.jsonl'))
    for f in files:
        if 'smoke' in f.parts:
            continue
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            bench = r.get('bench', 'find_feature')
            variant = r.get('variant', 'noexec')
            effort = r['effort'] + ('' if variant == 'noexec' else '+' + variant)
            if bench == 'find_feature':
                outcome, detail = grade_ff(ff_tasks[r['id']], r, tree)
                family = ff_tasks[r['id']]['family']
            else:
                key = f"{r['model_requested']} / {effort} / {r['trial']} / {r['id']}"
                g = cached[bench].get(key)
                outcome, detail = (g['outcome'], g['detail']) if g else ('ungraded', '')
                family = bench
            cells[(bench, r['model_requested'], effort, r['trial'])].append(
                {'id': r['id'], 'family': family, 'outcome': outcome, 'detail': detail,
                 'cost': r.get('cost_usd'), 'turns': r.get('num_turns'),
                 'wall': r.get('wall_seconds')})

    lines, out = [], {'cells': {}, 'by_family': {}, 'misses': []}
    lines.append('## Per bench x model x effort x trial\n')
    lines.append('| Bench | Model | Effort | Trial | n | success | outcomes | cost total $ | cost / success $ | cost p90 $ | cost max $ | turns mean | turns max | wall mean s |')
    lines.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for key in sorted(cells):
        b, m, e, t = key
        s = summarize(cells[key], b)
        out['cells'][' / '.join(map(str, key))] = s
        oc = ', '.join(f'{k} {v}' for k, v in s['outcomes'].items())
        lines.append(f"| {b} | {m} | {e} | {t} | {s['n']} | {s['success']} | {oc} | {fmt(s['cost_total'],2)} | {fmt(s['cost_per_success'],4)} | {fmt(s['cost_p90'],4)} | {fmt(s['cost_max'],4)} | {fmt(s['turns_mean'],1)} | {s['turns_max'] if s['turns_max'] is not None else '-'} | {fmt(s['wall_mean'],1)} |")
    lines.append('\n## find_feature per family\n')
    lines.append('| Model | Effort | Trial | Family | n | correct | outcomes | cost / correct $ | turns mean | wall mean s |')
    lines.append('|---|---|---|---|---|---|---|---|---|---|')
    for key in sorted(cells):
        if key[0] != 'find_feature':
            continue
        fams = defaultdict(list)
        for x in cells[key]:
            fams[x['family']].append(x)
        for fam in sorted(fams):
            s = summarize(fams[fam], 'find_feature')
            out['by_family'][' / '.join(map(str, key)) + ' / ' + fam] = s
            oc = ', '.join(f'{k} {v}' for k, v in s['outcomes'].items())
            lines.append(f"| {key[1]} | {key[2]} | {key[3]} | {fam} | {s['n']} | {s['success']} | {oc} | {fmt(s['cost_per_success'],4)} | {fmt(s['turns_mean'],1)} | {fmt(s['wall_mean'],1)} |")
    lines.append('\n## Every non-success response\n')
    lines.append('| Bench | Model | Effort | Trial | Task | Outcome | Detail |')
    lines.append('|---|---|---|---|---|---|---|')
    for key in sorted(cells):
        for x in cells[key]:
            if x['outcome'] not in SUCCESS[key[0]]:
                out['misses'].append({'cell': key, **x})
                lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} | {x['id']} | {x['outcome']} | {str(x['detail'])[:120]} |")
    text = '\n'.join(lines) + '\n'
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / 'grades.json').write_text(json.dumps(out, indent=1, default=str))
        (args.out / 'tables.md').write_text(text)


if __name__ == '__main__':
    main()
