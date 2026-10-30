"""Seed verified bugs into kernel lib code for K2.

A candidate mutation survives only if it (a) compiles, (b) makes its
paired KUnit suite FAIL, and (c) the file restored byte-identical
passes again (baseline pass is checked once per suite up front).
Each kept task records the mutated function source and the real
failing KUnit output - the model never sees the pristine function or
the mutation. Usage:
  python3 mutate.py --tree DIR [--seed N] [--per-target N] [--out F]
"""
import argparse
import difflib
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kunit_lab

TARGETS = [
    {'file': 'lib/string.c', 'suite': 'string',
     'functions': ['strncasecmp', 'strcspn', 'strpbrk', 'strlcat']},
    {'file': 'lib/string_helpers.c', 'suite': 'string_helpers',
     'functions': ['string_get_size', 'string_unescape', 'string_escape_mem']},
    {'file': 'lib/cmdline.c', 'suite': 'cmdline',
     'functions': ['get_option', 'get_options', 'memparse']},
    {'file': 'lib/siphash.c', 'suite': 'siphash',
     'functions': ['__siphash_aligned', '__hsiphash_aligned']},
    # rational dropped: RATIONAL is a hidden Kconfig symbol with no
    # UML-reachable selector, so its KUnit suite cannot build here.
]
# (pattern, replacement, label) - one site changed per candidate.
MUTATIONS = [
    (r'<=', '<', 'le-to-lt'), (r'>=', '>', 'ge-to-gt'),
    (r'(?<![<>=!])<(?![<=])', '<=', 'lt-to-le'),
    (r'(?<![<>=!-])>(?![>=])', '>=', 'gt-to-ge'),
    (r'==', '!=', 'eq-to-ne'), (r'!=', '==', 'ne-to-eq'),
    (r'\+ 1\b', '+ 2', 'plus1-to-plus2'), (r'- 1\b', '- 2', 'minus1-to-minus2'),
    (r'\+\+', '--', 'inc-to-dec'), (r'&&', '||', 'and-to-or'),
]


def candidates(function_text):
    """Yield (mutated_text, label, site_index) deterministically."""
    for pattern, repl, label in MUTATIONS:
        sites = list(re.finditer(pattern, function_text))
        for index, site in enumerate(sites):
            yield (function_text[:site.start()] + repl
                   + function_text[site.end():], label, index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=20261009)
    ap.add_argument('--per-target', type=int, default=4)
    ap.add_argument('--out', type=Path,
                    default=Path(__file__).resolve().parents[2]
                    / 'results/kernel-edit/tasks.json')
    args = ap.parse_args()
    tree, rng = str(args.tree), random.Random(args.seed)
    tasks = []
    for target in TARGETS:
        baseline = kunit_lab.run_suite(tree, target['suite'])
        assert baseline['passed'], f"baseline FAILS: {target['suite']}"
        file = Path(tree) / target['file']
        pristine = file.read_text()
        kept = 0
        functions = list(target['functions'])
        rng.shuffle(functions)
        for name in functions:
            if kept >= args.per_target:
                break
            span = kunit_lab.function_span(pristine, name)
            if span is None:
                print(f'skip {name}: no span', flush=True)
                continue
            original = pristine[span[0]:span[1]]
            pool = list(candidates(original))
            rng.shuffle(pool)
            for mutated, label, site in pool[:6]:
                file.write_text(pristine[:span[0]] + mutated + pristine[span[1]:])
                result = kunit_lab.run_suite(tree, target['suite'])
                file.write_text(pristine)
                if result['passed']:
                    print(f'  {name} {label}@{site}: survived, discard', flush=True)
                    continue
                kept += 1
                tasks.append({
                    'id': f"edit-{target['suite']}-{kept:02d}-{name}",
                    'file': target['file'], 'function': name,
                    'suite': target['suite'], 'mutation': label,
                    'mutated_function': mutated,
                    'original_function': original,  # oracle only, never in prompts
                    'failing_output': result['output_tail'],
                    'diff_lines': sum(1 for _ in difflib.unified_diff(
                        original.splitlines(), mutated.splitlines(), n=0)) - 2,
                })
                print(f'KEPT {tasks[-1]["id"]} ({label}@{site})', flush=True)
                break
        assert file.read_text() == pristine, f'tree dirty: {target["file"]}'
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {'tree': tree, 'seed': args.seed, 'tasks': tasks}, indent=1))
    print(json.dumps({'tasks': len(tasks)}))


if __name__ == '__main__':
    main()
