"""Run one cell of the find-feature family: one model x one effort, agent
with file/search tools inside the pinned Linux v6.12 tree, web off.
Receipt-first and resumable: rerunning skips tasks already recorded
without an operational error. `--harness codex` runs the same tasks through
the OpenAI Codex CLI (bench/common/harness.py); the receipt shape is the same.

Usage:
  python3 run_agent.py --model claude-haiku-5-5 --effort low \
      --tasks tasks/lexical.json tasks/semantic.json --out ../../runs
  python3 run_agent.py --model gpt-6-luna --effort low --harness codex
  python3 run_agent.py ... --ids exists-real-01 callers-01   # smoke
"""
import argparse
import json
import sys
import time
from pathlib import Path

import run_retrieval  # build_prompt_t, restore_tree (K3 arm T contract)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'common'))
import harness  # noqa: E402


def load_tasks(files, ids, limit):
    tree, tasks = None, []
    for f in files:
        spec = json.loads(Path(f).read_text(encoding='utf-8'))
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
    ap.add_argument('--harness', default='claude', choices=sorted(harness.ADAPTERS))
    args = ap.parse_args()

    tree, tasks = load_tasks(args.tasks, args.ids, args.limit)
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f'runs-{args.model}-{args.effort}-t{args.trial}.jsonl'
    kept = []
    if out.exists():
        kept = [json.loads(l) for l in out.read_text(encoding='utf-8').splitlines() if l.strip()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept), encoding='utf-8')
    done = {r['id'] for r in kept}
    with out.open('a', encoding='utf-8') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            prompt = run_retrieval.build_prompt_t(task)
            start = time.perf_counter()
            try:
                reply = harness.run(args.harness, prompt, args.model, args.effort,
                                    args.max_turns, args.tools, args.timeout, tree)
            except Exception as error:  # timeout etc.
                reply = {'text': '', 'usage': None, 'cost_usd': None,
                         'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            record = {'id': task['id'], 'family': task['family'],
                      'bench': 'find_feature', 'arm': 'T',
                      'model_requested': args.model, 'effort': args.effort,
                      'harness': args.harness,
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
