#!/usr/bin/env python3
"""What the last N days of interactive Claude Code work consumed, and on what.

Reads the local transcripts (~/.claude/projects): main sessions by model and
effort (the effort of each request is in its api-request row), and every Agent
call with the subagent it started, its model and its catalog-priced cost. Each
call is classified by its prompt (fact-lookup, research-synthesis, code-change,
code-explore, other); the classes are a keyword heuristic, say so when quoting
them. Catalog prices are API-equivalent: on a subscription they measure
rate-limit headroom, not a bill. tools/status.py turns this into suggestions.

Usage: python3 tools/consumption.py [--days 30] [--json]
"""
import argparse
import collections
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / 'catalog'))
sys.path.insert(0, str(HERE / 'bench/common'))
import price  # noqa: E402
import local  # noqa: E402

CAT = price.catalog(HERE / 'catalog/models.json')
ROOT = Path.home() / '.claude/projects'
BENCH = local.skip_projects()   # benchmark sessions on this machine (local/config.json), not the user's own work
AGENT_IDS = (re.compile(r'agentId\\?":\\?"([0-9a-f]{12,24})'), re.compile(r'\b([0-9a-f]{15,24}) \(internal ID'))
TOKENS = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')

LOOKUP = ('what is the', 'which version', 'latest version', 'look up', 'find out', 'check the docs', 'default value',
          'release date', 'is it supported', 'what does the doc', 'current version', 'find the url')
SYNTHESIS = ('research', 'compare', 'comparison', 'report', 'compile', 'deep dive', 'survey', 'landscape', 'fact-dense',
             'summarize the', 'write up', 'notes that let')
CODE = ('fix', 'implement', 'refactor', 'write tests', 'bug', 'add a', 'change the', 'migrate', 'failing test')
BROWSER = ('in the browser', 'chrome', 'web page', 'the page at', 'fill the form', 'fill in the form', 'click', 'sign in', 'log in',
           'navigate to', 'open http', 'checklist', 'pass/fail')   # the same list the widget's router uses


def classify(subagent_type, prompt):
    """The kind of work an Agent call is, by agent type first, then by its prompt. code-explore, fact-lookup
    and browser-flow are measured families (tools/status.py CLASS_FAMILY); the rest are not, and no suggestion
    downgrades them."""
    p = (prompt or '').lower()
    t = (subagent_type or '').lower()
    if subagent_type == 'Web Researcher':
        return 'fact-lookup'
    if subagent_type in ('Explore', 'Plan', 'Codebase Onboarding Engineer'):
        return 'code-explore'
    if 'browser' in t or subagent_type == 'Evidence Collector' or sum(k in p for k in BROWSER) >= 2:
        return 'browser-flow'
    if 'review' in t:
        return 'code-review'
    if len(p) < 900 and any(k in p for k in LOOKUP):
        return 'fact-lookup'
    if any(k in p for k in SYNTHESIS):
        return 'research-synthesis'
    if any(k in p for k in CODE):
        return 'code-change'
    return 'other'


