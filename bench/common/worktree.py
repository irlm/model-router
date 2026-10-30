"""Shared helpers: git worktree reset, seeding a K2 mutation, claude -p call."""
import json
import subprocess
from pathlib import Path

import kunit_lab

BASE = 'adc218676'  # Linux 6.12 tag in the pinned tree
TEST_PATTERNS = ('_kunit.c', 'test', 'lib/kunit/', 'tools/testing/')


def git(wt, *args, check=True):
    return subprocess.run(['git', '-C', str(wt), *args], text=True,
                          capture_output=True, stdin=subprocess.DEVNULL,
                          check=check)


def reset(wt, base=BASE):
    git(wt, 'reset', '-q', '--hard', base)
    git(wt, 'clean', '-qfd')


def seed_mutation(wt, task):
    """Write the K2 mutated function over the pristine one. Returns pristine."""
    file = Path(wt) / task['file']
    pristine = file.read_text()
    span = kunit_lab.function_span(pristine, task['function'])
    if span is None:
        raise RuntimeError(f"no span for {task['function']} in {task['file']}")
    file.write_text(pristine[:span[0]] + task['mutated_function'] + pristine[span[1]:])
    return pristine


def is_test_path(path):
    p = path.lower()
    return any(x in p for x in TEST_PATTERNS)


def call_claude(prompt, model, effort, max_turns, tools, timeout, cwd):
    cmd = ['claude', '-p', '--output-format', 'json', '--model', model,
           '--max-turns', str(max_turns), '--effort', effort,
           '--allowed-tools', tools]
    proc = subprocess.run(cmd, cwd=str(cwd), input=prompt, text=True,
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
            'model_used': ','.join(sorted((data.get('modelUsage') or {}).keys())),
            'operational_error': 'endpoint-error' if data.get('is_error') else None}


def run_suite(wt, build_dir, kunitconfig, suite_glob='', timeout=900, jobs=8):
    cmd = ['python3', 'tools/testing/kunit/kunit.py', 'run',
           f'--kunitconfig={kunitconfig}', f'--build_dir={build_dir}',
           f'--jobs={jobs}']
    if suite_glob:
        cmd.append(suite_glob)
    proc = subprocess.run(cmd, cwd=str(wt), stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=timeout)
    out = proc.stdout + proc.stderr
    tail = '\n'.join(out.splitlines()[-40:])
    return {'passed': proc.returncode == 0, 'output_tail': tail, 'output': out}
