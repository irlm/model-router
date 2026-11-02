"""Turn the receipts into the routing decision, per family, by one fixed rule.

For each routing family (a set of benches that measure the same kind of work):
  1. candidates are (model, effort[+variant]) cells with receipts for every bench
     of the family and at least --min-trials trials in each;
  2. rate = successes / (runs - runs the harness lost), because a lost browser
     tab or a CLI failure is retried in use, not judged (report.NOT_MODEL);
  3. the bar is the best candidate's score minus --margin (default 0.02, about one
     task in fifty). --rule lower (default): the score is the lower bound of the
     95% Wilson interval of the rate, so thin evidence cannot win a family (10/10
     scores 0.72, 63/63 scores 0.94) and a cheap model earns the default with
     trials, not luck. --rule point: the score is the rate itself (routing v1);
  4. the default is the cheapest candidate at or above the bar by cost per
     success (catalog prices, catalog/price.py); ties go to the faster one.
     The step-up is the next cheapest candidate above the bar with a higher rate.
The table also shows pass^k (Anthropic's consistency figure): the chance that
all k trials of a task succeed, estimated per task as C(c,k)/C(n,k) over its n
judged runs with c successes, averaged over tasks, with k = the fewest judged
runs any task has in the cell (1 when there is a single trial: then it is the rate).
It also writes a plan for models in the catalog that have no receipts: which
families are worth running (a new model can only win a family by being cheaper
than the current default, so it is run only where its price is lower, cheapest
family first), with the expected cost from the family's mean token counts.

Writes families[*].default / step_up / decided into routing.json and the
decision table into ROUTING.md between <!-- decide:start --> and
<!-- decide:end -->. `--dry-run` prints without writing.

Usage: python3 decide.py [--dry-run] [--margin 0.02] [--min-trials 1] [--rule lower|point] [--prices FILE]
"""
import argparse
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

import report

HERE = Path(__file__).resolve().parent
FAMILIES = {
    'find_feature': {'benches': ['find_feature'], 'what': 'find a feature in a huge codebase'},
    'fix_bug': {'benches': ['fix_bug_hard'], 'what': 'fix a bug with a failing test (hard tier decides; the easy tier is saturated on every tier)'},
    'write_tests': {'benches': ['write_tests'], 'what': 'write tests for a function'},
    'browser_flow': {'benches': ['browser_flow', 'own_app_flow'], 'what': 'drive a web page through a checklist in a real browser'},
    'repo_fix': {'benches': ['repo_fix'], 'what': "fix a bug with a failing test in a repository of the user's own (TypeScript with vitest when measured)"},
    'web_research': {'benches': ['web_research'], 'what': 'look up a technical fact on the web and cite a page that states it'},
    'research_synthesis': {'benches': ['research_synthesis'], 'what': 'write a short research note answering three looked-up questions, each claim with the page that states it'},
}
ALIAS = {'claude-haiku-5-5': 'haiku', 'claude-sonnet-5-5': 'sonnet', 'claude-opus-5-5': 'opus', 'claude-fable-5-1': 'fable'}
HARNESS_FOR = {'anthropic': 'claude', 'openai': 'codex'}  # provider -> adapter in bench/common/harness.py
REQUIRES = {'kunit': 'the test runner in the loop (KUnit)', 'vitest': 'the test runner in the loop (vitest)'}


def pass_k(per_task):
    """per_task: {id: (judged, successes)}. Returns (k, estimate) with k = fewest judged runs of any task."""
    if not per_task:
        return 1, 0.0
    k = min(n for n, _ in per_task.values())
    if k == 0:
        return 1, 0.0
    est = statistics.mean(math.comb(c, k) / math.comb(n, k) for n, c in per_task.values())
    return k, est


def list_price(entry):
    """One number to order models by price: input + output list price per Mtok."""
    r = report.price.rates(entry)
    return None if r is None else (r['in'] + r['out']) * 1e6