def collect(days=30, now=None, splits=None):
    """The window's consumption; with `splits` (sorted ISO UTC times, the recorded changes), the current
    window is also cut into segments between them, so each change can be measured in its own window
    (tools/status.py realized_savings): segment i is the stretch before change i, segment i+1 the one after."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    since_cur = (now - datetime.timedelta(days=days)).isoformat()
    since_prev = (now - datetime.timedelta(days=2 * days)).isoformat()
    tok = collections.defaultdict(collections.Counter)      # (window, where, model, effort) -> token counts
    cost = collections.Counter(); out_cost = collections.Counter(); msgs = collections.Counter()
    calls = {}                                               # tool_use_id -> Agent call
    agent_of = {}                                            # tool_use_id -> agentId
    agent_cost = collections.Counter(); agent_model = {}
    daily = collections.Counter()                            # day -> catalog $ (main and subagents)
    pmsgs = collections.Counter(); pcost = collections.Counter()   # (segment, where, model, effort) when splits are set
    seen = set()
    files = 0
    for f in ROOT.glob('**/*.jsonl'):
        proj = f.relative_to(ROOT).parts[0]
        if any(b in proj for b in BENCH):
            continue
        files += 1
        is_sub = 'subagents' in f.parts
        effort = None
        for line in f.open(encoding='utf-8', errors='replace'):
            if not ('"api-request"' in line or '"assistant"' in line or 'agentId' in line or '"tool_use"' in line):
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            t = r.get('type')
            if t == 'api-request':
                effort = ((r.get('params') or {}).get('output_config') or {}).get('effort') or effort
                continue
            ts = r.get('timestamp') or ''
            window = 'cur' if ts >= since_cur else 'prev' if ts >= since_prev else None
            m = r.get('message') or {}
            if t == 'assistant' and isinstance(m.get('content'), list):
                u, model, mid = m.get('usage') or {}, m.get('model') or '?', m.get('id')
                if u and model != '<synthetic>' and (mid, u.get('output_tokens')) not in seen:
                    if mid:
                        seen.add((mid, u.get('output_tokens')))
                    entry = price.model_entry(model, CAT)
                    if not entry:
                        model = model + ' (no price)'
                    c = (price.price_usage(u, entry) or 0) if entry else 0
                    oc = u.get('output_tokens', 0) * price.rates(entry)['out'] if entry else 0
                    if window:
                        key = (window, 'sub' if is_sub else 'main', model, effort or '?')
                        for k in TOKENS:
                            tok[key][k] += u.get(k, 0) or 0
                        msgs[key] += 1; cost[key] += c; out_cost[key] += oc
                        if window == 'cur':
                            daily[ts[:10]] += c
                            if splits:
                                pk = (sum(1 for sp in splits if ts >= sp), 'sub' if is_sub else 'main', model, effort or '?')
                                pmsgs[pk] += 1; pcost[pk] += c
                    if is_sub and r.get('agentId'):
                        agent_cost[r['agentId']] += c; agent_model[r['agentId']] = model
                for it in m['content']:
                    if isinstance(it, dict) and it.get('type') == 'tool_use' and it.get('name') in ('Agent', 'Task') and window:
                        inp = it.get('input') or {}
                        st = inp.get('subagent_type') or 'general-purpose'
                        calls[it.get('id')] = {'ts': ts[:16], 'window': window, 'project': proj, 'type': st, 'model_asked': inp.get('model'),
                                               'description': (inp.get('description') or '')[:60], 'prompt_chars': len(inp.get('prompt') or ''),
                                               'class': classify(st, inp.get('prompt'))}
            elif t == 'user' and 'agentId' in line and isinstance(m.get('content'), list):
                # one user row can hold several tool_results (parallel Agent calls): match each by its own text
                results = [it for it in m['content'] if isinstance(it, dict) and it.get('type') == 'tool_result']
                tur = r.get('toolUseResult') if isinstance(r.get('toolUseResult'), dict) else {}
                for it in results:
                    text = json.dumps(it.get('content'))
                    found = next((mm.group(1) for rx in AGENT_IDS for mm in [rx.search(text)] if mm), None)
                    if not found and len(results) == 1 and tur.get('agentId'):
                        found = tur['agentId']
                    if found:
                        agent_of[it.get('tool_use_id')] = found
    for cid, c in calls.items():
        aid = agent_of.get(cid)
        c['agent'] = aid; c['cost'] = round(agent_cost.get(aid, 0.0), 4) if aid else None; c['model'] = agent_model.get(aid)

    def rows(window):
        out = []
        for (w, where, model, eff), n in sorted(msgs.items(), key=lambda kv: -cost[kv[0]]):
            if w == window and where == 'main':
                out.append({'model': model, 'effort': eff, 'msgs': n, **{k: tok[(w, where, model, eff)][k] for k in TOKENS},
                            'cost': round(cost[(w, where, model, eff)], 2), 'out_cost': round(out_cost[(w, where, model, eff)], 2)})
        return out
    by_class = collections.defaultdict(lambda: {'n': 0, 'cost': 0.0, 'types': collections.Counter(), 'unpriced': 0, 'last': '',
                                                'models': collections.defaultdict(lambda: {'n': 0, 'cost': 0.0})})
    for c in calls.values():
        if c['window'] != 'cur':
            continue
        b = by_class[c['class']]; b['n'] += 1; b['types'][c['type']] += 1
        bm = b['models'][c['model'] or '?']; bm['n'] += 1; bm['cost'] += c['cost'] or 0.0
        b['last'] = max(b['last'], c['ts'])
        if c['cost'] is None:
            b['unpriced'] += 1
        else:
            b['cost'] += c['cost']
    for b in by_class.values():
        b['cost'] = round(b['cost'], 2); b['types'] = dict(b['types'])
        b['models'] = {m: {'n': v['n'], 'cost': round(v['cost'], 4)} for m, v in b['models'].items()}
    day_list = [(now - datetime.timedelta(days=i)).date().isoformat() for i in range(days - 1, -1, -1)]
    def segment(i):
        prow = [{'model': m, 'effort': e, 'msgs': n, 'cost': round(pcost[(p, w, m, e)], 2)}
                for (p, w, m, e), n in sorted(pmsgs.items(), key=lambda kv: -pcost[kv[0]]) if p == i and w == 'main']
        return {'main_rows': prow, 'main_total': round(sum(v for k, v in pcost.items() if k[0] == i and k[1] == 'main'), 2),
                'main_msgs': sum(v for k, v in pmsgs.items() if k[0] == i and k[1] == 'main')}
    sub_total = {w: round(sum(v for k, v in cost.items() if k[0] == w and k[1] == 'sub'), 2) for w in ('cur', 'prev')}
    main_total = {w: round(sum(v for k, v in cost.items() if k[0] == w and k[1] == 'main'), 2) for w in ('cur', 'prev')}
    return {'days': days, 'since': since_cur[:10], 'files': files, 'daily': [{'date': d, 'cost': round(daily[d], 2)} for d in day_list],
            'splits': splits, 'segments': [segment(i) for i in range(len(splits) + 1)] if splits else None,
            'main': {'rows': rows('cur'), 'total': main_total['cur'], 'out_cost': round(sum(v for k, v in out_cost.items() if k[0] == 'cur' and k[1] == 'main'), 2)},
            'subagents': {'calls': sorted((c for c in calls.values() if c['window'] == 'cur'), key=lambda c: c['ts']),
                          'by_class': dict(by_class), 'total': sub_total['cur']},
            'previous': {'since': since_prev[:10], 'main_total': main_total['prev'], 'main_rows': rows('prev'), 'subagents_total': sub_total['prev']}}


def text(s):
    out = [f"consumption, last {s['days']} days (since {s['since']}), catalog-equivalent $ (headroom on a subscription)",
           f"{'main sessions':<34}{'msgs':>6}{'in':>9}{'out':>9}{'cache_r':>12}{'cache_w':>10}{'$':>8}{'out $':>8}"]
    for r in s['main']['rows']:
        out.append(f"  {r['model']:<20}{r['effort']:<12}{r['msgs']:>6}{r['input_tokens']:>9}{r['output_tokens']:>9}{r['cache_read_input_tokens']:>12}"
                   f"{r['cache_creation_input_tokens']:>10}{r['cost']:>8.2f}{r['out_cost']:>8.2f}")
    out.append(f"  {'total':<32}{'':>6}{'':>9}{'':>9}{'':>12}{'':>10}{s['main']['total']:>8.2f}{s['main']['out_cost']:>8.2f}")
    sub = s['subagents']
    out.append(f"subagent calls: {len(sub['calls'])} (${sub['total']:.2f}); classes are a keyword heuristic")
    for cls, b in sorted(sub['by_class'].items(), key=lambda kv: -kv[1]['cost']):
        types = ', '.join(f'{t} x{n}' for t, n in b['types'].items())
        out.append(f"  {cls:<20}{b['n']:>4}  ${b['cost']:>7.2f}  {types}" + (f"  ({b['unpriced']} unpriced)" if b['unpriced'] else ''))
    p = s['previous']
    out.append(f"previous {s['days']} days (since {p['since']}): main ${p['main_total']:.2f}, subagents ${p['subagents_total']:.2f}")
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    s = collect(args.days)
    print(json.dumps(s) if args.json else text(s))


if __name__ == '__main__':
    main()
