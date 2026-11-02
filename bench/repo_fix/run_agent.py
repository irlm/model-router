"""repo_fix family, agent arm: fix a bug with a failing test in one of the
user's own repositories (repos/<name>.json), the same shape as bench/fix_bug
on the kernel. For each task: reset this slot's worktree to the pinned
commit, seed the mutated line, commit the seeded tree as a single commit with
no history, run the agent inside the worktree with Read/Glob/Grep/Edit and,
unless --noexec, Bash restricted to the test command, give it the failing
output, record its patch (git diff HEAD) and reset. Resumable.

--prompt-variant b asks the same thing in other words (receipts go to bench
repo_fix_pb) to measure how much the wording moves the result.

Usage: python3 run_agent.py --repo <name> --slot a --model M --effort E
       [--noexec] [--prompt-variant a|b] [--trial N] [--ids ...] [--harness claude|codex]
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import harness  # noqa: E402
import repo as R  # noqa: E402

PROMPT = {
    'a': """You are working inside a checkout of `{name}`, a {language} project (your current working directory).

The test suite fails. Failing output:

{failing_output}

Find the bug in the source and fix it with a minimal change. Do not modify any test code (anything under {test_dirs}). Do not use the web. {runner}

When finished, reply with ONLY a JSON object: {{"changed_files": ["path", ...], "summary": "<one sentence>"}} or {{"unknown": true}} if you cannot find the bug.""",
    'b': """The project in your working directory is `{name}` ({language}). Running its tests gives these failures:

{failing_output}

Something in the source is wrong. Change as little as possible so the suite is green again. The tests themselves (everything under {test_dirs}) are correct and must stay as they are. No web access. {runner}

Finish with just this JSON and nothing else: {{"changed_files": ["path", ...], "summary": "<one sentence>"}}, or {{"unknown": true}} if you give up.""",
}
RUNNER = {
    'a': {True: "You CAN run the tests in this session with exactly this command (about 10 seconds; append a test file path to run one file):\n\n    {test_cmd_text}\n\nUse it to confirm your fix before you finish.",
          False: 'You cannot run the tests in this session, so reason from the source and the failing output.'},
    'b': {True: "The tests can be run here, only with this exact command (about 10 seconds; add a test file path to run a single file):\n\n    {test_cmd_text}\n\nCheck your change with it before you answer.",
          False: 'There is no way to run the tests here; work from the source and the failures above.'},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--slot', required=True, help='worktree name under the repo config\'s worktrees dir')
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', required=True, choices=['low', 'medium', 'high', 'xhigh', 'max'])
    ap.add_argument('--tasks', type=Path, default=HERE / 'tasks.json')
    ap.add_argument('--ids', nargs='*', default=None)
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--max-turns', type=int, default=30)
    ap.add_argument('--tools', default='Read Glob Grep Edit')
    ap.add_argument('--timeout', type=int, default=1500)
    ap.add_argument('--noexec', action='store_true', help='no test runner for the agent')
    ap.add_argument('--prompt-variant', default='a', choices=['a', 'b'])
    ap.add_argument('--harness', default='claude', choices=harness.harnesses(need=('write',)))
    ap.add_argument('--out', type=Path, default=None)
    args = ap.parse_args()
    cfg = R.load_repo(args.repo)
    wt = cfg['worktrees'] / args.slot
    assert wt.is_dir(), f'no worktree {wt}: {cfg["setup"]}'
    variant = 'noexec' if args.noexec else cfg['test_cmd'][1] if cfg['test_cmd'][0] == 'npx' else cfg['test_cmd'][0]
    if not args.noexec:
        args.tools = args.tools + f" Bash({cfg['test_cmd_text']}:*)"
    bench = 'repo_fix' + ('' if args.prompt_variant == 'a' else '_p' + args.prompt_variant)
    args.out = args.out or HERE.parents[1] / 'runs' / bench
    tasks = json.loads(args.tasks.read_text(encoding='utf-8'))['tasks']
    if args.ids:
        tasks = [t for t in tasks if t['id'] in set(args.ids)]
    args.out.mkdir(parents=True, exist_ok=True)
    suffix = '' if variant == 'noexec' else '-' + variant
    out = args.out / f'runs-{args.model}-{args.effort}{suffix}-t{args.trial}.jsonl'
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
            R.reset(wt, cfg['base'])
            R.seed(wt, task)
            R.commit_seed(wt)
            runner = RUNNER[args.prompt_variant][not args.noexec].format(test_cmd_text=cfg['test_cmd_text'])
            prompt = PROMPT[args.prompt_variant].format(name=cfg['name'], language=cfg['language'], test_dirs=cfg['test_dirs'],
                                                        failing_output=task['failing_output'], runner=runner)
            start = time.perf_counter()
            try:
                reply = harness.run(args.harness, prompt, args.model, args.effort, args.max_turns,
                                    args.tools, args.timeout, wt, write=True)
            except Exception as error:
                reply = {'text': '', 'usage': None, 'cost_usd': None, 'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            patch = R.git(wt, 'diff', 'HEAD').stdout
            changed = [l[3:].strip() for l in R.git(wt, 'status', '--porcelain').stdout.splitlines()]
            record = {'id': task['id'], 'family': 'repo_fix', 'bench': bench, 'repo': args.repo, 'arm': 'T',
                      'variant': variant, 'prompt_variant': args.prompt_variant,
                      'model_requested': args.model, 'effort': args.effort, 'harness': args.harness,
                      'trial': args.trial, 'tools': args.tools, 'max_turns': args.max_turns,
                      'prompt_chars': len(prompt), 'wall_seconds': round(time.perf_counter() - start, 2),
                      'changed_files': changed, 'patch': patch, **reply}
            R.reset(wt, cfg['base'])
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(args.model, args.effort, variant, task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s turns={record.get('num_turns')} cost={record.get('cost_usd')} changed={changed}", flush=True)


if __name__ == '__main__':
    main()
