"""Find bugs the repo's own test suite catches: mutate one source line at a time
(comparison, boolean and arithmetic operators, Math.* rounding, negation,
literals, off-by-one), run the suite, keep the mutants that fail between 1 and
--max-failed tests without crashing a whole test file (a syntax error is not a
bug anyone has to find). Writes every killed mutant to mutants.json and a
spread of them (at most --per-file per source file) to tasks.json, each with
the failing output the agent will be shown.

Usage: python3 make_tasks.py --repo <name> --worktree DIR [--want 24] [--max-tries 300] [--seed 42]
"""
import argparse
import json
import random
import re
import time
from pathlib import Path

import repo as R

HERE = Path(__file__).resolve().parent
# (op name, pattern, replacement); the pattern is applied once per match, one mutant per match.
OPS = [
    ('eq->neq', r'===', '!=='),
    ('neq->eq', r'!==', '==='),
    ('le->lt', r'<=', '<'),
    ('ge->gt', r'>=', '>'),
    ('lt->le', r'(?<=[\w)\]]) < (?=[\w(\-])', ' <= '),
    ('gt->ge', r'(?<=[\w)\]]) > (?=[\w(\-])', ' >= '),
    ('and->or', r' && ', ' || '),
    ('or->and', r' \|\| ', ' && '),
    ('plus1->minus1', r'(?<=[\w)\]]) \+ 1\b', ' - 1'),
    ('minus1->plus1', r'(?<=[\w)\]]) - 1\b', ' + 1'),
    ('true->false', r'\breturn true\b', 'return false'),
    ('false->true', r'\breturn false\b', 'return true'),
    ('max->min', r'Math\.max\(', 'Math.min('),
    ('min->max', r'Math\.min\(', 'Math.max('),
    ('round->floor', r'Math\.round\(', 'Math.floor('),
    ('floor->ceil', r'Math\.floor\(', 'Math.ceil('),
    ('ceil->floor', r'Math\.ceil\(', 'Math.floor('),
    ('drop-not', r'if \(!(?=[A-Za-z_])', 'if ('),
    ('length-1', r'\.length\b(?! [-+])', '.length - 1'),
    ('float*1.1', r'(?<![\w.])\d+\.\d+\b', None),
]


def in_string(line, pos):
    return (line[:pos].count('"') + line[:pos].count("'") + line[:pos].count('`')) % 2 == 1


def candidates(wt, cfg, rng):
    out = []
    for f in sorted(Path(wt).glob(cfg['src_glob'])):
        rel = str(f.relative_to(wt))
        if R.is_test_path(rel):
            continue
        for i, line in enumerate(f.read_text().split('\n'), 1):
            s = line.strip()
            if not s or s.startswith(('//', '*', '/*', 'import ', 'export type', 'type ', 'interface ')):
                continue
            for op, pat, repl in OPS:
                for m in re.finditer(pat, line):
                    if in_string(line, m.start()):
                        continue
                    rep = repl if repl is not None else repr(round(float(m.group(0)) * 1.1, 4))
                    mutated = line[:m.start()] + rep + line[m.end():]
                    if mutated != line:
                        out.append({'file': rel, 'line': i, 'op': op, 'original': line, 'mutated': mutated})
    rng.shuffle(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--worktree', type=Path, required=True)
    ap.add_argument('--want', type=int, default=24)
    ap.add_argument('--max-tries', type=int, default=300)
    ap.add_argument('--max-failed', type=int, default=40)
    ap.add_argument('--per-file', type=int, default=2)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--out', type=Path, default=HERE)
    args = ap.parse_args()
    cfg = R.load_repo(args.repo)
    wt = args.worktree
    rng = random.Random(args.seed)
    R.reset(wt, cfg['base'])
    base = R.run_tests(wt, cfg)
    assert base['complete'] and base['failed'] == 0, f'the pristine suite must pass: {base}'
    print(f"pristine: {base['passed']} tests pass", flush=True)
    cands = candidates(wt, cfg, rng)
    print(f'{len(cands)} candidate mutants', flush=True)
    killed, tried, per_file = [], 0, {}
    mpath = args.out / 'mutants.json'
    for c in cands:
        if tried >= args.max_tries or len(killed) >= args.want * 2:
            break
        if per_file.get(c['file'], 0) >= args.per_file:
            continue
        tried += 1
        R.reset(wt, cfg['base'])
        R.seed(wt, c)
        t0 = time.perf_counter()
        res = R.run_tests(wt, cfg)
        R.reset(wt, cfg['base'])
        verdict = ('crash' if not res['complete'] or res['crashed_files'] else
                   'survived' if res['failed'] == 0 else
                   'too-many' if res['failed'] > args.max_failed else 'killed')
        print(f"{tried:3d} {verdict:9} {c['op']:14} {c['file']}:{c['line']} failed={res['failed']} {time.perf_counter() - t0:.0f}s", flush=True)
        if verdict != 'killed':
            continue
        per_file[c['file']] = per_file.get(c['file'], 0) + 1
        killed.append({**c, 'failed': res['failed'], 'failing_tests': [f['name'] for f in res['failures']],
                       'failing_files': sorted({f['file'] for f in res['failures']}),
                       'failing_output': R.failing_output(res)})
        mpath.write_text(json.dumps({'repo': args.repo, 'base': cfg['base'], 'tried': tried, 'mutants': killed}, indent=1))
    # spread: cycle through files, one mutant per file per round, until --want
    by_file = {}
    for k in killed:
        by_file.setdefault(k['file'], []).append(k)
    chosen = []
    while len(chosen) < args.want and any(by_file.values()):
        for f in sorted(by_file):
            if by_file[f] and len(chosen) < args.want:
                chosen.append(by_file[f].pop(0))
    tasks = [{'id': f'{args.repo}-{i:02d}', **k} for i, k in enumerate(chosen, 1)]
    (args.out / 'tasks.json').write_text(json.dumps({'repo': args.repo, 'base': cfg['base'], 'tasks': tasks}, indent=1))
    print(f'{len(killed)} killed of {tried} tried; wrote {len(tasks)} tasks', flush=True)


if __name__ == '__main__':
    main()
