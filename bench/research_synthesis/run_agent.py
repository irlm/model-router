"""research_synthesis family: a short research note that answers three questions looked up on the web,
each claim with the page read. The kind of work the user's general-purpose subagents actually do most
(tools/consumption.py: research-synthesis). The questions are bench/web_research's fixed-truth tasks,
so the note is graded in code by bench/research_synthesis/grade.py.

Usage: python3 run_agent.py --model M --effort E [--trial N] [--ids ...] [--prompt-variant a|b]
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

PROMPT = {
 'a': """Write a short research note (250 to 700 words) for a colleague who is {brief}. The note must answer these questions, looked up on the web, not from memory:

{questions}

Use web search and read the pages that state each answer; prefer the official documentation or the primary source. Write the note as prose, with the URL you read right after each claim as (source: URL), and a two-sentence recommendation at the end.

After the note, output exactly one JSON object on its own line:
{{"answers": {{"1": "<the value, short>", "2": "...", "3": "..."}}, "sources": {{"1": ["<url>", ...], "2": [...], "3": [...]}}}}
where every url is a page you actually read in this session that states that answer. Do not list a page you did not read.""",
 'b': """A colleague is {brief} and asked for a short written note (250-700 words). It has to settle these points from the web, each with the page you read, never from memory:

{questions}

Search, open the official documentation or the primary source for each, and write the note as connected prose (not a list), putting the URL you read after each claim like this: (source: URL). Close with a recommendation of two sentences.

Then, on its own line after the note, print one JSON object:
{{"answers": {{"1": "<short value>", "2": "...", "3": "..."}}, "sources": {{"1": ["<url>", ...], "2": [...], "3": [...]}}}}
listing only pages you really opened in this session that state the answer.""",
}
TOOLS = 'WebSearch WebFetch'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', required=True, choices=['low', 'medium', 'high', 'xhigh', 'max'])
    ap.add_argument('--ids', nargs='*', default=None)
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--prompt-variant', default='a', choices=['a', 'b'])
    ap.add_argument('--max-turns', type=int, default=25)
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--harness', default='claude', choices=['claude'])
    ap.add_argument('--out', type=Path, default=HERE.parents[1] / 'runs/research_synthesis')
    args = ap.parse_args()
    tasks = json.loads((HERE / 'tasks.json').read_text(encoding='utf-8'))['tasks']
    facts = {t['id']: t for t in json.loads((HERE.parent / 'web_research/tasks.json').read_text(encoding='utf-8'))['tasks']}
    if args.ids:
        tasks = [t for t in tasks if t['id'] in set(args.ids)]
    bench = 'research_synthesis' + ('' if args.prompt_variant == 'a' else '_p' + args.prompt_variant)
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f'runs-{args.model}-{args.effort}-t{args.trial}.jsonl'
    kept = []
    if out.exists():
        kept = [json.loads(l) for l in out.read_text(encoding='utf-8').splitlines() if l.strip()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept), encoding='utf-8')
    done = {r['id'] for r in kept}
    cwd = Path(tempfile.mkdtemp(prefix='research_synthesis_'))  # an empty directory: no CLAUDE.md, no repo
    with out.open('a', encoding='utf-8') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            questions = '\n'.join(f"{i}. {facts[f]['question']}" for i, f in enumerate(task['facts'], 1))
            prompt = PROMPT[args.prompt_variant].format(brief=task['brief'], questions=questions)
            start = time.perf_counter()
            try:
                reply = harness.run(args.harness, prompt, args.model, args.effort, args.max_turns, TOOLS, args.timeout, cwd)
            except Exception as error:
                reply = {'text': '', 'usage': None, 'cost_usd': None, 'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            record = {'id': task['id'], 'family': 'research_synthesis', 'bench': bench, 'arm': 'T', 'variant': 'noexec',
                      'prompt_variant': args.prompt_variant, 'model_requested': args.model, 'effort': args.effort,
                      'harness': args.harness, 'trial': args.trial, 'tools': TOOLS, 'max_turns': args.max_turns,
                      'prompt_chars': len(prompt), 'wall_seconds': round(time.perf_counter() - start, 2), **reply}
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(args.model, args.effort, task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s turns={record.get('num_turns')} cost={record.get('cost_usd')} words={len((record.get('text') or '').split())}", flush=True)


if __name__ == '__main__':
    main()
