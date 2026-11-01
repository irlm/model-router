"""Regression check of the routing: run each decided family's default (model,
effort, runner) on a small sample of its own tasks, grade it with the family's
checker, and compare to the evidence the decision rests on. Use it after a
Claude Code update, when a model keeps its id but changes underneath, or
monthly with the ledger. It also records the Claude Code version and the fixed
prefix of a trivial call (the part the agent files inflate, results/prefix).

A family "regressed" when the sample's successes are improbable under the
decided rate: the one-sided binomial tail P(X <= successes | n, p0) is below
--alpha, with p0 = the lower bound of the decided cell's 95% Wilson interval.
Small samples catch only large drops; that is the point: a check that runs in
minutes and costs cents.

Families that need a kernel worktree (fix_bug, write_tests) run only with
--kernel-worktree and --build-dir (their graders use the grade-fix /
build-grade-fix pair beside them); browser families only with --browser
(Chrome open, left alone). Receipts go to runs/regress/<tag>/<bench>/, which
report.py does not read; the summary to ledger/regress-<tag>.md.

Usage: python3 regress.py [--sample 6] [--families find_feature,repo_fix,web_research]
       [--kernel-worktree DIR --build-dir DIR] [--browser] [--alpha 0.05] [--slot e] [--no-prefix]
"""
import argparse
import datetime
import json
import math
import random
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

import decide
import report

HERE = Path(__file__).resolve().parent
PY = sys.executable
CLAUDE = shutil.which('claude') or 'claude'   # PATH lookup: on Windows the CLI is claude.cmd
ID_FOR = {alias: mid for mid, alias in decide.ALIAS.items()}
TASK_FILES = {'find_feature': None, 'fix_bug_hard': 'bench/fix_bug/tasks-hard.json', 'write_tests': 'bench/write_tests/tasks.json',
              'repo_fix': 'bench/repo_fix/tasks.json', 'web_research': 'bench/web_research/tasks.json',
              'browser_flow': 'bench/browser_flow/tasks.json'}


def claude_version():
    try:
        return subprocess.run([CLAUDE, '--version'], capture_output=True, text=True, timeout=30).stdout.split()[0]
    except (OSError, IndexError, subprocess.TimeoutExpired):
        return 'unknown'


def prefix_tokens(n=2):
    """Total input tokens of a one-turn Haiku call from an empty directory, n times."""
    cwd = tempfile.mkdtemp(prefix='prefix_')
    rows = []
    for _ in range(n):
        try:
            p = subprocess.run([CLAUDE, '-p', '--output-format', 'json', '--model', 'claude-haiku-5-5', '--effort', 'low',
                                '--max-turns', '1', '--allowed-tools', 'Read'], input='Reply with the single word OK.',
                               capture_output=True, text=True, timeout=180, cwd=cwd)
            u = json.loads(p.stdout)['usage']
            rows.append(u['input_tokens'] + u['cache_creation_input_tokens'] + u['cache_read_input_tokens'])
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            rows.append(None)
    return rows


def task_ids(bench):
    if bench == 'find_feature':
        return sorted(report.load_ff_tasks()[1])
    return [t['id'] for t in json.loads((HERE / TASK_FILES[bench]).read_text())['tasks']]


def variant_of(requires):
    s = ' '.join(requires or [])
    return 'kunit' if 'KUnit' in s else 'vitest' if 'vitest' in s else ''


