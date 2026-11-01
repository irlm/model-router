"""Grade every receipt and report per bench x model x effort x trial:
success rate, outcome breakdown, cost per success, tail cost, turns and time.
find_feature, browser_flow and own_app_flow are graded inline; fix_bug and
write_tests read the cached KUnit grades their grade.py wrote.

Cost is priced from the receipt's token counts with catalog/models.json
(catalog/price.py), so a price change is a catalog edit and a re-run of this
script, not a re-run of the tasks. `--prices FILE` prices everything under an
alternative catalog (what-if); `--cli-cost` uses the figure the CLI reported
instead. On every Anthropic receipt so far the two agree to the cent.

Usage: python3 report.py [--runs runs] [--out results/<cell>] [--prices FILE] [--cli-cost]
"""
import argparse
import importlib.util
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'bench/find_feature'))
import grade  # noqa: E402
import grade_semantic  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bf_grade = _load('bf_grade', 'bench/browser_flow/grade.py')
ds_grade = _load('ds_grade', 'bench/own_app_flow/grade.py')
price = _load('price', 'catalog/price.py')

FF_TASK_FILES = [HERE / 'bench/find_feature/tasks/lexical.json',
                 HERE / 'bench/find_feature/tasks/semantic.json']
SUCCESS = {'find_feature': {'correct'}, 'fix_bug': {'fixed'}, 'fix_bug_hard': {'fixed'},
           'write_tests': {'catches-bug'}, 'browser_flow': {'correct'}, 'own_app_flow': {'correct'},
           'repo_fix': {'fixed'}, 'repo_fix_pb': {'fixed'}, 'web_research': {'correct'}}
# Outcomes the harness caused, not the model's judgement (a lost browser tab, a CLI
# failure). In use these runs are retried; decide.py leaves them out of the rate.
NOT_MODEL = {'operational', 'incomplete'}
BF_TASKS = {t['id']: t for t in json.loads((HERE / 'bench/browser_flow/tasks.json').read_text())['tasks']}
_ds = HERE / 'bench/own_app_flow/tasks.json'
DS_TASKS = {t['id']: t for t in json.loads(_ds.read_text())['tasks']} if _ds.exists() else {}


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


def tokens_of(usage):
    u = usage or {}
    return {'input': u.get('input_tokens', 0) or 0, 'output': u.get('output_tokens', 0) or 0,
            'cache_read': u.get('cache_read_input_tokens', 0) or 0,
            'cache_write': u.get('cache_creation_input_tokens', 0) or 0}


def load_cells(runs_dir, cat=None, cli_cost=False):
    """Grade every receipt under runs_dir. Returns {(bench, model, effort, trial): [row]}."""
    tree, ff_tasks = load_ff_tasks()
    # benches graded by their own grade.py (a build, a test run, page fetches) cache the verdicts here
    cached = {d.name: json.loads((d / 'grades.json').read_text())
              for d in runs_dir.iterdir() if d.is_dir() and (d / 'grades.json').exists()}
    cells = defaultdict(list)
    files = sorted(runs_dir.glob('runs-*.jsonl')) + sorted(runs_dir.glob('*/runs-*.jsonl'))
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
            elif bench == 'browser_flow':
                outcome, detail = bf_grade.grade_one(BF_TASKS[r['id']], r)
                family = bench
            elif bench == 'own_app_flow':
                outcome, detail = ds_grade.grade_one(DS_TASKS[r['id']], r)
                family = bench
            else:
                key = f"{r['model_requested']} / {effort} / {r['trial']} / {r['id']}"
                g = cached.get(bench, {}).get(key)
                outcome, detail = (g['outcome'], g['detail']) if g else ('ungraded', '')
                family = bench
            cli = r.get('cost_usd')
            priced = None if cli_cost else price.price_record(r, cat)
            cells[(bench, r['model_requested'], effort, r['trial'])].append(
                {'id': r['id'], 'family': family, 'outcome': outcome, 'detail': detail,
                 'cost': priced if priced is not None else cli, 'cost_cli': cli,
                 'turns': r.get('num_turns'), 'wall': r.get('wall_seconds'),
                 'tokens': tokens_of(r.get('usage'))})
    return cells


def wilson(success, n, z=1.96):
    """95% Wilson score interval for a rate; (None, None) when nothing was judged."""
    if not n:
        return (None, None)
    p = success / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


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
    not_model = sum(1 for x in rows if x['outcome'] in NOT_MODEL)
    costs = [x['cost'] for x in rows if x['cost'] is not None]
    turns = [x['turns'] for x in rows if x['turns'] is not None]
    walls = [x['wall'] for x in rows if x['wall'] is not None]
    total = sum(costs) if costs else None
    tok = {k: statistics.mean(x['tokens'][k] for x in rows) for k in ('input', 'output', 'cache_read', 'cache_write')} if rows else {}
    return {'n': n, 'success': success, 'not_model': not_model, 'outcomes': dict(sorted(outcomes.items())),
            'ci': wilson(success, n - not_model),
            'cost_total': total,
            'cost_per_success': (total / success) if (total is not None and success) else None,
            'cost_mean': statistics.mean(costs) if costs else None,
            'cost_p90': pct(costs, 0.9), 'cost_max': max(costs) if costs else None,
            'turns_mean': statistics.mean(turns) if turns else None,
            'turns_max': max(turns) if turns else None,
            'wall_mean': statistics.mean(walls) if walls else None,
            'wall_total': sum(walls) if walls else None,
            'tokens_mean': tok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=Path, default=HERE / 'runs')
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--prices', type=Path, default=None, help='alternative catalog (what-if pricing)')
    ap.add_argument('--cli-cost', action='store_true', help="use the CLI's reported cost instead of catalog prices")
    args = ap.parse_args()
    cat = price.catalog(args.prices) if args.prices else None
    cells = load_cells(args.runs, cat, args.cli_cost)
    source = "the CLI's reported cost" if args.cli_cost else f"catalog prices ({args.prices or 'catalog/models.json'})"

    lines, out = [], {'cells': {}, 'by_family': {}, 'misses': [], 'price_source': source}
    lines.append(f'Cost column: {source}.\n')
    lines.append('## Per bench x model x effort x trial\n')
    lines.append('| Bench | Model | Effort | Trial | n | success | rate 95% CI | outcomes | cost total $ | cost / success $ | cost p90 $ | cost max $ | turns mean | turns max | wall mean s |')
    lines.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for key in sorted(cells):
        b, m, e, t = key
        s = summarize(cells[key], b)
        out['cells'][' / '.join(map(str, key))] = s
        oc = ', '.join(f'{k} {v}' for k, v in s['outcomes'].items())
        ci = '-' if s['ci'][0] is None else f"{s['ci'][0]:.2f}-{s['ci'][1]:.2f}"
        lines.append(f"| {b} | {m} | {e} | {t} | {s['n']} | {s['success']} | {ci} | {oc} | {fmt(s['cost_total'],2)} | {fmt(s['cost_per_success'],4)} | {fmt(s['cost_p90'],4)} | {fmt(s['cost_max'],4)} | {fmt(s['turns_mean'],1)} | {s['turns_max'] if s['turns_max'] is not None else '-'} | {fmt(s['wall_mean'],1)} |")
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
                out['misses'].append({'cell': key, **{k: v for k, v in x.items() if k != 'tokens'}})
                lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} | {x['id']} | {x['outcome']} | {str(x['detail'])[:120]} |")
    text = '\n'.join(lines) + '\n'
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / 'grades.json').write_text(json.dumps(out, indent=1, default=str))
        (args.out / 'tables.md').write_text(text)


if __name__ == '__main__':
    main()
