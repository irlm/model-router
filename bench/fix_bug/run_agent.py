"""Bug-fix family, agent arm. For each of the 10 K2 tasks: seed the verified
bug into this model's own git worktree of Linux v6.12 and commit it, run the
agent inside the worktree with Read/Glob/Grep/Edit (no Bash: it cannot run
the tests), give it only the suite name and the real failing KUnit output,
then record its patch (git diff) and reset the worktree. Resumable.

Usage: python3 run_agent.py --model M --effort E --worktree DIR [--trial N] [--ids ...]
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import worktree as W  # noqa: E402

PROMPT = """You are working inside a full checkout of the Linux kernel v6.12 (your current working directory).

The KUnit test suite `{suite}` fails. Failing output:

{failing_output}

Find the bug in the kernel source and fix it with a minimal change. Do not modify any test code (files named *_kunit.c or *test*.c, or anything under lib/kunit or tools/testing). Do not use the web. You cannot run the build or the tests in this session, so reason from the source and the failing output.

When finished, reply with ONLY a JSON object: {{"changed_files": ["path", ...], "summary": "<one sentence>"}} or {{"unknown": true}} if you cannot find the bug."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', required=True, choices=['low', 'medium', 'high', 'xhigh', 'max'])
    ap.add_argument('--worktree', type=Path, required=True)
    ap.add_argument('--tasks', type=Path, default=HERE / 'tasks.json')
    ap.add_argument('--ids', nargs='*', default=None)
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--max-turns', type=int, default=30)
    ap.add_argument('--tools', default='Read Glob Grep Edit')
    ap.add_argument('--timeout', type=int, default=1500)
    ap.add_argument('--out', type=Path, default=HERE.parents[1] / 'runs/fix_bug')
    args = ap.parse_args()
    tasks = json.loads(args.tasks.read_text())['tasks']
    if args.ids:
        tasks = [t for t in tasks if t['id'] in set(args.ids)]
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f'runs-{args.model}-{args.effort}-t{args.trial}.jsonl'
    kept = []
    if out.exists():
        kept = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept))
    done = {r['id'] for r in kept}
    wt = args.worktree
    with out.open('a') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            W.reset(wt)
            W.seed_mutation(wt, task)
            W.git(wt, '-c', 'user.email=bench@local', '-c', 'user.name=bench',
                  'commit', '-qam', 'seed')
            prompt = PROMPT.format(suite=task['suite'], failing_output=task['failing_output'])
            start = time.perf_counter()
            try:
                reply = W.call_claude(prompt, args.model, args.effort, args.max_turns,
                                      args.tools, args.timeout, wt)
            except Exception as error:
                reply = {'text': '', 'usage': None, 'cost_usd': None,
                         'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            patch = W.git(wt, 'diff', 'HEAD').stdout
            status = W.git(wt, 'status', '--porcelain').stdout
            changed = [l[3:].strip() for l in status.splitlines()]
            record = {'id': task['id'], 'family': 'fix_bug', 'bench': 'fix_bug', 'arm': 'T',
                      'model_requested': args.model, 'effort': args.effort,
                      'trial': args.trial, 'tools': args.tools, 'max_turns': args.max_turns,
                      'prompt_chars': len(prompt),
                      'wall_seconds': round(time.perf_counter() - start, 2),
                      'changed_files': changed, 'patch': patch, **reply}
            W.reset(wt)
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(args.model, args.effort, task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s turns={record.get('num_turns')} "
                  f"cost={record.get('cost_usd')} changed={changed}", flush=True)


if __name__ == '__main__':
    main()