def binom_tail(n, s, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(s + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=6)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--families', default='find_feature,repo_fix,web_research')
    ap.add_argument('--kernel-worktree', type=Path, default=None, help='a free linux-v6.12 worktree for the agent (fix_bug, write_tests)')
    ap.add_argument('--build-dir', type=Path, default=None, help='its KUnit build dir')
    ap.add_argument('--browser', action='store_true', help='also run browser_flow (Chrome must be open)')
    ap.add_argument('--slot', default='e', help='repo_fix worktree slot for the agent')
    ap.add_argument('--grade-slot', default='grade')
    ap.add_argument('--alpha', type=float, default=0.05)
    ap.add_argument('--no-prefix', action='store_true')
    ap.add_argument('--tag', default=None)
    args = ap.parse_args()
    version = claude_version()
    tag = args.tag or f"{datetime.date.today().isoformat()}-claude-{version}"
    out_root = HERE / 'runs/regress' / tag
    routing = json.loads((HERE / 'routing.json').read_text())
    lines = [f'# Regression check {tag}', '', f'Claude Code {version}, sample {args.sample} tasks per family, seed {args.seed}, alpha {args.alpha}.', '']
    if not args.no_prefix:
        pre = prefix_tokens()
        lines += [f"Fixed prefix of a trivial Haiku call (input + cache write + cache read): {', '.join(str(x) for x in pre)} tokens.", '']
    lines += ['| Family | Default | Sample | Successes | Decided rate (95% CI) | P(this few) | Verdict | Cost $ |', '|---|---|---|---|---|---|---|---|']
    for fam in [f.strip() for f in args.families.split(',') if f.strip()]:
        rf = routing['families'].get(fam) or {}
        d = rf.get('default')
        if not d or not rf.get('decided'):
            lines.append(f'| {fam} | none decided | | | | | skipped | |')
            continue
        model, effort, variant = ID_FOR.get(d['model'], d['model']), d['effort'], variant_of(rf.get('requires'))
        bench = decide.FAMILIES[fam]['benches'][0]
        if bench in ('fix_bug_hard', 'write_tests') and not (args.kernel_worktree and args.build_dir):
            lines.append(f'| {fam} | {d["model"]} {effort} | | | | | skipped: needs --kernel-worktree and --build-dir | |')
            continue
        if bench == 'browser_flow' and not args.browser:
            lines.append(f'| {fam} | {d["model"]} {effort} | | | | | skipped: needs --browser | |')
            continue
        ids = sorted(random.Random(args.seed).sample(task_ids(bench), min(args.sample, len(task_ids(bench)))))
        out = out_root / bench
        common = ['--model', model, '--effort', effort, '--ids', *ids, '--out', str(out), '--trial', '1']
        if bench == 'find_feature':
            run = [PY, 'bench/find_feature/run_agent.py', *common]
            grade = None
        elif bench == 'fix_bug_hard':
            wt, bd = args.kernel_worktree, args.build_dir
            gwt, gbd = wt.parent / 'grade-fix', wt.parent / 'build-grade-fix'
            run = [PY, 'bench/fix_bug/run_agent.py', *common, '--worktree', str(wt), '--tasks', 'bench/fix_bug/tasks-hard.json',
                   '--bench', 'fix_bug_hard'] + (['--kunit', '--build-dir', str(bd)] if variant == 'kunit' else [])
            grade = [PY, 'bench/fix_bug/grade.py', '--worktree', str(gwt), '--build-dir', str(gbd), '--runs', str(out), '--tasks', 'bench/fix_bug/tasks-hard.json']
        elif bench == 'write_tests':
            wt, bd = args.kernel_worktree, args.build_dir
            gwt, gbd = wt.parent / 'grade-tests', wt.parent / 'build-grade-tests'
            run = [PY, 'bench/write_tests/run_agent.py', *common, '--worktree', str(wt)] + (['--kunit', '--build-dir', str(bd)] if variant == 'kunit' else [])
            grade = [PY, 'bench/write_tests/grade.py', '--worktree', str(gwt), '--build-dir', str(gbd), '--runs', str(out)]
        elif bench == 'repo_fix':
            run = [PY, 'bench/repo_fix/run_agent.py', *common, '--repo', 'private-ts', '--slot', args.slot] + ([] if variant == 'vitest' else ['--noexec'])
            grade = [PY, 'bench/repo_fix/grade.py', '--repo', 'private-ts', '--slot', args.grade_slot, '--runs', str(out)]
        elif bench == 'web_research':
            run = [PY, 'bench/web_research/run_agent.py', *common]
            grade = [PY, 'bench/web_research/grade.py', '--runs', str(out)]
        elif bench == 'browser_flow':
            run = [PY, 'bench/browser_flow/run_agent.py', *common]
            grade = None
        else:
            lines.append(f'| {fam} | | | | | | skipped: no runner wired | |')
            continue
        print('run', ' '.join(run), flush=True)
        subprocess.run(run, cwd=str(HERE), check=False)
        if grade:
            subprocess.run(grade, cwd=str(HERE), check=False)
        cells = report.load_cells(out_root)
        rows = [x for (b, m, e, t), rs in cells.items() if b == bench for x in rs]
        judged = [x for x in rows if x['outcome'] not in report.NOT_MODEL]
        n, s = len(judged), sum(1 for x in judged if x['outcome'] in report.SUCCESS[bench])
        cost = sum(x['cost'] or 0 for x in rows)
        ev = (rf['decided'].get('evidence') or {}).get(f"{model} {effort}{'+' + variant if variant else ''}") or {}
        p0_lo, p0_hi = report.wilson(ev.get('success', 0), ev.get('n', 0) - ev.get('not_model', 0)) if ev else (None, None)
        if p0_lo is None or n == 0:
            verdict, tail, dec = 'no decided evidence to compare' if p0_lo is None else 'nothing judged', None, '-'
        else:
            tail = binom_tail(n, s, p0_lo)
            verdict = 'REGRESSED' if tail < args.alpha else 'ok'
            dec = f"{ev['success']}/{ev['n'] - ev['not_model']} ({p0_lo:.2f}-{p0_hi:.2f})"
        lines.append(f"| {fam} | {d['model']} {effort}{' +' + variant if variant else ''} | {n} | {s} | {dec} | {'-' if tail is None else f'{tail:.2f}'} | {verdict} | {cost:.3f} |")
        print(lines[-1], flush=True)
    text = '\n'.join(lines) + '\n'
    (HERE / 'ledger').mkdir(exist_ok=True)
    (HERE / 'ledger' / f'regress-{tag}.md').write_text(text)
    print(text)


if __name__ == '__main__':
    main()
