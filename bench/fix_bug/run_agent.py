"""Bug-fix family, agent arm. For each of the 10 K2 tasks: seed the verified
bug into this model's own git worktree of Linux v6.12 and commit it, run the
agent inside the worktree with Read/Glob/Grep/Edit (no Bash: it cannot run
the tests), give it only the suite name and the real failing KUnit output,
then record its patch (git diff) and reset the worktree. Resumable.

Hard tier (cell 3): --tasks tasks-hard.json --bench fix_bug_hard. The hard prompt
does not say how many defects there are. --kunit lets the agent build and run the
suite (Bash restricted to kunit.py, absolute --build-dir outside the worktree).

--harness codex runs the same tasks through the OpenAI Codex CLI
(bench/common/harness.py) in a workspace-write sandbox; with --kunit the build
dir is an extra writable root, but the UML kernel cannot boot in Codex's sandbox
(ptrace is blocked), so --kunit through Codex also needs --codex-full-access,
which drops the sandbox. Same receipt shape, plus `harness`.

Usage: python3 run_agent.py --model M --effort E --worktree DIR [--trial N] [--ids ...]
       [--tasks tasks-hard.json --bench fix_bug_hard] [--kunit --build-dir DIR]
       [--harness claude|codex [--codex-full-access]]
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import harness  # noqa: E402
import worktree as W  # noqa: E402

PROMPT = """You are working inside a full checkout of the Linux kernel v6.12 (your current working directory).

The KUnit test suite `{suite}` fails. Failing output:

{failing_output}

Find the bug in the kernel source and fix it with a minimal change. Do not modify any test code (files named *_kunit.c or *test*.c, or anything under lib/kunit or tools/testing). Do not use the web. You cannot run the build or the tests in this session, so reason from the source and the failing output.

When finished, reply with ONLY a JSON object: {{"changed_files": ["path", ...], "summary": "<one sentence>"}} or {{"unknown": true}} if you cannot find the bug."""

PROMPT_HARD = """You are working inside a full checkout of the Linux kernel v6.12 (your current working directory).

The KUnit test suite `{suite}` fails. Failing output:

{failing_output}

Find what is wrong in the kernel source and fix it with minimal changes, so that the suite passes. Do not modify any test code (files named *_kunit.c or *test*.c, or anything under lib/kunit or tools/testing). Do not use the web. You cannot run the build or the tests in this session, so reason from the source and the failing output.

When finished, reply with ONLY a JSON object: {{"changed_files": ["path", ...], "summary": "<one sentence>"}} or {{"unknown": true}} if you cannot find the cause."""

NOEXEC_SENTENCE = 'You cannot run the build or the tests in this session, so reason from the source and the failing output.'
KUNIT_HINT = """You CAN build and run the suite in this session with exactly this command (it takes about a minute):

    python3 tools/testing/kunit/kunit.py run --kunitconfig=agent.kunitconfig --build_dir={build_dir} --jobs=8 {suite}

Use it to confirm your fix before you finish."""


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
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--bench', default='fix_bug', help='receipt bench name and runs/ subfolder')
    ap.add_argument('--kunit', action='store_true',
                    help='let the agent build and run the suite (Bash restricted to kunit.py)')
    ap.add_argument('--build-dir', type=Path, default=None,
                    help='absolute build dir outside the worktree, used with --kunit')
    ap.add_argument('--harness', default='claude', choices=harness.harnesses(need=('write',)))
    ap.add_argument('--codex-full-access', action='store_true',
                    help='with --harness codex: no sandbox at all (danger-full-access). Needed for --kunit, '
                         'because the Codex sandbox blocks ptrace and the UML kernel cannot boot in it. '
                         'The model then runs as your user on the whole machine, not just in the worktree.')
    args = ap.parse_args()
    if args.harness == 'codex' and args.kunit and not args.codex_full_access:
        ap.error('--kunit through codex needs --codex-full-access: the Codex sandbox blocks ptrace, '
                 'so KUnit\'s UML kernel cannot boot inside it (bench/common/harness.py)')
    variant = 'kunit' if args.kunit else 'noexec'
    if args.kunit:
        assert args.build_dir and args.build_dir.is_absolute(), '--kunit needs an absolute --build-dir'
        args.tools = args.tools + ' Bash(python3 tools/testing/kunit/kunit.py:*)'
    args.out = args.out or HERE.parents[1] / 'runs' / args.bench
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
    wt = args.worktree
    with out.open('a', encoding='utf-8') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            W.reset(wt)
            W.seed_mutation(wt, task)
            W.git(wt, '-c', 'user.email=bench@local', '-c', 'user.name=bench',
                  'commit', '-qam', 'seed')
            if args.kunit:
                (Path(wt) / 'agent.kunitconfig').write_text((HERE / 'kunitconfig').read_text(encoding='utf-8'), encoding='utf-8')
            template = PROMPT_HARD if task.get('kind') else PROMPT
            prompt = template.format(suite=task['suite'], failing_output=task['failing_output'])
            if args.kunit:
                prompt = prompt.replace(NOEXEC_SENTENCE, KUNIT_HINT.format(
                    build_dir=args.build_dir, suite=task['suite']))
                assert NOEXEC_SENTENCE not in prompt
            start = time.perf_counter()
            try:
                reply = harness.run(args.harness, prompt, args.model, args.effort, args.max_turns,
                                    args.tools, args.timeout, wt, write=True,
                                    writable=[args.build_dir] if args.kunit else [],
                                    unsandboxed=args.codex_full_access)
            except Exception as error:
                reply = {'text': '', 'usage': None, 'cost_usd': None,
                         'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            patch = W.git(wt, 'diff', 'HEAD').stdout
            status = W.git(wt, 'status', '--porcelain').stdout
            changed = [l[3:].strip() for l in status.splitlines()]
            changed = [c for c in changed if c != 'agent.kunitconfig']
            record = {'id': task['id'], 'family': args.bench, 'bench': args.bench, 'arm': 'T',
                      'kind': task.get('kind', 'single'), 'variant': variant,
                      'model_requested': args.model, 'effort': args.effort,
                      'harness': args.harness,
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
