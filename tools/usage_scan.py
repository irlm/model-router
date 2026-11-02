"""What this machine actually runs: scan the local Claude Code transcripts
(~/.claude/projects) and print subagent calls by type, project and month, plus
tokens and catalog-priced cost by model, split into interactive sessions and the
benchmark's own headless sessions. Catalog prices are API-equivalent; on a
subscription they measure rate-limit headroom, not a bill.

Usage: python3 tools/usage_scan.py            (reads ~/.claude/projects, catalog/models.json)
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'catalog'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bench/common'))
import price
import local
CAT = price.catalog(Path(__file__).resolve().parents[1] / 'catalog/models.json')
ROOT = Path.home() / '.claude/projects'
BENCH = local.skip_projects()   # benchmark sessions on this machine (local/config.json), not the user's own work
agent_calls = collections.Counter(); agent_by_proj = collections.Counter(); agent_by_month = collections.Counter()
tok = collections.defaultdict(lambda: collections.Counter()); cost = collections.Counter(); msgs = collections.Counter()
seen_ids = set(); files = 0; bad = 0
for f in ROOT.glob('**/*.jsonl'):
    proj = f.relative_to(ROOT).parts[0]
    kind = 'bench' if any(b in proj for b in BENCH) else 'interactive'
    sub = 'subagent-file' if 'subagents' in f.parts else 'main'
    files += 1
    for line in f.open(encoding='utf-8', errors='replace'):
        try: r = json.loads(line)
        except ValueError: bad += 1; continue
        m = r.get('message') or {}
        ts = (r.get('timestamp') or '')[:7]
        if r.get('type') == 'assistant' and isinstance(m.get('content'), list):
            mid = m.get('id')
            u = m.get('usage') or {}
            model = m.get('model') or '?'
            if mid and (mid, u.get('output_tokens')) in seen_ids: pass
            else:
                if mid: seen_ids.add((mid, u.get('output_tokens')))
                if u and model != '<synthetic>':
                    key = (kind, sub, ts, model)
                    for k in ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'):
                        tok[key][k] += u.get(k, 0) or 0
                    msgs[key] += 1
                    try:
                        c = price.price_usage(u, price.model_entry(model, CAT))
                        cost[key] += c or 0
                    except Exception:
                        cost[(kind, sub, ts, model + ' (no price)')] += 0
            for it in m['content']:
                if isinstance(it, dict) and it.get('type') == 'tool_use' and it.get('name') in ('Agent', 'Task'):
                    st = (it.get('input') or {}).get('subagent_type') or 'general-purpose'
                    agent_calls[(kind, st)] += 1; agent_by_proj[(kind, proj)] += 1; agent_by_month[(kind, ts)] += 1
print('files', files, 'bad lines', bad)
print('\n== Agent tool calls by subagent_type (interactive sessions)')
for (kind, st), n in agent_calls.most_common():
    if kind == 'interactive': print(f'{n:5d}  {st}')
print('bench-session agent calls:', sum(n for (k, _), n in agent_calls.items() if k == 'bench'))
print('\n== Agent calls by month (interactive)')
for (kind, ts), n in sorted(agent_by_month.items()):
    if kind == 'interactive': print(f'{ts}  {n}')
if '--projects' in sys.argv:   # project directory names stay off the ledger: they name the user's repositories
    print('\n== Agent calls by project (interactive, top 12)')
    for (kind, p), n in agent_by_proj.most_common(40):
        if kind == 'interactive': print(f'{n:5d}  {p}')
print('\n== Tokens and catalog cost by kind / file / month / model')
rows = sorted(tok.keys())
print(f"{'kind':12} {'file':14} {'month':8} {'model':24} {'msgs':>7} {'in':>10} {'cache_w':>12} {'cache_r':>14} {'out':>10} {'cost$':>10}")
agg = collections.Counter()
for key in rows:
    t = tok[key]
    print(f"{key[0]:12} {key[1]:14} {key[2]:8} {key[3]:24} {msgs[key]:7d} {t['input_tokens']:10d} {t['cache_creation_input_tokens']:12d} {t['cache_read_input_tokens']:14d} {t['output_tokens']:10d} {cost[key]:10.2f}")
    agg[(key[0], key[3])] += cost[key]
print('\n== Catalog cost by kind and model (all months)')
for (kind, model), c in sorted(agg.items(), key=lambda x: -x[1]):
    print(f'{c:10.2f}  {kind:12} {model}')
