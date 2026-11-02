"""Grade research_synthesis receipts in code, no judge model. Each of the note's three answers must
match its web_research pattern, and a page cited for it must fetch and state it (the same checker as
bench/web_research/grade.py); the note itself must be prose of 200 to 1000 words. Outcomes:
  correct          every answer right and stated by a cited page, the note within length
  length           every answer right and sourced, but the note is too short or too long
  right-unsourced  every answer right, at least one with no cited page that states it
  partial          some answers right, some wrong
  wrong            no answer right
  unparseable      no JSON object with "answers" and "sources" after the note
  operational      the harness failed
Fetched pages are cached in runs/research_synthesis/fetch_cache.json.

Usage: python3 grade.py [--runs DIR] [--only GLOB]
"""
import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'web_research'))
import grade as wr  # noqa: E402  the fetcher and the evidence check, shared with web_research

RUNS = HERE.parents[1] / 'runs/research_synthesis'
WORDS = (200, 1000)


def split_note(text):
    """The prose before the last JSON object that has 'answers', and that object."""
    found = None
    for m in re.finditer(r'\{', text):
        depth = 0
        for i in range(m.start(), len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[m.start():i + 1])
                    except ValueError:
                        break
                    if isinstance(obj, dict) and 'answers' in obj:
                        found = (text[:m.start()], obj)
                    break
    if not found:
        raise ValueError('no JSON object with an answers key')
    return found


def grade_one(task, facts, record, cache):
    if record.get('operational_error'):
        return 'operational', record['operational_error']
    try:
        prose, obj = split_note(record.get('text') or '')
    except ValueError as e:
        return 'unparseable', str(e)
    answers = obj.get('answers') or {}
    sources = obj.get('sources') or {}
    right = sourced = 0
    notes = []
    for i, fid in enumerate(task['facts'], 1):
        f = facts[fid]
        a = str(answers.get(str(i), ''))
        if not any(re.search(p, a, re.I) for p in f['answer_patterns']):
            notes.append(f'{i}: wrong ({a[:40]!r})')
            continue
        right += 1
        urls = [u for u in (sources.get(str(i)) or []) if isinstance(u, str)][:6]
        if any(wr.page_states(f, wr.fetch(u, cache).get('text', '')) for u in urls):
            sourced += 1
        else:
            notes.append(f'{i}: right, no cited page states it')
    words = len(prose.split())
    n = len(task['facts'])
    if sourced == n:
        return ('correct' if WORDS[0] <= words <= WORDS[1] else 'length'), f'{words} words, {n}/{n} sourced'
    if right == n:
        return 'right-unsourced', '; '.join(notes)
    return ('partial' if right else 'wrong'), f'{right}/{n} right; ' + '; '.join(notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--runs', type=Path, default=RUNS)
    args = ap.parse_args()
    tasks = {t['id']: t for t in json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))['tasks']}
    facts = {t['id']: t for t in json.loads((HERE.parent / 'web_research/tasks.json').read_text(encoding='utf-8'))['tasks']}
    cache_file = args.runs / 'fetch_cache.json'
    cache = json.loads(cache_file.read_text(encoding='utf-8')) if cache_file.exists() else {}
    grades_file = args.runs / 'grades.json'
    grades = json.loads(grades_file.read_text(encoding='utf-8')) if grades_file.exists() else {}
    for f in sorted(args.runs.glob('runs-*.jsonl')):
        for line in f.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            pv = r.get('prompt_variant', 'a')
            key = f"{r['model_requested']} / {r['effort']} / {r['trial']} / {r['id']}" + ('' if pv == 'a' else f' / p{pv}')   # report.py's cached-grade key
            if args.only and not fnmatch.fnmatch(r['id'], args.only):
                continue
            if key in grades and grades[key]['outcome'] != 'operational':
                continue
            outcome, detail = grade_one(tasks[r['id']], facts, r, cache)
            grades[key] = {'outcome': outcome, 'detail': detail}
            print(f'{outcome:16} {key}  {detail[:120]}')
    args.runs.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache), encoding='utf-8')
    grades_file.write_text(json.dumps(grades, indent=1, sort_keys=True), encoding='utf-8')
    counts = {}
    for g in grades.values():
        counts[g['outcome']] = counts.get(g['outcome'], 0) + 1
    print('totals:', counts)


if __name__ == '__main__':
    main()
