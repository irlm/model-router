"""The runs the widget saved on this machine, and the days before it watched.

A run is one task's agents: the agents a prompt spawned, or everything under a named task (/router task).
The widget writes one JSON file per run under <CLAUDE_CONFIG_DIR or ~/.claude>/model-router/runs/<day>/
when the run's last agent ends (never in the repository). This tool lists them, prints one, writes one as a
markdown report, and rebuilds runs for the days before the widget watched from the transcripts (the Agent
calls with their prompts, models and priced usage; no per-second timing, no tool-by-tool tail: the engine
reports those only while the widget is loaded).

  python3 tools/runs.py list [--json]
  python3 tools/runs.py show <id>
  python3 tools/runs.py export <id> [--out-dir DIR]
  python3 tools/runs.py import [--days N] [--rebuild]
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

import claude_home  # the one resolver of <CLAUDE_CONFIG_DIR or ~/.claude>

HERE = Path(__file__).resolve().parent
RUNS = claude_home.config_dir() / 'model-router' / 'runs'
GAP_MIN = 15   # Agent calls of one session this far apart begin a new run, when rebuilt from transcripts


def slug(t):
    return (re.sub(r'[^a-z0-9]+', '-', (t or '').lower()).strip('-')[:40]) or 'run'


def money(n):
    return f"${n:.0f}" if n >= 10 else f"${n:.2f}"


def files(runs_dir=None):
    d = Path(runs_dir or RUNS)
    return sorted(d.glob('*/*.json')) if d.exists() else []


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def meta_of(run, path):
    m = run.get('meta') or {}
    return {'file': str(path), 'id': m.get('id', ''), 'startedAt': m.get('startedAt', 0), 'prompt': m.get('prompt', ''), 'name': m.get('name'),
            'agentN': m.get('agentN', len(run.get('agents') or [])), 'cost': round(float(m.get('cost') or 0), 4), 'source': run.get('source', 'live')}


def list_runs(runs_dir=None):
    out = []
    for p in files(runs_dir):
        try:
            out.append(meta_of(load(p), p))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda r: r['startedAt'])


def find(id_or_file, runs_dir=None):
    p = Path(id_or_file)
    if p.exists():
        return load(p), p
    for f in files(runs_dir):
        try:
            run = load(f)
        except (OSError, ValueError):
            continue
        if (run.get('meta') or {}).get('id') == id_or_file:
            return run, f
    raise SystemExit(f"no saved run {id_or_file}; python3 tools/runs.py list names them")


def when(ms):
    """Local date and time, the clock the widget names the run folders by."""
    try:
        return datetime.datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d %H:%M')
    except (TypeError, ValueError, OSError):
        return '?'


def secs(ms):
    s = max(0, int(round(ms / 1000)))
    return f"{s}s" if s < 60 else f"{s // 60}m{s % 60:02d}"


def end_word(a):
    return 'stopped' if a.get('stopped') else 'failed' if a.get('failed') else 'done' if a.get('done') else 'running'


def text(run):
    m = run.get('meta') or {}
    agents = sorted(run.get('agents') or [], key=lambda a: (a.get('n', 0), a.get('run', 1)))
    out = [f"run {m.get('id', '?')}: {m.get('name') or m.get('prompt') or ''}",
           f"started {when(m.get('startedAt', 0))}" + (f", ended {when(m['endedAt'])}" if m.get('endedAt') else '')
           + f" · {m.get('agentN', len(agents))} agents · {money(float(m.get('cost') or 0))}"
           + (f" · {m['failedN']} failed" if m.get('failedN') else '') + (f" · {m['stoppedN']} stopped" if m.get('stoppedN') else '')
           + (" · from transcripts" if run.get('source') == 'transcript' else '')]
    for a in agents:
        n = f"{a.get('n', 0):02d}" + (f" · run {a['run']}" if a.get('run', 1) > 1 else '')
        model = f"{a.get('model', '')} {a.get('effort', '')}".strip()
        elapsed = secs((a.get('done') or a.get('startedAt', 0)) - a.get('startedAt', 0)) if a.get('done') else '-'
        cost = money(a['cost']) if a.get('cost') is not None else '-'
        out.append(f"  {n:10} {a.get('type', ''):22} {model:16} {a.get('family') or 'unmeasured':18} {a.get('steps', 0):3} steps {elapsed:>6} {cost:>6}  {end_word(a):8} {a.get('description', '')}")
    for ev in run.get('events') or []:
        out.append(f"  {when(ev.get('at', 0))[-5:]}  {ev.get('text', '')}")
    return '\n'.join(out)


def markdown(run):
    m = run.get('meta') or {}
    agents = sorted(run.get('agents') or [], key=lambda a: (a.get('n', 0), a.get('run', 1)))
    out = [f"# Agent run: {m.get('name') or m.get('prompt') or m.get('id', '')}", '',
           f"started {when(m.get('startedAt', 0))}" + (f", ended {when(m['endedAt'])}" if m.get('endedAt') else '')
           + f" · {m.get('agentN', len(agents))} agents · {money(float(m.get('cost') or 0))}"
           + (f" · {m['failedN']} failed" if m.get('failedN') else '') + (f" · {m['stoppedN']} stopped" if m.get('stoppedN') else '')
           + (" · rebuilt from the transcripts (no timing, no tool tail)" if run.get('source') == 'transcript' else ''), '']
    if m.get('prompt') and not m.get('name'):
        out += ['## Asked', '', m['prompt'], '']
    out += ['## Agents', '', '| # | agent | model effort | family | steps | elapsed | cost | outcome | task |', '|---|---|---|---|---|---|---|---|---|']
    for a in agents:
        n = f"{a.get('n', 0):02d}" + (f" · run {a['run']}" if a.get('run', 1) > 1 else '')
        elapsed = secs((a.get('done') or 0) - a.get('startedAt', 0)) if a.get('done') else '-'
        cost = money(a['cost']) if a.get('cost') is not None else '-'
        out.append(f"| {n} | {a.get('type', '')} | {(a.get('model', '') + ' ' + a.get('effort', '')).strip()} | {a.get('family') or 'unmeasured'} | {a.get('steps', 0)} | {elapsed} | {cost} | {end_word(a)} | {(a.get('description') or '').replace('|', '/')} |")
    answers = [a for a in agents if a.get('answer')]
    if answers:
        out += ['', '## Answers', '']
        for a in answers:
            out += [f"### {a.get('n', 0):02d} {a.get('type', '')}: {a.get('description', '')}", '', a['answer'], '']
    if run.get('events'):
        out += ['', '## Events', ''] + [f"- {when(ev.get('at', 0))[-5:]}  {ev.get('text', '')}" for ev in run['events']]
    out += ['', f"_Written by model-router (tools/runs.py); figures from the engine's per-turn usage, priced from the catalog._", '']
    return '\n'.join(out)


def export(run, out_dir):
    m = run.get('meta') or {}
    day = when(m.get('startedAt', 0))[:10]
    path = Path(out_dir) / f"{day}-{slug(m.get('name') or m.get('prompt') or m.get('id'))}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown(run), encoding='utf-8')
    return path


def parent_agent(call):
    """The agent whose transcript this call sits in: a subagent's transcript is agent-<its id>.jsonl; None from a main session."""
    stem = Path(call.get('session', '')).stem
    return stem[len('agent-'):] if stem.startswith('agent-') else None


