"""find_feature on a private tree: the contamination control. The Linux tree is in every model's training
data; a repository of your own is not. The same lexical families as bench/find_feature/tasks/lexical.json,
with the truth made mechanically from the tree (a word search), so nothing is hand-classified:
  exists  does a function named X exist anywhere in the repository? (real names, and fakes that do not)
  refs    which of these candidate files reference the function X (a call written `X(`)?
Tasks, receipts and grades stay local (.gitignore): they name files and functions of a private repository.
Only the table (counts) goes into results/.

  python3 private_tree.py make --repo <name> [--want 8] [--seed 42]      -> bench/find_feature/private-tasks.json
  python3 private_tree.py run --model M --effort E [--trial N] [--ids ...] -> runs/find_feature_private/
  python3 private_tree.py grade                                           -> runs/find_feature_private/grades.json
"""
import argparse
import json
import os
import random
import re
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'bench/common'))
import harness  # noqa: E402

TASKS = HERE / 'private-tasks.json'
RUNS = ROOT / 'runs/find_feature_private'
SKIP = ('node_modules', 'dist', 'build', '.git', 'coverage')
EXPORT = re.compile(r'^export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)|^export\s+const\s+(\w+)\s*=\s*(?:async\s*)?\(', re.M)
SCHEMAS = {'exists': '{"exists": true | false | "unknown", "file": "<defining path or unknown>"}',
           'refs': '{"referencing": ["path", ...] | "unknown"}'}
QUESTIONS = {'exists': 'In this repository, does a function named `{name}` exist anywhere in the source (not counting node_modules)?',
             'refs': 'Which of these files contain a reference to the function `{name}` (a call or use written `{name}(`)?\nCandidates: {candidates}'}
ABSTAIN = 'If you cannot determine the answer with certainty, answer "unknown". Guessing is worse than unknown.'


def source_files(tree, exts):
    out = []
    for dirpath, dirs, files in os.walk(tree):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('.')]
        out += [Path(dirpath) / f for f in files if f.endswith(exts)]
    return sorted(out)


def make(args):
    cfg = json.loads((ROOT / 'bench/repo_fix/repos' / f'{args.repo}.json').read_text(encoding='utf-8'))
    tree = Path(os.path.expanduser(cfg['clone']))
    exts = {'TypeScript': ('.ts', '.tsx'), 'Rust': ('.rs',), 'Go': ('.go',), 'Python': ('.py',)}.get(cfg.get('language'), ('.ts',))
    files = source_files(tree, exts)
    texts = {f: f.read_text(encoding='utf-8', errors='replace') for f in files}
    rel = {f: str(f.relative_to(tree)) for f in files}
    defined = {}
    for f, t in texts.items():
        for m in EXPORT.finditer(t):
            name = m.group(1) or m.group(2)
            if name and len(name) > 4:
                defined.setdefault(name, rel[f])
    refs = {}
    for name, where in defined.items():
        pat = re.compile(r'\b' + re.escape(name) + r'\(')
        refs[name] = sorted(rel[f] for f, t in texts.items() if rel[f] != where and pat.search(t))
    rng = random.Random(args.seed)
    usable = sorted(n for n, r in refs.items() if 1 <= len(r) <= 6)
    rng.shuffle(usable)
    tasks = []
    for name in usable[:args.want]:
        tasks.append({'id': f'exists-real-{len(tasks) + 1:02d}', 'family': 'exists', 'name': name, 'truth': {'exists': True, 'file': defined[name]}})
    all_text = '\n'.join(texts.values())
    fakes = 0
    for name in usable[args.want:]:
        fake = name[:-2] + 'ed' if not name.endswith('ed') else name + 'All'
        if fakes >= args.want // 2 + 1:
            break
        if re.search(r'\b' + re.escape(fake) + r'\b', all_text) or fake in defined:
            continue
        fakes += 1
        tasks.append({'id': f'exists-fake-{fakes:02d}', 'family': 'exists', 'name': fake, 'truth': {'exists': False}})
    others = [r for r in rel.values()]
    for i, name in enumerate(usable[args.want:args.want * 2], 1):
        truth = refs[name]
        distract = [p for p in rng.sample(others, min(len(others), 12)) if p not in truth and p != defined[name]][:6 - len(truth)]
        cands = sorted(truth + distract)
        tasks.append({'id': f'refs-{i:02d}', 'family': 'refs', 'name': name, 'candidates': cands, 'truth': {'referencing': truth}})
    spec = {'tree': str(tree), 'repo': args.repo, 'language': cfg.get('language'), 'seed': args.seed,
            'verification': 'exists: the name is defined (export function/const) in the tree, or appears nowhere as a word (fakes); '
                            'refs: candidate files searched for `name(` outside the defining file', 'tasks': tasks}
    TASKS.write_text(json.dumps(spec, indent=1), encoding='utf-8')
    print(f'{len(tasks)} tasks on {len(files)} files of {args.repo}: '
          f"{sum(1 for t in tasks if t['family'] == 'exists' and t['truth']['exists'])} real, "
          f"{sum(1 for t in tasks if t['family'] == 'exists' and not t['truth']['exists'])} fake, "
          f"{sum(1 for t in tasks if t['family'] == 'refs')} refs -> {TASKS.relative_to(ROOT)} (local)")


