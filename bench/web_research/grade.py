"""Grade web_research receipts in code, no judge model: the answer must match
one of the task's answer patterns, and at least one cited URL must fetch
(HTTP 200) and contain the task's evidence pattern (and every `evidence_also`
pattern) in its visible text. Outcomes:
  correct          right answer, a cited page states it
  right-unsourced  right answer, but no cited page fetches and states it (made-up or wrong URL)
  wrong            answer does not match
  stale            live-* tasks only: an older version than the source shows now (answered from memory)
  unparseable      no JSON object with "answer" and "sources"
  operational      the harness failed
Fetched pages are cached in runs/web_research/fetch_cache.json so regrading
does not refetch. `--self-test` checks the tasks' own truth_url against the
patterns (every task must pass, or its patterns are wrong, not the model).

Usage: python3 grade.py [--self-test] [--only GLOB]
"""
import argparse
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'bench/find_feature'))
RUNS = HERE.parents[1] / 'runs/web_research'
CACHE = RUNS / 'fetch_cache.json'
UA = 'Mozilla/5.0 (X11; Linux x86_64) model-router-grader/1.0'
TAGS = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S | re.I)


def visible_text(raw):
    t = TAGS.sub(' ', raw)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(t))


META_REFRESH = re.compile(r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+url=([^"\'>\s]+)', re.I)


def fetch(url, cache, hops=0):
    """GET the page and keep its visible text. A page that is only a meta-refresh redirect (duckdb.org
    does this for /docs/stable/) is followed once, like a browser would."""
    if url in cache:
        return cache[url]
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,*/*'})
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read(3_000_000).decode('utf-8', 'replace')
            entry = {'status': resp.status, 'text': visible_text(raw)[:400_000], 'final_url': resp.geturl()}
        m = META_REFRESH.search(raw) if len(raw) < 4000 else None
        if m and hops < 1:
            target = m.group(1)
            if target.startswith('/'):
                target = re.match(r'https?://[^/]+', url).group(0) + target
            entry = dict(fetch(target, cache, hops + 1), redirected_from=url)
    except Exception as e:  # noqa: BLE001
        entry = {'status': None, 'error': f'{type(e).__name__}: {str(e)[:120]}', 'text': ''}
    cache[url] = entry
    return entry


def extract_json(text):
    """The first JSON object in the text that has an 'answer' key."""
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
                    if isinstance(obj, dict) and 'answer' in obj:
                        return obj
                    break
    raise ValueError('no JSON object with an answer key')


def live_truth(task, cache):
    """Fetch the live source and extract the current version string; cached per grading run."""
    spec = task['live']
    key = 'live:' + spec['url']
    if key in cache:
        return cache[key]
    req = urllib.request.Request(spec['url'], headers={'User-Agent': UA, 'Accept': 'application/json,*/*'})
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read(3_000_000).decode('utf-8', 'replace')
    pick = spec['pick']
    if spec['kind'] == 'json':
        j = json.loads(raw)
        if pick == 'max_current_latestMinor':
            cur = [v for v in j if v.get('current') and v.get('supported')]
            best = max(cur, key=lambda v: int(v['major']))
            val = f"{best['major']}.{best['latestMinor']}"
        elif pick == 'first_lts_version':
            val = next(v['version'] for v in j if v.get('lts'))
        else:
            val = j
            for part in re.findall(r'\[(\d+)\]|([A-Za-z_]+)', pick):
                val = val[int(part[0])] if part[0] else val[part[1]]
            val = str(val)
    else:  # toml-rust: [pkg.rust] version = "1.95.0 (hash date)"
        m = re.search(r'\[pkg\.rust\]\s*version\s*=\s*"([^"\s]+)', raw)
        val = m.group(1)
    val = re.sub(r'^(go|v)', '', val)
    cache[key] = val
    return val


def versions_in(text):
    return re.findall(r'\b\d+\.\d+(?:\.\d+)?\b', text)


def page_states(task, text):
    ok = any(re.search(p, text, re.I) for p in task['evidence_patterns'])
    return ok and all(re.search(p, text, re.I) for p in task.get('evidence_also', []))


def grade_one(task, record, cache):
    if record.get('operational_error'):
        return 'operational', record['operational_error']
    try:
        obj = extract_json(record.get('text') or '')
    except ValueError as e:
        return 'unparseable', str(e)
    answer = str(obj.get('answer', ''))
    sources = obj.get('sources') or []
    sources = [s for s in sources if isinstance(s, str)][:6]
    if task.get('live'):
        try:
            truth = live_truth(task, cache)
        except Exception as e:  # noqa: BLE001
            return 'operational', f'live source failed: {type(e).__name__}: {str(e)[:100]}'
        task = dict(task, answer_patterns=[re.escape(truth) + r'\b'], evidence_patterns=[re.escape(truth)])
        if not re.search(task['answer_patterns'][0], answer):
            given = versions_in(answer)
            return ('stale' if given else 'wrong'), f'answer: {answer[:80]}; current: {truth}'
    if not any(re.search(p, answer, re.I) for p in task['answer_patterns']):
        return 'wrong', f'answer: {answer[:100]}'
    states = []
    for url in sources:
        entry = fetch(url, cache)
        states.append((url, entry.get('status'), page_states(task, entry.get('text', ''))))
    if any(s[2] for s in states):
        return 'correct', f"{sum(1 for s in states if s[2])}/{len(states)} cited pages state it"
    why = '; '.join(f"{u[:60]} -> {st or err}" for (u, st, _), err in zip(states, [cache[u].get('error', 'fetched, no evidence') for u, _, _ in states])) or 'no sources'
    return 'right-unsourced', why[:300]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--runs', type=Path, default=RUNS, help='receipts and grades.json live here (default runs/web_research)')
    args = ap.parse_args()
    tasks = {t['id']: t for t in json.loads((HERE / 'tasks.json').read_text())['tasks']}
    RUNS.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if args.self_test:
        bad = 0
        for t in tasks.values():
            if t.get('live'):
                try:
                    print(f"{t['id']} live truth now: {live_truth(t, cache)}")
                except Exception as e:  # noqa: BLE001
                    print(f"{t['id']} live source FAILED: {type(e).__name__}: {str(e)[:100]}")
                    bad += 1
                continue
            entry = fetch(t['truth_url'], cache)
            ok = page_states(t, entry.get('text', ''))
            ans = any(re.search(p, t['answer'], re.I) for p in t['answer_patterns'])
            print(f"{t['id']} status={entry.get('status')} evidence={'ok' if ok else 'MISSING'} answer_pattern={'ok' if ans else 'MISSING'} {t['truth_url']}")
            bad += (not ok) or (not ans)
        CACHE.write_text(json.dumps(cache))
        print(f'{len(tasks) - bad}/{len(tasks)} tasks self-test ok')
        return
    grades_path = args.runs / 'grades.json'
    grades = json.loads(grades_path.read_text()) if grades_path.exists() else {}
    for f in sorted(args.runs.glob(f'runs-*{args.only}*.jsonl')):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:  # a receipt still being written by a runner
                continue
            pv = r.get('prompt_variant', 'a')
            key = f"{r['model_requested']} / {r['effort']} / {r['trial']} / {r['id']}" + ('' if pv == 'a' else f' / p{pv}')
            if key in grades or r['id'] not in tasks:
                continue
            outcome, detail = grade_one(tasks[r['id']], r, cache)
            grades[key] = {'outcome': outcome, 'detail': detail}
            grades_path.write_text(json.dumps(grades, indent=1))
            CACHE.write_text(json.dumps(cache))
            print(key, '->', outcome, detail[:100], flush=True)


if __name__ == '__main__':
    main()
