"""Shared helpers for the repo_fix family: one of the user's own repositories
with a test runner, a bug seeded by replacing one source line, the test run
parsed from vitest's JSON reporter. The repo is described by repos/<name>.json."""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_PATTERNS = ('test/', '.test.', '.spec.', '__tests__/')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


def load_repo(name):
    cfg = json.loads((HERE / 'repos' / f'{name}.json').read_text())
    cfg['clone'] = Path(os.path.expanduser(cfg['clone']))
    cfg['worktrees'] = Path(os.path.expanduser(cfg['worktrees']))
    return cfg


def git(wt, *args, check=True):
    proc = subprocess.run(['git', '-C', str(wt), *args], text=True, capture_output=True, stdin=subprocess.DEVNULL)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {wt}: {proc.stderr[-400:]}")
    return proc


def seed_branch(wt):
    return 'seed-' + Path(wt).name


def reset(wt, base):
    """Back to the pinned commit, detached, no seed branch, nothing untracked (ignored files such as the
    node_modules symlink stay)."""
    git(wt, 'checkout', '-qf', '--detach', base)
    git(wt, 'branch', '-qD', seed_branch(wt), check=False)
    git(wt, 'reset', '-q', '--hard', base)
    git(wt, 'clean', '-qfd')


def seed(wt, task):
    f = Path(wt) / task['file']
    lines = f.read_text().split('\n')
    i = task['line'] - 1
    if lines[i] != task['original']:
        raise RuntimeError(f"{task['file']}:{task['line']} does not match the task's original line")
    lines[i] = task['mutated']
    f.write_text('\n'.join(lines))


def commit_seed(wt):
    """Commit the seeded tree as a single commit with no history, so an agent that has git (Codex)
    cannot read the mutation off the log. The agent's work is then `git diff HEAD`."""
    git(wt, 'checkout', '-q', '--orphan', seed_branch(wt))
    git(wt, 'add', '-A')
    git(wt, '-c', 'user.email=bench@local', '-c', 'user.name=bench', '-c', 'core.hooksPath=/dev/null',
        'commit', '-qm', 'seed', '--no-verify')


def is_test_path(path):
    p = path.lower()
    return any(x in p for x in TEST_PATTERNS)


def run_tests(wt, cfg, timeout=600, files=()):
    """Run the suite with vitest's JSON reporter. complete=False means the run produced no report."""
    tmp = Path(tempfile.mkdtemp(prefix='repo_fix_'))
    out = tmp / 'vitest.json'
    cmd = [*cfg['test_cmd'], '--reporter=json', f'--outputFile={out}', *files]
    try:
        proc = subprocess.run(cmd, cwd=str(wt), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {'complete': False, 'timeout': True, 'failed': None, 'passed': None, 'total': None,
                'crashed_files': [], 'failures': [], 'stderr_tail': ''}
    res = {'returncode': proc.returncode, 'complete': False, 'failed': None, 'passed': None, 'total': None,
           'crashed_files': [], 'failures': [], 'stderr_tail': ANSI.sub('', proc.stderr)[-800:]}
    if not out.exists():
        return res
    j = json.loads(out.read_text())
    out.unlink()
    tmp.rmdir()
    res.update(complete=True, failed=j.get('numFailedTests', 0), passed=j.get('numPassedTests', 0),
               total=j.get('numTotalTests', 0), success=bool(j.get('success')),
               failed_suites=j.get('numFailedTestSuites', 0))
    prefix = str(wt).rstrip('/') + '/'
    for tr in j.get('testResults', []):
        rel = (tr.get('name') or '').replace(prefix, '')
        if tr.get('status') == 'failed' and not tr.get('assertionResults'):
            res['crashed_files'].append({'file': rel, 'message': ANSI.sub('', tr.get('message') or '').replace(prefix, '')[:800]})
        for a in tr.get('assertionResults', []):
            if a.get('status') == 'failed':
                msg = '\n'.join(a.get('failureMessages') or [])
                res['failures'].append({'file': rel, 'name': a.get('fullName'),
                                        'message': ANSI.sub('', msg).replace(prefix, '')[:1500]})
    return res


def failing_output(res, max_lines=90):
    """What the agent is shown: the failing tests with their assertion messages (stack lines dropped)."""
    lines = []
    for c in res['crashed_files']:
        lines += [f"FAIL {c['file']} (suite failed to run)", *c['message'].splitlines()[:10], '']
    for f in res['failures']:
        body = [l for l in f['message'].splitlines() if not l.strip().startswith('at ') and not l.strip().startswith('❯')]
        lines += [f"FAIL {f['file']} > {f['name']}", *body[:14], '']
    lines.append(f"Tests  {res['failed']} failed | {res['passed']} passed ({res['total']})")
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ['... (output truncated)']
    return '\n'.join(lines)
