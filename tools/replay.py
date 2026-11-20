"""Price the last N days of Agent calls under another routing: a candidate routing.json before `apply`, or the current one
against what the calls really ran on. Shadow mode before the fact: nothing is moved, nothing is written.

  python3 tools/replay.py [CANDIDATE.json] [--days 30] [--json]

For each class of call a family covers (tools/status.py CLASS_FAMILY), the calls' own tokens are priced, token for token, at
the rates of the model the candidate decides for that family (the same-work figure realized_savings uses: task size cancels
out; what a different model does with the same ask does not, which is why the family's regression verdict stands beside it).
A class whose candidate decision equals the model the calls ran on shows zero: the replay prices the model change alone.
Output: per class, the calls, what they cost, what they would have cost, and the difference; then the total.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'tools'))
import status  # noqa: E402
import consumption  # noqa: E402
import decide  # noqa: E402


def decisions(routing):
    """family -> (model id, effort) of the routing's default, with the alias resolved to the catalog id."""
    out = {}
    for fam, rf in routing['families'].items():
        d = rf.get('default') or {}
        if d.get('model') and d['model'] != 'inherit':
            mid = next((m for m, a in decide.ALIAS.items() if a == d['model']), d['model'])
            out[fam] = (mid, d.get('effort'))
    return out


def replay(usage, routing):
    """The window's calls under ROUTING: rows per class, and the totals."""
    dec = decisions(routing)
    rows = []
    for cls, fam in status.CLASS_FAMILY.items():
        calls = [c for c in usage['subagents']['calls'] if c.get('window') == 'cur' and c.get('class') == cls and c.get('cost') is not None]
        if not calls or fam not in dec:
            continue
        mid, eff = dec[fam]
        priced = [(c, status.price_tokens(c.get('tok'), mid)) for c in calls]
        priced = [(c, p) for c, p in priced if p is not None]
        actual = sum(c['cost'] for c, _ in priced)
        under = sum(p for _, p in priced)
        moved = sum(1 for c, _ in priced if (c.get('model') or '') != mid)
        rows.append({'class': cls, 'family': fam, 'decision': f'{mid} {eff}', 'calls': len(priced), 'moved': moved, 'actual': round(actual, 2),
                     'under': round(under, 2), 'saved': round(actual - under, 2), 'unpriced': len(calls) - len(priced)})
    return {'rows': rows, 'actual': round(sum(r['actual'] for r in rows), 2), 'under': round(sum(r['under'] for r in rows), 2),
            'saved': round(sum(r['saved'] for r in rows), 2), 'days': usage['days'], 'since': usage['since']}


def text(r, label):
    out = [f"replay of the last {r['days']} days (since {r['since']}) under {label}: the calls' own tokens at the decided model's rates",
           f"{'class':<20}{'decision':<28}{'calls':>6}{'moved':>6}{'actual':>9}{'under':>9}{'saved':>9}"]
    for x in r['rows']:
        out.append(f"{x['class']:<20}{x['decision']:<28}{x['calls']:>6}{x['moved']:>6}{x['actual']:>9.2f}{x['under']:>9.2f}{x['saved']:>9.2f}"
                   + (f"  ({x['unpriced']} unpriced)" if x['unpriced'] else ''))
    if not r['rows']:
        out.append('  no call of a covered class in the window')
    out.append(f"{'total':<54}{r['actual']:>9.2f}{r['under']:>9.2f}{r['saved']:>9.2f}")
    out.append('moved: calls that ran on another model than the decision (a positive saved is what the decision would have kept; what a different '
               'model does with the same ask is not in it: the regression verdict is)')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('candidate', nargs='?', help='a routing.json to price the window under (default: the current one)')
    ap.add_argument('--days', type=int, default=status.USAGE_DAYS)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    path = Path(a.candidate) if a.candidate else HERE / 'routing.json'
    routing = json.loads(path.read_text(encoding='utf-8'))
    usage = consumption.collect(a.days)
    r = replay(usage, routing)
    r['routing'] = str(path)
    print(json.dumps(r, indent=1) if a.json else text(r, 'the current routing.json' if not a.candidate else str(path)))


if __name__ == '__main__':
    main()
