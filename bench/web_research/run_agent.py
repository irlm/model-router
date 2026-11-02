"""web_research family: one technical fact per task, looked up on the web with
Claude Code's WebSearch and WebFetch tools, answered as JSON with the URLs the
agent read. This is the kind of work the user's general-purpose subagents
actually do (tools/usage_scan.py). Graded by bench/web_research/grade.py in
code: the answer pattern plus a fetch of every cited page.

Usage: python3 run_agent.py --model M --effort E [--trial N] [--ids ...] [--max-turns 12]
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import harness  # noqa: E402

PROMPT = """Answer this question by looking it up on the web, not from memory:

{question}

Use web search and read the page(s) that state the answer; prefer the official documentation or the primary source. Then reply with ONLY a JSON object:
{{"answer": "<the value, short>", "sources": ["<url>", ...]}}
where every url is a page you actually read in this session that states the answer. Do not list a page you did not read."""
TOOLS = 'WebSearch WebFetch'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', required=True, choices=['low', 'medium', 'high', 'xhigh', 'max'])
    ap.add_argument('--ids', nargs='*', default=None)
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--max-turns', type=int, default=12)
    ap.add_argument('--timeout', type=int, default=600)
    ap.add_argument('--harness', default='claude', choices=['claude'])
    ap.add_argument('--out', type=Path, default=HERE.parents[1] / 'runs/web_research')
    args = ap.parse_args()
    tasks = json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))['tasks']
    if args.ids:
        tasks = [t for t in tasks if t['id'] in set(args.ids)]
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f'runs-{args.model}-{args.effort}-t{args.trial}.jsonl'
    kept = []
    if out.exists():
        kept = [json.loads(l) for l in out.read_text(encoding='utf-8').splitlines() if l.strip()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept), encoding='utf-8')
    done = {r['id'] for r in kept}
    cwd = Path(tempfile.mkdtemp(prefix='web_research_'))  # an empty directory: no CLAUDE.md, no repo
    with out.open('a', encoding='utf-8') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            prompt = PROMPT.format(question=task['question'])
            start = time.perf_counter()
            try:
                reply = harness.run(args.harness, prompt, args.model, args.effort, args.max_turns, TOOLS, args.timeout, cwd)
            except Exception as error:
                reply = {'text': '', 'usage': None, 'cost_usd': None, 'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            record = {'id': task['id'], 'family': 'web_research', 'bench': 'web_research', 'arm': 'T', 'variant': 'noexec',
                      'model_requested': args.model, 'effort': args.effort, 'harness': args.harness, 'trial': args.trial,
                      'tools': TOOLS, 'max_turns': args.max_turns, 'prompt_chars': len(prompt),
                      'wall_seconds': round(time.perf_counter() - start, 2), **reply}
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(args.model, args.effort, task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s turns={record.get('num_turns')} cost={record.get('cost_usd')} {(record.get('text') or '')[:100]!r}", flush=True)


if __name__ == '__main__':
    main()
