"""Shared helpers: git worktree reset, seeding a K2 mutation, a KUnit run.
The agent call lives in harness.py."""
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


def seed_site(wt, site):
    """Write one mutated function over the pristine one. Returns pristine text."""
    file = Path(wt) / site['file']
    pristine = file.read_text()
    span = kunit_lab.function_span(pristine, site['function'])
    if span is None:
        raise RuntimeError(f"no span for {site['function']} in {site['file']}")
    file.write_text(pristine[:span[0]] + site['mutated_function'] + pristine[span[1]:])
    return pristine


def seed_mutation(wt, task):
    """Seed a task's bug: one site (K2 tasks: file/function/mutated_function at
    the top level) or several (hard tasks: task['sites']), spliced in order so
    two sites in one file both land."""
    for site in task.get('sites') or [task]:
        seed_site(wt, site)


def is_test_path(path):
    p = path.lower()
    return any(x in p for x in TEST_PATTERNS)


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
