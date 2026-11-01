"""Write-tests family, agent arm. The agent, inside its own worktree of Linux
v6.12 with the placeholder lib/agent_kunit.c already wired into the build,
must write a KUnit suite for one function. Read/Glob/Grep/Edit/Write, no
Bash. The receipt stores the test file it wrote and any other changes.

--kunit lets the agent build and run its suite (Bash restricted to kunit.py).
--harness codex runs the same tasks through the OpenAI Codex CLI
(bench/common/harness.py) in a workspace-write sandbox; with --kunit the build
dir is an extra writable root, but the UML kernel cannot boot in Codex's sandbox
(ptrace is blocked), so --kunit through Codex also needs --codex-full-access,
which drops the sandbox. Same receipt shape, plus `harness`.

Usage: python3 run_agent.py --model M --effort E --worktree DIR [--trial N] [--ids ...]
       [--kunit --build-dir DIR] [--harness claude|codex [--codex-full-access]]
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
sys.path.insert(0, str(HERE))
import harness  # noqa: E402
import worktree as W  # noqa: E402
import wiring  # noqa: E402

PROMPT = """You are working inside a full checkout of the Linux kernel v6.12 (your current working directory).

Write a KUnit test suite for the function `{function}` defined in {file}. Write it in the file lib/agent_kunit.c, which already exists as a placeholder and is already wired into the build as CONFIG_AGENT_KUNIT_TEST (see lib/Makefile and lib/Kconfig.debug). Name the suite "agent_test". Cover normal inputs, boundaries and error paths thoroughly: a good suite fails if the function has an off-by-one or a wrong comparison. Do not modify any other file. Do not use the web. You cannot run the build or the tests in this session.

When finished, reply with ONLY a JSON object: {{"test_cases": <number of KUNIT_CASE entries you wrote>, "summary": "<one sentence>"}}."""

KUNIT_HINT = """You CAN build and run your suite in this session with exactly this command (it takes about a minute):

    python3 tools/testing/kunit/kunit.py run --kunitconfig=agent.kunitconfig --build_dir={build_dir} --jobs=8

Run it, read the output, and fix your suite until every case passes on the current code. A suite that fails on the current code is worthless."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', required=True, choices=['low', 'medium', 'high', 'xhigh', 'max'])
    ap.add_argument('--worktree', type=Path, required=True)
    ap.add_argument('--tasks', type=Path, default=HERE / 'tasks.json')
    ap.add_argument('--ids', nargs='*', default=None)
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--max-turns', type=int, default=30)
    ap.add_argument('--tools', default='Read Glob Grep Edit Write')
    ap.add_argument('--timeout', type=int, default=1500)
    ap.add_argument('--out', type=Path, default=HERE.parents[1] / 'runs/write_tests')
    ap.add_argument('--kunit', action='store_true',
                    help='let the agent build and run its suite (Bash restricted to kunit.py)')
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
        args.timeout = max(args.timeout, 3600)
    tasks = json.loads(args.tasks.read_text())['tasks']
    if args.ids:
        tasks = [t for t in tasks if t['id'] in set(args.ids)]
    args.out.mkdir(parents=True, exist_ok=True)
    suffix = '' if variant == 'noexec' else '-' + variant
    out = args.out / f'runs-{args.model}-{args.effort}{suffix}-t{args.trial}.jsonl'
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
            wiring.apply(wt)
            if args.kunit:
                (Path(wt) / 'agent.kunitconfig').write_text((HERE / 'kunitconfig').read_text())
            W.git(wt, 'add', '-A')
            W.git(wt, '-c', 'user.email=bench@local', '-c', 'user.name=bench',
                  'commit', '-qm', 'wiring')
            prompt = PROMPT.format(function=task['function'], file=task['file'])
            if args.kunit:
                prompt = prompt.replace('You cannot run the build or the tests in this session.',
                                        KUNIT_HINT.format(build_dir=args.build_dir))
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
            test_file = (Path(wt) / 'lib/agent_kunit.c').read_text()
            status = W.git(wt, 'status', '--porcelain').stdout
            changed = [l[3:].strip() for l in status.splitlines()]
            other_patch = W.git(wt, 'diff', 'HEAD', '--', '.', ':!lib/agent_kunit.c').stdout
            changed = [c for c in changed if c != 'agent.kunitconfig']
            record = {'id': task['id'], 'family': 'write_tests', 'bench': 'write_tests', 'arm': 'T',
                      'model_requested': args.model, 'effort': args.effort,
                      'harness': args.harness, 'variant': variant,
                      'trial': args.trial, 'tools': args.tools, 'max_turns': args.max_turns,
                      'prompt_chars': len(prompt),
                      'wall_seconds': round(time.perf_counter() - start, 2),
                      'changed_files': changed, 'test_file': test_file,
                      'other_patch': other_patch, **reply}
            W.reset(wt)
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(args.model, args.effort, task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s turns={record.get('num_turns')} "
                  f"cost={record.get('cost_usd')} changed={changed} "
                  f"test_bytes={len(test_file)}", flush=True)


if __name__ == '__main__':
    main()