def candidates(cells, fam):
    """Aggregate receipts per (model, effort) over the family's benches and trials."""
    agg = defaultdict(lambda: {'n': 0, 'success': 0, 'not_model': 0, 'cost': 0.0, 'walls': [], 'trials': defaultdict(set), 'tokens': [],
                               'per_task': defaultdict(lambda: [0, 0])})
    for (bench, model, effort, trial), rows in cells.items():
        if bench not in fam['benches']:
            continue
        a = agg[(model, effort)]
        pending = sum(1 for x in rows if x['outcome'] == 'ungraded')
        rows = [x for x in rows if x['outcome'] != 'ungraded']  # not graded yet: not evidence either way
        if not rows:
            continue
        a['pending'] = a.get('pending', 0) + pending
        s = report.summarize(rows, bench)
        a['n'] += s['n']; a['success'] += s['success']; a['not_model'] += s['not_model']
        a['cost'] += s['cost_total'] or 0.0
        a['walls'] += [x['wall'] for x in rows if x['wall'] is not None]
        a['trials'][bench].add(trial)
        a['tokens'] += [x['tokens'] for x in rows]
        for x in rows:
            if x['outcome'] not in report.NOT_MODEL:
                t = a['per_task'][(bench, x['id'])]
                t[0] += 1
                t[1] += x['outcome'] in report.SUCCESS[bench]
    out = {}
    for key, a in agg.items():
        judged = a['n'] - a['not_model']
        k, pk = pass_k({i: tuple(v) for i, v in a['per_task'].items()})
        out[key] = {'n': a['n'], 'success': a['success'], 'not_model': a['not_model'], 'pending': a.get('pending', 0),
                    'rate': (a['success'] / judged) if judged else 0.0,
                    'ci': report.wilson(a['success'], judged), 'k': k, 'pass_k': pk,
                    'cost_per_success': (a['cost'] / a['success']) if a['success'] else None,
                    'cost_total': a['cost'], 'wall_mean': statistics.mean(a['walls']) if a['walls'] else None,
                    'trials': {b: len(t) for b, t in a['trials'].items()},
                    'covers': all(b in a['trials'] for b in fam['benches']),
                    'tokens_mean': {k: statistics.mean(t[k] for t in a['tokens']) for k in ('input', 'output', 'cache_read', 'cache_write')}}
    return out


def score(v, rule):
    return v['ci'][0] if rule == 'lower' else v['rate']


def decide_family(cands, margin, min_trials, rule='lower'):
    ok = {k: v for k, v in cands.items() if v['covers'] and min(v['trials'].values()) >= min_trials and v['cost_per_success'] is not None}
    if not ok:
        return None, None, None
    bar = max(score(v, rule) for v in ok.values()) - margin
    above = sorted((k for k, v in ok.items() if score(v, rule) >= bar),
                   key=lambda k: (ok[k]['cost_per_success'], ok[k]['wall_mean'] or 0))
    best = above[0]
    # step-up: the cheapest candidate above the bar that is more reliable than the default
    better = [k for k in above[1:] if ok[k]['rate'] > ok[best]['rate']]
    return bar, best, (better[0] if better else None)


def split_effort(effort):
    eff, _, variant = effort.partition('+')
    return eff, ([REQUIRES.get(variant, variant)] if variant else [])


def fmt_cand(k, v):
    lost = f", {v['not_model']} lost to the harness" if v['not_model'] else ''
    pend = f", {v['pending']} ungraded" if v.get('pending') else ''
    cps = f"${v['cost_per_success']:.4f}" if v['cost_per_success'] is not None else 'no success'
    ci = f"{v['ci'][0]:.2f}-{v['ci'][1]:.2f}" if v['ci'][0] is not None else '-'
    pk = f", pass^{v['k']} {v['pass_k']:.2f}" if v['k'] > 1 else ''
    return f"{ALIAS.get(k[0], k[0])} {k[1]} {v['success']}/{v['n'] - v['not_model']} ({v['rate']:.3f}, CI {ci}{pk}) {cps} {v['wall_mean']:.0f} s{lost}{pend}"