def group(calls, gap_min=GAP_MIN):
    """Agent calls (tools/consumption.py's, sorted) into runs: one session's calls, a new run after a gap of gap_min minutes.
    A call made inside a subagent's own transcript joins the run of the call that spawned that subagent, under it,
    the way the live graph hangs a child under its spawner; one whose spawner is not in the window stands alone."""
    by_agent = {c['agent']: c for c in calls if c.get('agent')}
    nested = [c for c in calls if parent_agent(c) in by_agent]
    runs = []
    by_session = {}
    for c in sorted((c for c in calls if c not in nested), key=lambda c: (c.get('session', ''), c.get('ts', ''))):
        s = c.get('session', '')
        try:
            t = datetime.datetime.strptime(c['ts'][:16], '%Y-%m-%dT%H:%M').replace(tzinfo=datetime.timezone.utc)
        except (KeyError, ValueError):
            continue
        last = by_session.get(s)
        if last is None or (t - last['t']).total_seconds() > gap_min * 60:
            run = {'session': s, 'start': t, 'calls': []}
            runs.append(run)
            by_session[s] = {'t': t, 'run': run}
        by_session[s]['t'] = t
        by_session[s]['run']['calls'].append((t, c))
    out = []
    for r in runs:
        started = int(r['start'].timestamp() * 1000)
        sess = Path(r['session']).stem[:8]
        # the calls a run's agents made themselves, under the agent that made them, after the top-level ones
        top = [c for _, c in r['calls']]
        kids = []
        frontier = list(top)
        while frontier:
            found = [c for c in nested if parent_agent(c) in {x.get('agent') for x in frontier} and c not in kids]
            kids.extend(found)
            frontier = found
        agents = []
        for i, c in enumerate(top + sorted(kids, key=lambda c: c.get('ts', '')), 1):
            try:
                t = datetime.datetime.strptime(c['ts'][:16], '%Y-%m-%dT%H:%M').replace(tzinfo=datetime.timezone.utc)
            except (KeyError, ValueError):
                t = r['start']
            at = int(t.timestamp() * 1000)
            agents.append({'id': c.get('agent') or f"call-{i}", 'parent': parent_agent(c), 'type': c.get('type', ''), 'description': c.get('description', ''),
                           'model': (c.get('model') or c.get('model_asked') or '').replace('claude-', '').split('-')[0] if (c.get('model') or c.get('model_asked')) else '',
                           'effort': '', 'wantEffort': None, 'family': c.get('class'), 'startedAt': at, 'lastStepAt': at, 'steps': 0, 'done': at,
                           'cost': c.get('cost'), 'out': (c.get('tok') or {}).get('output_tokens', 0), 'failed': bool(c.get('failed')), 'stopped': False,
                           'ctx': int((c.get('prompt_chars') or 0) / 4), 'n': i, 'run': 1, 'recent': [], 'runId': '', 'answer': ''})
        cost = round(sum(a['cost'] or 0 for a in agents), 4)
        rid = f"transcript:{sess}:{r['start'].strftime('%Y%m%dT%H%M')}"
        for a in agents:
            a['runId'] = rid
        first = r['calls'][0][1]
        out.append({'source': 'transcript', 'meta': {'id': rid, 'startedAt': started, 'endedAt': max(a['done'] for a in agents), 'prompt': (first.get('description') or '')[:120],
                                                    'name': None, 'agentN': len(agents), 'cost': cost, 'failedN': sum(1 for a in agents if a['failed']), 'stoppedN': 0, 'saved': None},
                    'agents': agents, 'events': []})
    return sorted(out, key=lambda r: r['meta']['startedAt'])


