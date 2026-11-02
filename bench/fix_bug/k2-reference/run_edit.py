"""Run K2 edit tasks against one endpoint, one arm. Receipt-first.

Arms: B = failing KUnit output + the buggy function's source;
A = B plus deterministic noise files to ~3x context (K1's pool and
budget rule). The model replies with the complete corrected C
function in a ```c fence, or the word "unknown". Endpoint adapters,
empty-cwd isolation and the resume rule are reused from K1.
Usage: python3 run_edit.py --endpoint E --model M --arm B|A [...]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'common'))
import local  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'kernel_probe'))
import run_probe  # ENDPOINTS, NOISE_CAP_CHARS

PROMPT = """You are fixing a real bug in the Linux kernel v6.12 source tree.
You have no tools, commands, or file access in this session; answer directly from this message only.

The KUnit suite `{suite}` fails. Failing output:

{failing_output}

The suspect function is `{function}` in {file}:

```c
{mutated_function}
```
{noise}
Reply with ONLY the complete corrected C function in a ```c fence (same signature, full body), or the single word unknown if you cannot determine the fix."""


def build_prompt(task, arm, tree, noise_pool):
    noise = ''
    if arm == 'A':
        base = len(task['mutated_function']) + len(task['failing_output'])
        budget = min(2 * base + 20000, run_probe.NOISE_CAP_CHARS)
        offset = sum(ord(c) for c in task['id']) % len(noise_pool)
        blocks, added = [], 0
        for name in noise_pool[offset:] + noise_pool[:offset]:
            text = (Path(tree) / name).read_text(errors='replace')
            if added + len(text) > budget:
                continue
            blocks.append(f'=== FILE: {name} ===\n{text}')
            added += len(text)
        noise = ('\nOther files from the tree, for context:\n\n'
                 + '\n\n'.join(blocks) + '\n')
    return PROMPT.format(noise=noise, **task)


def extract_function(text):
    """The C function from a ```c fence, or 'unknown', or None."""
    if re.fullmatch(r'\W*unknown\W*', text.strip(), re.I):
        return 'unknown'
    fences = re.findall(r'```(?:c)?\s*\n(.*?)```', text, re.S)
    if fences:
        return max(fences, key=len).strip()
    return text.strip() if '{' in text else None


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parents[2]
    ap.add_argument('--tasks', type=Path, default=here / 'results/kernel-edit/tasks.json')
    ap.add_argument('--probe-tasks', type=Path,
                    default=here / 'results/kernel-probe/tasks.json')
    ap.add_argument('--endpoint', choices=sorted(run_probe.ENDPOINTS), required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--arm', choices=['B', 'A'], required=True)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--out', type=Path, default=here / 'results/kernel-edit')
    args = ap.parse_args()
    spec = json.loads(args.tasks.read_text())
    noise_pool = json.loads(args.probe_tasks.read_text())['noise_pool']
    tasks = spec['tasks'][:args.limit or None]
    out = args.out / f"runs-{args.endpoint}-{args.model.replace(':', '_')}-{args.arm}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        kept = [json.loads(line) for line in out.read_text().splitlines()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept))
        done = {r['id'] for r in kept}
    with out.open('a') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            prompt = build_prompt(task, args.arm, local.resolve(spec['tree']), noise_pool)
            start = time.perf_counter()
            try:
                if args.endpoint == 'ollama':
                    # K1's JSON output mode would mangle the ```c fence.
                    reply = run_probe.call_ollama(prompt, args.model,
                                                  args.timeout, json_format=False)
                else:
                    reply = run_probe.ENDPOINTS[args.endpoint](prompt, args.model,
                                                               args.timeout)
            except Exception as error:
                reply = {'text': '', 'usage': None, 'cost_usd': None,
                         'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                # agy sometimes reports SUCCESS with no text (K1-known
                # endpoint artifact); that is not a model answer.
                reply['operational_error'] = 'empty-response'
            record = {'id': task['id'], 'arm': args.arm,
                      'endpoint': args.endpoint, 'model_requested': args.model,
                      'prompt_chars': len(prompt),
                      'wall_seconds': round(time.perf_counter() - start, 2),
                      **reply}
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s", flush=True)


if __name__ == '__main__':
    main()