def run(args):
    spec = json.loads(TASKS.read_text(encoding='utf-8'))
    tree = Path(spec['tree'])
    tasks = [t for t in spec['tasks'] if not args.ids or t['id'] in set(args.ids)]
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f'runs-{args.model}-{args.effort}-t{args.trial}.jsonl'
    kept = [json.loads(l) for l in out.read_text(encoding='utf-8').splitlines() if l.strip()] if out.exists() else []
    kept = [r for r in kept if not r.get('operational_error')]
    out.write_text(''.join(json.dumps(r) + '\n' for r in kept), encoding='utf-8')
    done = {r['id'] for r in kept}
    tools = 'Read Glob Grep'
    with out.open('a', encoding='utf-8') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            q = QUESTIONS[task['family']].format(name=task['name'], candidates=json.dumps(task.get('candidates', [])))
            prompt = '\n\n'.join([f"You answer questions about the {spec['language']} repository in your current working directory. "
                                  'Use your file and search tools to answer. Do not use the web. Do not modify any files.',
                                  ABSTAIN, 'Reply with ONLY a JSON object of the form: ' + SCHEMAS[task['family']], 'Question: ' + q])
            start = time.perf_counter()
            try:
                reply = harness.run('claude', prompt, args.model, args.effort, args.max_turns, tools, args.timeout, tree)
            except Exception as error:
                reply = {'text': '', 'usage': None, 'cost_usd': None, 'operational_error': type(error).__name__}
            record = {'id': task['id'], 'family': task['family'], 'bench': 'find_feature_private', 'arm': 'T', 'variant': 'noexec',
                      'model_requested': args.model, 'effort': args.effort, 'harness': 'claude', 'trial': args.trial, 'tools': tools,
                      'max_turns': args.max_turns, 'prompt_chars': len(prompt), 'wall_seconds': round(time.perf_counter() - start, 2), **reply}
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(args.model, args.effort, task['id'], record.get('operational_error') or 'ok', f"{record['wall_seconds']}s cost={record.get('cost_usd')}", flush=True)


def extract_json(text):
    for m in re.finditer(r'\{', text):
        depth = 0
        for i in range(m.start(), len(text)):
            depth += text[i] == '{'
            depth -= text[i] == '}'
            if depth == 0:
                try:
                    obj = json.loads(text[m.start():i + 1])
                except ValueError:
                    break
                if isinstance(obj, dict):
                    return obj
                break
    raise ValueError('no JSON object')


def grade_one(task, record):
    if record.get('operational_error'):
        return 'operational', record['operational_error']
    try:
        a = extract_json(record.get('text') or '')
    except ValueError as e:
        return 'unparseable', str(e)
    truth = task['truth']
    if task['family'] == 'exists':
        e = a.get('exists')
        if e == 'unknown':
            return 'abstained', ''
        if truth['exists']:
            return ('correct' if e is True else 'wrong'), f"said {e!r}"
        return ('hallucination' if e is True else 'correct' if e is False else 'wrong'), f"said {e!r}"
    named = a.get('referencing')
    if named == 'unknown':
        return 'abstained', ''
    if not isinstance(named, list):
        return 'wrong', 'not a list'
    got, want = set(map(str, named)), set(truth['referencing'])
    if got == want:
        return 'correct', ''
    return ('hallucination' if got - want else 'wrong'), f"missing {sorted(want - got)} extra {sorted(got - want)}"[:200]


def grade(args):
    spec = json.loads(TASKS.read_text(encoding='utf-8'))
    tasks = {t['id']: t for t in spec['tasks']}
    gf = RUNS / 'grades.json'
    grades = json.loads(gf.read_text(encoding='utf-8')) if gf.exists() else {}
    for f in sorted(RUNS.glob('runs-*.jsonl')):
        for line in f.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            key = f"{r['model_requested']} / {r['effort']} / {r['trial']} / {r['id']}"   # report.py's cached-grade key
            outcome, detail = grade_one(tasks[r['id']], r)
            grades[key] = {'outcome': outcome, 'detail': detail}
    gf.write_text(json.dumps(grades, indent=1, sort_keys=True), encoding='utf-8')
    by = {}
    for k, g in grades.items():
        m = k.split(' / ')[0]
        by.setdefault(m, {}).setdefault(g['outcome'], 0)
        by[m][g['outcome']] += 1
    for m, c in sorted(by.items()):
        print(f"{m:22} {c}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('make'); m.add_argument('--repo', required=True); m.add_argument('--want', type=int, default=8); m.add_argument('--seed', type=int, default=42)
    r = sub.add_parser('run'); r.add_argument('--model', required=True); r.add_argument('--effort', required=True)
    r.add_argument('--trial', type=int, default=1); r.add_argument('--ids', nargs='*', default=None); r.add_argument('--max-turns', type=int, default=15); r.add_argument('--timeout', type=int, default=600)
    sub.add_parser('grade')
    args = ap.parse_args()
    {'make': make, 'run': run, 'grade': grade}[args.cmd](args)


if __name__ == '__main__':
    main()
