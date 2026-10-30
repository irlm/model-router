"""Run one cell of the find-feature family: one model x one effort, agent
with file/search tools inside the pinned Linux v6.12 tree, web off.
Receipt-first and resumable: rerunning skips tasks already recorded
without an operational error.

Usage:
  python3 run_agent.py --model claude-haiku-5-5 --effort low \
      --tasks tasks/lexical.json tasks/semantic.json --out ../../runs
  python3 run_agent.py ... --ids exists-real-01 callers-01   # smoke
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import run_retrieval  # build_prompt_t, restore_tree (K3 arm T contract)


def call_claude(prompt, model, effort, max_turns, tools, timeout, tree):
    cmd = ['claude', '-p', '--output-format', 'json', '--model', model,
           '--max-turns', str(max_turns), '--effort', effort,
           '--allowed-tools', tools]
    proc = subprocess.run(cmd, cwd=tree, input=prompt, text=True,
                          capture_output=True, timeout=timeout)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return {'text': proc.stdout[-2000:], 'stderr': proc.stderr[-500:],
                'usage': None, 'cost_usd': None,
                'operational_error': 'invalid-endpoint-response'}
    return {'text': data.get('result', ''), 'usage': data.get('usage'),
            'cost_usd': data.get('total_cost_usd'),
            'num_turns': data.get('num_turns'),
            'duration_ms': data.get('duration_ms'),
            'duration_api_ms': data.get('duration_api_ms'),
            'model_used': ','.join(sorted((data.get('modelUsage') or {}).keys())),
            'operational_error': 'endpoint-error' if data.get('is_error') else None}


def load_tasks(files, ids, limit):
    tree, tasks = None, []
    for f in files:
        spec = json.loads(Path(f).read_text())
        if tree is None:
            tree = spec['tree']
        elif spec['tree'] != tree:
            raise SystemExit('task files point at different trees')
        tasks.extend(spec['tasks'])
    if ids:
        wanted = set(ids)
        tasks = [t for t in tasks if t['id'] in wanted]
    if limit:
        tasks = tasks[:limit]
    return tree, tasks


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', required=True,
                    choices=['low', 'medium', 'high', 'xhigh', 'max'])
    ap.add_argument('--tasks', nargs='+', type=Path,
                    default=[here / 'tasks/lexical.json',
                             here / 'tasks/semantic.json'])
    ap.add_argument('--ids', nargs='*', default=None)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--max-turns', type=int, default=15)
    ap.add_argument('--tools', default='Read Glob Grep')
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--out', type=Path, default=here.parents[1] / 'runs/find_feature')
    args = ap.parse_args()

    tree, tasks = load_tasks(args.tasks, args.ids, args.limit)
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f'runs-{args.model}-{args.effort}-t{args.trial}.jsonl'
    kept = []
    if out.exists():
        kept = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept))
    done = {r['id'] for r in kept}
    with out.open('a') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            prompt = run_retrieval.build_prompt_t(task)
            start = time.perf_counter()
            try:
                reply = call_claude(prompt, args.model, args.effort,
                                    args.max_turns, args.tools,
                                    args.timeout, tree)
            except Exception as error:  # timeout etc.
                reply = {'text': '', 'usage': None, 'cost_usd': None,
                         'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            record = {'id': task['id'], 'family': task['family'],
                      'bench': 'find_feature', 'arm': 'T',
                      'model_requested': args.model, 'effort': args.effort,
                      'trial': args.trial, 'tools': args.tools,
                      'max_turns': args.max_turns,
                      'prompt_chars': len(prompt),
                      'wall_seconds': round(time.perf_counter() - start, 2),
                      **reply}
            dirt = run_retrieval.restore_tree(tree)
            if dirt:
                record['tree_dirty'] = dirt[:500]
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(args.model, args.effort, task['id'],
                  record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s",
                  f"turns={record.get('num_turns')}",
                  f"cost={record.get('cost_usd')}", flush=True)


if __name__ == '__main__':
    main()
