"""Browser-flow family, agent arm. For each task: start the app with its
planted defect on a fresh port, give the agent the URL and the checklist, let it
drive the user's Chrome through the Claude in Chrome extension (headless
`claude -p --chrome`, browser tools only, no file or network-inspection tools),
then record its verdicts, the app's action log and the usual usage receipt.
Sequential: the extension is one shared browser.

--harness picks the agent program (bench/common/harness.py); only harnesses
with a browser are offered, which today means Claude Code.

Usage: python3 run_agent.py --model M --effort E [--trial N] [--ids ...] [--max-turns 80]
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'common'))
import harness  # noqa: E402

TOOLS = ' '.join('mcp__claude-in-chrome__' + t for t in (
    'tabs_context_mcp', 'tabs_create_mcp', 'tabs_close_mcp', 'navigate', 'read_page',
    'get_page_text', 'find', 'form_input', 'computer', 'browser_batch', 'resize_window'))
PROMPT = """You are testing a small web application the way a careful end user would, using only the Chrome browser tools. The app's sign-in page is {url}

Open it in a NEW browser tab, do the steps below in order in that tab, and judge each numbered item only by what you actually observe on screen. Do every step exactly as written and in order, even if an earlier item failed. Close the tab when you are done.

{checklist}

You cannot read the application's source and must not use network or console inspection; the browser is your only tool.

When finished, reply with ONLY a JSON object: {{"results": {{"1": "pass" or "fail", "2": ..., "9": ...}}, "notes": "<one short sentence per failed item, or empty>"}}"""


def start_app(port, defect):
    proc = subprocess.Popen([sys.executable, str(HERE / 'app.py'), '--port', str(port), '--defect', defect],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/__state', timeout=1).read()
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError(f'app did not start on {port}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--effort', required=True, choices=['low', 'medium', 'high', 'xhigh', 'max'])
    ap.add_argument('--tasks', type=Path, default=HERE / 'tasks.json')
    ap.add_argument('--ids', nargs='*', default=None)
    ap.add_argument('--trial', type=int, default=1)
    ap.add_argument('--max-turns', type=int, default=80)
    ap.add_argument('--timeout', type=int, default=1800)
    ap.add_argument('--base-port', type=int, default=8800)
    ap.add_argument('--out', type=Path, default=HERE.parents[1] / 'runs/browser_flow')
    ap.add_argument('--harness', default='claude', choices=harness.harnesses(need=('browser',)))
    args = ap.parse_args()
    spec = json.loads(args.tasks.read_text())
    tasks = spec['tasks']
    if args.ids:
        tasks = [t for t in tasks if t['id'] in set(args.ids)]
    checklist = '\n'.join(f'{n}. {line}' for n, line in enumerate(spec['checklist'], 1))
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f'runs-{args.model}-{args.effort}-t{args.trial}.jsonl'
    kept = []
    if out.exists():
        kept = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept))
    done = {r['id'] for r in kept}
    cwd = HERE.parents[1] / 'runs/browser_flow/cwd'
    cwd.mkdir(parents=True, exist_ok=True)
    with out.open('a') as sink:
        for n, task in enumerate(tasks):
            if task['id'] in done:
                continue
            port = args.base_port + (n % 50)
            proc = start_app(port, task['defect'])
            url = f'http://127.0.0.1:{port}/'
            prompt = PROMPT.format(url=url, checklist=checklist)
            start = time.perf_counter()
            try:
                reply = harness.run(args.harness, prompt, args.model, args.effort, args.max_turns,
                                    TOOLS, args.timeout, cwd, chrome=True)
            except Exception as error:
                reply = {'text': '', 'usage': None, 'cost_usd': None, 'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            try:
                state = json.loads(urllib.request.urlopen(f'{url}__state', timeout=5).read())
            except OSError:
                state = None
            proc.kill()
            proc.wait()
            record = {'id': task['id'], 'family': 'browser_flow', 'bench': 'browser_flow', 'arm': 'T',
                      'driver': 'claude-in-chrome', 'defect': task['defect'],
                      'model_requested': args.model, 'effort': args.effort, 'harness': args.harness,
                      'trial': args.trial,
                      'tools': TOOLS, 'max_turns': args.max_turns, 'prompt_chars': len(prompt),
                      'wall_seconds': round(time.perf_counter() - start, 2), 'state': state, **reply}
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(args.model, args.effort, task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s turns={record.get('num_turns')} cost={record.get('cost_usd')} "
                  f"actions={len((state or {}).get('log', []))}", flush=True)


if __name__ == '__main__':
    main()