def plan_new_models(cat, fams_decided, cells):
    """Which families a catalog model with no receipts is worth running, and what it would cost."""
    seen = {model for (_, model, _, _) in cells}
    plan = []
    for mid, entry in cat['models'].items():
        model = mid.split(':', 1)[-1]
        if model in seen or list_price(entry) is None:
            continue
        rows = []
        for name, d in fams_decided.items():
            if not d.get('default'):
                rows.append({'family': name, 'run': True, 'why': 'no candidate decided yet'})
                continue
            cur = report.price.model_entry(d['default']['model_id'], cat)
            cheaper = cur is None or list_price(entry) <= list_price(cur)
            # a dearer model can only change the decision by raising the bar above the default's rate
            can_raise_bar = d['default_rate'] + d['margin'] < 1.0
            cheaper = cheaper or can_raise_bar
            tok = d['tokens_mean']
            r = report.price.rates(entry)
            est = d['n_tasks'] * (tok['input'] * r['in'] + tok['output'] * r['out'] + tok['cache_read'] * r['cache_read'] + tok['cache_write'] * r['write_1h'])
            rows.append({'family': name, 'run': cheaper, 'n_tasks': d['n_tasks'], 'expected_cost_usd': round(est, 2),
                         'why': ('not dearer than the current default, so it could win on cost' if list_price(entry) <= list_price(cur) else
                                 'dearer, but the default is below the bar ceiling, so a perfect run could raise the bar') if cheaper
                         else 'dearer than the current default and the default is at the ceiling; it cannot change the decision'})
        rows.sort(key=lambda x: (not x['run'], x.get('expected_cost_usd', 0)))
        plan.append({'model': mid, 'provider': entry.get('provider'), 'list_price_in_plus_out_per_mtok': list_price(entry), 'families': rows,
                     'harness': HARNESS_FOR.get(entry.get('provider'), 'needs a harness adapter (bench/common/harness.py)')})
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--margin', type=float, default=0.02)
    ap.add_argument('--min-trials', type=int, default=1)
    ap.add_argument('--rule', default='lower', choices=['lower', 'point'],
                    help='score a candidate by the Wilson 95%% lower bound of its rate (default) or by the rate itself')
    ap.add_argument('--prices', type=Path, default=None)
    ap.add_argument('--runs', type=Path, default=HERE / 'runs')
    args = ap.parse_args()
    cat = report.price.catalog(args.prices) if args.prices else report.price.catalog()
    cells = report.load_cells(args.runs, cat)
    n_tasks = defaultdict(set)
    for (bench, _, _, _), rows in cells.items():
        n_tasks[bench] |= {x['id'] for x in rows}

    decided, lines = {}, []
    lines.append(f'| Family | Default | Needs | Rate (judged runs) | 95% CI | pass^k | Cost per success | Step-up | Bar ({args.rule}) | Candidates |')
    lines.append('|---|---|---|---|---|---|---|---|---|---|')
    for name, fam in FAMILIES.items():
        cands = candidates(cells, fam)
        bar, best, second = decide_family(cands, args.margin, args.min_trials, args.rule)
        if best is None:
            decided[name] = {'default': None, 'why': 'no candidate covers every bench with enough trials'}
            lines.append(f'| {name} | none | | | | | | | | {len(cands)} partial |')
            continue
        eff, needs = split_effort(best[1])
        v = cands[best]
        d = {'default': {'model': ALIAS.get(best[0], best[0]), 'model_id': best[0], 'effort': eff, 'requires': needs},
             'step_up': None, 'bar': round(bar, 4),
             'rule': (f'cheapest candidate whose {"Wilson 95% lower bound" if args.rule == "lower" else "rate"} >= best - {args.margin}, '
                      'by cost per success; harness-lost runs excluded from the rate'),
             'evidence': {f'{k[0]} {k[1]}': {x: (round(y, 4) if isinstance(y, float) else [round(z, 4) for z in y] if x == 'ci' and y[0] is not None else y)
                                             for x, y in c.items() if x != 'tokens_mean'} for k, c in sorted(cands.items())},
             'n_tasks': sum(len(n_tasks[b]) for b in fam['benches']), 'tokens_mean': v['tokens_mean'],
             'default_rate': v['rate'], 'default_ci': [round(x, 4) for x in v['ci']], 'margin': args.margin}
        if second:
            e2, n2 = split_effort(second[1])
            d['step_up'] = {'model': ALIAS.get(second[0], second[0]), 'model_id': second[0], 'effort': e2, 'requires': n2,
                            'cost_per_success': round(cands[second]['cost_per_success'], 4)}
        decided[name] = d
        su = f"{d['step_up']['model']} {d['step_up']['effort']} (${d['step_up']['cost_per_success']:.3f})" if d['step_up'] else 'none'
        pk = f"pass^{v['k']} {v['pass_k']:.2f}" if v['k'] > 1 else '1 trial'
        lines.append(f"| {name} | **{d['default']['model']}**, {eff} | {', '.join(needs) or '-'} | {v['success']}/{v['n'] - v['not_model']} = {v['rate']:.3f} | {v['ci'][0]:.2f}-{v['ci'][1]:.2f} | {pk} | ${v['cost_per_success']:.4f} | {su} | {bar:.3f} | "
                     + '; '.join(fmt_cand(k, c) for k, c in sorted(cands.items()) if c['covers']) + ' |')
    plan = plan_new_models(cat, decided, cells)
    table = '\n'.join(lines)
    print(table)
    print('\nUnmeasured catalog models:')
    for p in plan:
        runs = [f"{r['family']} (~${r['expected_cost_usd']})" if 'expected_cost_usd' in r else f"{r['family']} ({r['why']})" for r in p['families'] if r['run']]
        print(f"- {p['model']} ({p['provider']}, ${p['list_price_in_plus_out_per_mtok']:.2f}/Mtok in+out, {p['harness']}): " + (('run ' + ', '.join(runs)) if runs else 'nothing to run, it cannot beat the defaults on cost'))
    if args.dry_run:
        return
    rp = HERE / 'routing.json'
    j = json.loads(rp.read_text(encoding='utf-8'))
    for name, d in decided.items():
        if name not in j['families']:
            print(f'warning: routing.json has no family {name}; skipped')
            continue
        f = j['families'][name]
        if d.get('default'):
            f['default'] = {'model': d['default']['model'], 'effort': d['default']['effort']}
            if d['default']['requires']:
                f['requires'] = d['default']['requires']
            f['step_up'] = d['step_up']
        f['decided'] = {k: d[k] for k in ('bar', 'rule', 'evidence', 'n_tasks', 'default_rate') if k in d}
    # Agent files: Claude Code can only name Anthropic models, so each agent gets the cheapest
    # Anthropic candidate above its family's bar; if a non-Anthropic model won the family, say so.
    for name, route in j.get('agents', {}).items():
        d = decided.get(route.get('family'))
        if not d or not d.get('default'):
            continue
        fam = FAMILIES[route['family']]
        cands = candidates(cells, fam)
        bar = d['bar']
        anth = sorted((k for k, v in cands.items() if v['covers'] and v['cost_per_success'] is not None
                       and score(v, args.rule) >= bar and k[0] in ALIAS),
                      key=lambda k: (cands[k]['cost_per_success'], cands[k]['wall_mean'] or 0))
        if not anth:
            continue
        eff, needs = split_effort(anth[0][1])
        route['model'], route['effort'] = ALIAS[anth[0][0]], eff
        if anth[0][0] != d['default']['model_id']:
            route['note_provider'] = (f"the family's cheapest candidate is {d['default']['model_id']}, which a Claude Code agent file "
                                      f"cannot name; applied the cheapest Anthropic candidate above the bar instead")
        else:
            route.pop('note_provider', None)
    j['decided_by'] = f'decide.py --margin {args.margin} --min-trials {args.min_trials} --rule {args.rule} (catalog prices)'
    j['plan_for_unmeasured_models'] = plan
    rp.write_text(json.dumps(j, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    md = HERE / 'ROUTING.md'
    text = md.read_text(encoding='utf-8')
    block = (f'<!-- decide:start -->\n_Generated by `python3 decide.py` (margin {args.margin}, min trials {args.min_trials}, rule {args.rule}, catalog prices). '
             f'Rate = successes over judged runs; runs the harness lost are retried, not judged. CI = 95% Wilson interval of the rate; '
             f'with rule `lower` the bar is the best lower bound minus the margin, so thin evidence cannot win. '
             f'pass^k = chance that all k trials of a task succeed, k = trials per task._\n\n{table}\n<!-- decide:end -->')
    if '<!-- decide:start -->' in text:
        text = re.sub(r'<!-- decide:start -->.*?<!-- decide:end -->', lambda m: block, text, flags=re.S)
    else:
        text = text.rstrip('\n') + '\n\n## Decision table\n\n' + block + '\n'
    md.write_text(text, encoding='utf-8')
    print('\nwrote routing.json and ROUTING.md')


if __name__ == '__main__':
    main()
