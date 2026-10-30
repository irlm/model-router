"""Generate verified harder bug tasks for the fix_bug family (cell 3).

Two kinds, both verified by a real build plus KUnit run in a grading worktree:
  hidden: one operator mutation in a helper that no test case names (a static
          helper in the same file, or a callee in another file), so the failing
          output points at a function that is correct.
  multi:  two verified single-site mutations in two different functions covered
          by the same suite, so fixing one of them leaves the suite failing.
A candidate is kept only if the tree compiles and boots, the paired suite reports
[FAILED], and the restored tree passes again. The agent never sees the pristine
function, the diff or this generator.

Usage: python3 make_hard_tasks.py --worktree DIR --build-dir DIR [--seed N] [--out tasks-hard.json]
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import kunit_lab  # noqa: E402
import worktree as W  # noqa: E402

KUNITCONFIG = HERE / 'kunitconfig'
HIDDEN = [
    {'file': 'lib/cmdline.c', 'suite': 'cmdline', 'functions': ['get_range']},
    {'file': 'lib/vsprintf.c', 'suite': 'cmdline',
     'functions': ['simple_strntoull', 'simple_strntoll']},
    {'file': 'lib/kstrtox.c', 'suite': 'cmdline',
     'functions': ['_parse_integer_limit', '_parse_integer_fixup_radix']},
    {'file': 'lib/string_helpers.c', 'suite': 'string_helpers',
     'functions': ['unescape_space', 'unescape_octal', 'unescape_hex', 'unescape_special',
                   'escape_passthrough', 'escape_space', 'escape_special', 'escape_null',
                   'escape_octal', 'escape_hex']},
]
MULTI_QUOTA = {'cmdline': 4, 'string_helpers': 4, 'string': 1, 'siphash': 1}
# (pattern, replacement, label) - one site changed per candidate. Same list as K2.
MUTATIONS = [
    (r'<=', '<', 'le-to-lt'), (r'>=', '>', 'ge-to-gt'),
    (r'(?<![<>=!])<(?![<=])', '<=', 'lt-to-le'),
    (r'(?<![<>=!-])>(?![>=])', '>=', 'gt-to-ge'),
    (r'==', '!=', 'eq-to-ne'), (r'!=', '==', 'ne-to-eq'),
    (r'\+ 1\b', '+ 2', 'plus1-to-plus2'), (r'- 1\b', '- 2', 'minus1-to-minus2'),
    (r'\+\+', '--', 'inc-to-dec'), (r'&&', '||', 'and-to-or'),
]


def candidates(function_text):
    for pattern, repl, label in MUTATIONS:
        for index, site in enumerate(re.finditer(pattern, function_text)):
            yield (function_text[:site.start()] + repl + function_text[site.end():],
                   label, index)


def verify(wt, build_dir, suite, sites):
    """Seed the sites, run the suite, restore. Returns (kept, output_tail)."""
    W.reset(wt)
    try:
        for site in sites:
            W.seed_site(wt, site)
        result = W.run_suite(wt, build_dir, KUNITCONFIG, suite)
    finally:
        W.reset(wt)
    tail = result['output_tail']
    failed = (not result['passed']) and '[FAILED]' in tail and 'Testing complete' in tail
    return failed, tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--worktree', type=Path, required=True)
    ap.add_argument('--build-dir', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=20261030)
    ap.add_argument('--per-function', type=int, default=5)
    ap.add_argument('--out', type=Path, default=HERE / 'tasks-hard.json')
    args = ap.parse_args()
    wt, rng = args.worktree, random.Random(args.seed)
    easy = json.loads((HERE / 'tasks.json').read_text())['tasks']
    tasks, pool = [], {}  # pool: suite -> list of verified single sites
    for t in easy:
        pool.setdefault(t['suite'], []).append(
            {'file': t['file'], 'function': t['function'], 'mutation': t['mutation'],
             'mutated_function': t['mutated_function'],
             'original_function': t['original_function'], 'named': True})

    def save():
        args.out.write_text(json.dumps(
            {'tree': str(wt), 'base': W.BASE, 'seed': args.seed, 'tasks': tasks}, indent=1))

    W.reset(wt)
    for suite in sorted({t['suite'] for t in HIDDEN} | set(MULTI_QUOTA)):
        base = W.run_suite(wt, args.build_dir, KUNITCONFIG, suite)
        assert base['passed'], f'baseline FAILS: {suite}\n{base["output_tail"]}'
        print(f'baseline ok: {suite}', flush=True)

    # hidden: one mutation in a helper no test names
    for target in HIDDEN:
        pristine = (wt / target['file']).read_text()
        for name in target['functions']:
            span = kunit_lab.function_span(pristine, name)
            if span is None:
                print(f'skip {name}: no span', flush=True)
                continue
            original = pristine[span[0]:span[1]]
            cands = list(candidates(original))
            rng.shuffle(cands)
            for mutated, label, index in cands[:args.per_function]:
                t0 = time.time()
                site = {'file': target['file'], 'function': name, 'mutation': label,
                        'mutated_function': mutated, 'original_function': original,
                        'named': False}
                kept, tail = verify(wt, args.build_dir, target['suite'], [site])
                print(f"  hidden {name} {label}@{index}: {'KEPT' if kept else 'discard'} "
                      f'({time.time() - t0:.0f}s)', flush=True)
                if kept:
                    n = sum(1 for t in tasks if t['kind'] == 'hidden' and t['suite'] == target['suite']) + 1
                    tasks.append({'id': f"hard-hidden-{target['suite']}-{n:02d}-{name}",
                                  'kind': 'hidden', 'suite': target['suite'],
                                  'sites': [site], 'failing_output': tail})
                    pool.setdefault(target['suite'], []).append(site)
                    save()
                    break

    # multi: two verified sites in two different functions of one suite
    for suite, quota in MULTI_QUOTA.items():
        sites = pool.get(suite, [])
        pairs = [(a, b) for i, a in enumerate(sites) for b in sites[i + 1:]
                 if a['function'] != b['function'] and (a['named'] or b['named'])]
        rng.shuffle(pairs)
        # named+named first so every suite has at least one, then named+hidden
        pairs.sort(key=lambda p: not (p[0]['named'] and p[1]['named']))
        kept_n = 0
        for a, b in pairs:
            if kept_n >= quota:
                break
            t0 = time.time()
            kept, tail = verify(wt, args.build_dir, suite, [a, b])
            print(f"  multi {suite} {a['function']}+{b['function']}: "
                  f"{'KEPT' if kept else 'discard'} ({time.time() - t0:.0f}s)", flush=True)
            if kept:
                kept_n += 1
                tasks.append({'id': f"hard-multi-{suite}-{kept_n:02d}-{a['function']}+{b['function']}",
                              'kind': 'multi', 'suite': suite, 'sites': [a, b],
                              'failing_output': tail})
                save()

    W.reset(wt)
    for suite in sorted(MULTI_QUOTA):
        assert W.run_suite(wt, args.build_dir, KUNITCONFIG, suite)['passed'], f'restored tree FAILS: {suite}'
    save()
    print(json.dumps({'tasks': len(tasks),
                      'hidden': sum(t['kind'] == 'hidden' for t in tasks),
                      'multi': sum(t['kind'] == 'multi' for t in tasks)}))


if __name__ == '__main__':
    main()
