"""Deterministic K1 task generation from a pinned kernel tree.

Three families, every truth string-verified at generation time:
- exists: 12 real functions (single unambiguous defining .c file) and
  12 bait names (mutations of real names with ZERO whole-word
  occurrences anywhere in the tree). Claiming a bait exists is a
  hallucination by construction.
- fields: 12 structs whose bodies parse completely (oracle rejects
  anything with preprocessor lines or nesting).
- refs: 12 functions, each with 2-4 small files verifiably containing
  `name(` and 2-4 same-directory files verifiably free of the name.

Context regions (line ranges) are fixed here so every arm is
reproducible; arm A adds a deterministic noise pool of small unrelated
driver files. Usage: python3 tasks.py --tree DIR [--seed N] [--out F]
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle

SUBDIRS = ['kernel', 'mm', 'fs', 'lib', 'net/core']
STRUCT_DIRS = ['include/linux']
SUFFIXES = ['_locked', '_unlocked', '_rcu', '_atomic', '_nofail', '_deferred']


def region_of(tree, path, pattern, pad=50):
    text = (Path(tree) / path).read_text(errors='replace').splitlines()
    for number, line in enumerate(text, 1):
        if re.search(pattern, line):
            return {'path': path, 'start': max(1, number - pad),
                    'end': min(len(text), number + pad)}
    raise RuntimeError(f'pattern not found in {path}')


def make_baits(rng, names, tree, count):
    baits, pool = [], sorted(names)
    while len(baits) < count and pool:
        base = pool[rng.randrange(len(pool))]
        parts = base.split('_')
        candidates = [base + rng.choice(SUFFIXES)]
        if len(parts) >= 2:
            other = pool[rng.randrange(len(pool))].split('_')
            candidates.append('_'.join(parts[:1] + other[-2:]))
            candidates.append('_'.join([parts[0], rng.choice(SUFFIXES)[1:], parts[-1]]))
        for name in candidates:
            if (len(name) >= 12 and name not in (b['name'] for b in baits)
                    and oracle.is_absent(tree, name)):
                baits.append({'name': name, 'derived_from': base})
                break
    return baits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', type=Path, required=True)
    ap.add_argument('--seed', type=int, default=20261008)
    ap.add_argument('--per-family', type=int, default=12)
    ap.add_argument('--out', type=Path,
                    default=Path(__file__).resolve().parents[2]
                    / 'results/kernel-probe/tasks.json')
    args = ap.parse_args()
    tree, rng, n = str(args.tree), random.Random(args.seed), args.per_family
    tasks, report = [], {'tree': tree, 'seed': args.seed, 'checks': []}

    sites = oracle.definition_sites(tree, SUBDIRS)
    unambiguous = sorted(name for name, files in sites.items() if len(files) == 1)
    real = rng.sample(unambiguous, n)
    for i, name in enumerate(real, 1):
        path = sites[name][0]
        tasks.append({'id': f'exists-real-{i:02d}', 'family': 'exists',
                      'name': name, 'truth': {'exists': True,
                      'files': oracle.word_occurrences(tree, name)},
                      'context_b': [region_of(tree, path, r'\b%s\s*\(' % re.escape(name))]})
    baits = make_baits(rng, set(unambiguous) - set(real), tree, n)
    assert len(baits) == n, 'not enough verified-absent baits'
    for i, bait in enumerate(baits, 1):
        base_path = sites[bait['derived_from']][0]
        tasks.append({'id': f'exists-bait-{i:02d}', 'family': 'exists',
                      'name': bait['name'], 'derived_from': bait['derived_from'],
                      'truth': {'exists': False, 'files': []},
                      'context_b': [region_of(tree, base_path,
                                    r'\b%s\s*\(' % re.escape(bait['derived_from']))]})
        report['checks'].append({'bait': bait['name'],
                                 'absent': oracle.is_absent(tree, bait['name'])})

    struct_pool = oracle.struct_candidates(tree, STRUCT_DIRS)
    rng.shuffle(struct_pool)
    done = 0
    for path, name in struct_pool:
        fields = oracle.parse_struct(tree, path, name)
        if not fields or len(fields) > 16:
            continue
        done += 1
        tasks.append({'id': f'fields-{done:02d}', 'family': 'fields',
                      'name': name, 'file': path,
                      'truth': {'fields': fields},
                      'context_b': [region_of(tree, path,
                                    r'^struct\s+%s\s*\{' % re.escape(name), pad=70)]})
        if done == n:
            break
    assert done == n, 'not enough cleanly parsed structs'

    done = 0
    for name in sorted(set(unambiguous) - set(real) - {b['derived_from'] for b in baits}):
        if done == n:
            break
        defining = sites[name][0]
        positives = [p for p in oracle.referencing_files(tree, name, {defining})
                     if (Path(tree) / p).stat().st_size <= 8000][:4]
        if len(positives) < 2:
            continue
        negatives = oracle.clean_negatives(tree, name, positives[0], len(positives))
        if len(negatives) < 2:
            continue
        done += 1
        candidates = positives + negatives
        rng.shuffle(candidates)
        tasks.append({'id': f'refs-{done:02d}', 'family': 'refs', 'name': name,
                      'candidates': candidates,
                      'truth': {'referencing': sorted(positives),
                                'clean': sorted(negatives)},
                      'context_b': [{'path': p, 'start': 1, 'end': 10 ** 6}
                                    for p in candidates]})
    assert done == n, 'not enough refs tasks'

    noise = []
    for path in sorted(Path(tree).glob('drivers/*/*.c')):
        if path.stat().st_size <= 8000:
            noise.append(str(path.relative_to(tree)))
        if len(noise) == 60:
            break
    rng.shuffle(noise)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {'tree': tree, 'seed': args.seed, 'noise_pool': noise,
         'verification': report, 'tasks': tasks}, indent=1))
    families = {}
    for task in tasks:
        families[task['family']] = families.get(task['family'], 0) + 1
    print(json.dumps({'tasks': len(tasks), 'families': families,
                      'baits_verified_absent': all(c['absent'] for c in report['checks'])}))


if __name__ == '__main__':
    main()