def import_runs(days=30, runs_dir=None, calls=None, rebuild=False):
    """Runs for the window, rebuilt from the transcripts' Agent calls; files already present (by id) are kept,
    unless rebuild: then every file an earlier import wrote (never one the widget saved) is removed first."""
    if rebuild:
        for p in files(runs_dir):
            if p.name.endswith('-transcript.json'):
                p.unlink()
    if calls is None:
        sys.path.insert(0, str(HERE))
        import consumption  # noqa: E402
        calls = consumption.collect(days)['subagents']['calls']
    have = {r['id'] for r in list_runs(runs_dir)}
    written = []
    for run in group(calls):
        if run['meta']['id'] in have:
            continue
        day = when(run['meta']['startedAt'])[:10]
        path = Path(runs_dir or RUNS) / day / f"{when(run['meta']['startedAt'])[11:].replace(':', '')}00-{slug(run['meta']['prompt'])}-transcript.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        run['meta']['saved'] = str(path)
        path.write_text(json.dumps(run, indent=1), encoding='utf-8')
        written.append(path)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=['list', 'show', 'export', 'import'])
    ap.add_argument('words', nargs='*')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--out-dir', default='docs/runs')
    ap.add_argument('--rebuild', action='store_true', help='import: drop the files an earlier import wrote and rebuild them')
    a = ap.parse_args(argv)
    if a.verb == 'list':
        rows = list_runs()
        if a.json:
            print(json.dumps(rows))
            return
        if not rows:
            print(f"no saved run under {RUNS}")
            return
        for r in rows:
            print(f"{when(r['startedAt'])}  {(('task ' + r['name']) if r['name'] else r['prompt'])[:60]:60}  {r['agentN']:3} agents  {money(r['cost']):>6}  {'from transcripts' if r['source'] == 'transcript' else '':16}  {r['id']}")
    elif a.verb == 'show':
        if not a.words:
            raise SystemExit('show needs the run id')
        run, _ = find(a.words[0])
        print(text(run))
    elif a.verb == 'export':
        if not a.words:
            raise SystemExit('export needs the run id')
        run, _ = find(a.words[0])
        print(f"report written: {export(run, a.out_dir)}")
    else:
        written = import_runs(a.days, rebuild=a.rebuild)
        print(f"{len(written)} run(s) rebuilt from the last {a.days} days of transcripts into {RUNS}" + (f"; the first: {written[0]}" if written else ' (nothing new: every run of the window is already saved)'))


if __name__ == '__main__':
    main()
