"""Run K1 tasks against one endpoint, one arm. Receipt-first.

Arms: Z no source (memory only; 'unknown' is honest), B the task's
fixed context regions, A the same regions plus deterministic noise
files until the context roughly triples (capped). Usage:
  python3 run_probe.py --tasks F --endpoint ollama|claude|codex \
      --model NAME --arm Z|B|A [--limit N] [--out DIR]
"""
import argparse
import json
import sys
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
import local  # noqa: E402

# Agent CLIs (agy, grok) get an empty cwd so file tools find nothing;
# web/tool use is restricted where a flag exists and num_turns is
# recorded so any multi-turn (tool-using) answer can be flagged.
EMPTY_CWD = tempfile.mkdtemp(prefix='kernel-probe-empty-')

SCHEMAS = {
    'exists': '{"exists": true | false | "unknown", "file": "<defining path or unknown>"}',
    'fields': '{"fields": ["name", ...] | "unknown"}',
    'refs': '{"referencing": ["path", ...] | "unknown"}',
    # K4 semantic families
    'callers': '{"calling": ["path", ...] | "unknown"}',
    'dispatch': '{"function": "exact_function_name" | "unknown"}',
}
QUESTIONS = {
    'exists': 'In Linux v6.12, does a function named `{name}` exist anywhere in the kernel source tree?',
    'fields': 'List the field names of `struct {name}` as defined in {file} in Linux v6.12.',
    'refs': 'Which of these files contain a reference to the function `{name}` (a call or use written `{name}(`)?\nCandidates: {candidates}',
    'callers': ('Which of these candidate files contain at least one actual call to the kernel function `{name}` — '
                'a statement that invokes it at runtime — as opposed to merely declaring it, defining it, or '
                'mentioning it in a comment?\nCandidates: {candidates}\nList every candidate that contains a real call.'),
    'dispatch': 'In Linux v6.12, which C function {subject}? Give the exact function name.',
}
# Cap keeps every built prompt under Linux's 128KiB single-argument
# limit (agent CLIs take the prompt via argv). Set before any arm-A
# run existed, so all endpoints see identical arm-A prompts.
NOISE_CAP_CHARS = 70000


def excerpt(tree, ref):
    lines = (Path(tree) / ref['path']).read_text(errors='replace').splitlines()
    body = '\n'.join(lines[ref['start'] - 1:ref['end']])
    return f"=== FILE: {ref['path']} (lines {ref['start']}-{min(ref['end'], len(lines))}) ===\n{body}"


def build_prompt(task, arm, tree, noise_pool):
    question = QUESTIONS[task['family']].format(
        name=task['name'], file=task.get('file', ''),
        candidates=json.dumps(task.get('candidates', [])))
    # Prompt v2: the no-tools sentence is identical for every endpoint
    # and arm, so agent CLIs cannot search a filesystem or the web for
    # the answer (contamination) and non-agent endpoints are unaffected.
    parts = ['You answer questions about the Linux kernel v6.12 source tree.',
             'You have no tools, commands, or file access in this session; '
             'answer directly from this message only.']
    if arm == 'Z':
        parts.append('No source is provided. Answer from certain knowledge only; '
                     'when not certain, answer "unknown". Guessing is worse than unknown.')
    else:
        parts.append('Use ONLY the source excerpts below. If they are insufficient '
                     'to be certain, answer "unknown". Guessing is worse than unknown.')
    parts.append('Reply with ONLY a JSON object of the form: ' + SCHEMAS[task['family']])
    parts.append('Question: ' + question)
    if arm in ('B', 'A'):
        blocks = [excerpt(tree, ref) for ref in task['context_b']]
        if arm == 'A':
            base = sum(len(b) for b in blocks)
            budget = min(2 * base + 20000, NOISE_CAP_CHARS)
            # Deterministic per-task noise: rotate the pool by task index.
            offset = int(re.sub(r'\D', '', task['id']) or 0)
            added = 0
            for name in noise_pool[offset:] + noise_pool[:offset]:
                text = (Path(tree) / name).read_text(errors='replace')
                if added + len(text) > budget:
                    continue
                blocks.append(f'=== FILE: {name} ===\n{text}')
                added += len(text)
        parts.append('\n\n'.join(blocks))
    return '\n\n'.join(parts)


def call_ollama(prompt, model, timeout, json_format=True):
    # json_format suits K1's JSON-answer protocol; K2 needs free-form
    # text (a ```c fence), so run_edit passes json_format=False.
    body = json.dumps({'model': model, 'prompt': prompt, 'stream': False,
                       **({'format': 'json'} if json_format else {}),
                       'options': {'num_ctx': 32768, 'temperature': 0}}).encode()
    request = urllib.request.Request('http://localhost:11434/api/generate',
                                     data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.load(response)
    return {'text': data.get('response', ''),
            'usage': {'input_tokens': data.get('prompt_eval_count'),
                      'output_tokens': data.get('eval_count')},
            'cost_usd': 0.0, 'model': data.get('model'),
            'operational_error': None if data.get('done') else 'incomplete'}


def call_claude(prompt, model, timeout):
    proc = subprocess.run(['claude', '-p', '--output-format', 'json', '--model',
                           model, '--max-turns', '1', '--effort', 'medium',
                           '--tools', ''],
                          input=prompt, text=True, capture_output=True, timeout=timeout)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return {'text': proc.stdout, 'usage': None, 'cost_usd': None,
                'operational_error': 'invalid-endpoint-response'}
    return {'text': data.get('result', ''), 'usage': data.get('usage'),
            'cost_usd': data.get('total_cost_usd'),
            'model': ','.join(sorted((data.get('modelUsage') or {}).keys())),
            'operational_error': 'endpoint-error' if data.get('is_error') else None}


def call_codex(prompt, model, timeout):
    proc = subprocess.run(['codex', 'exec', '--skip-git-repo-check', '-s',
                           'read-only', '-', '--color', 'never'],
                          cwd=EMPTY_CWD, input=prompt, text=True,
                          capture_output=True, timeout=timeout)
    return {'text': proc.stdout, 'usage': None, 'cost_usd': None, 'model': model,
            'operational_error': None if proc.returncode == 0 else 'endpoint-error'}


def call_agy(prompt, model, timeout):
    proc = subprocess.run(['agy', '-p', prompt, '--model', model,
                           '--output-format', 'json'],
                          cwd=EMPTY_CWD, text=True, capture_output=True,
                          timeout=timeout)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return {'text': proc.stdout + proc.stderr[:300], 'usage': None,
                'cost_usd': None, 'operational_error': 'invalid-endpoint-response'}
    usage = data.get('usage') or {}
    return {'text': data.get('response', ''),
            'usage': {'input_tokens': usage.get('input_tokens'),
                      'output_tokens': usage.get('output_tokens')},
            'cost_usd': None, 'model': model,
            'num_turns': data.get('num_turns'),
            'operational_error': None if data.get('status') == 'SUCCESS'
            else data.get('status', 'endpoint-error')}


def call_grok(prompt, model, timeout):
    # Prompt via file: the biggest arm-A prompts are near the argv
    # size limit, and --prompt-file is verified headless.
    prompt_file = Path(EMPTY_CWD) / 'prompt.txt'
    prompt_file.write_text(prompt)
    cmd = ['grok', '--prompt-file', str(prompt_file), '--output-format', 'json',
           '--max-turns', '1', '--disable-web-search']
    if model != 'default':
        cmd += ['--model', model]
    try:
        proc = subprocess.run(cmd, cwd=EMPTY_CWD, text=True, capture_output=True,
                              timeout=timeout)
    finally:
        prompt_file.unlink(missing_ok=True)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return {'text': proc.stdout + proc.stderr[:300], 'usage': None,
                'cost_usd': None, 'operational_error': 'invalid-endpoint-response'}
    return {'text': data.get('text', ''), 'usage': data.get('usage'),
            'cost_usd': data.get('total_cost_usd'),
            'model': ','.join(sorted((data.get('modelUsage') or {}).keys())),
            'num_turns': data.get('num_turns'),
            'operational_error': None if proc.returncode == 0 else 'endpoint-error'}


ENDPOINTS = {'ollama': call_ollama, 'claude': call_claude, 'codex': call_codex,
             'agy': call_agy, 'grok': call_grok}


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parents[2]
    ap.add_argument('--tasks', type=Path, default=here / 'results/kernel-probe/tasks.json')
    ap.add_argument('--endpoint', choices=sorted(ENDPOINTS), required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--arm', choices=['Z', 'B', 'A'], required=True)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--out', type=Path, default=here / 'results/kernel-probe')
    args = ap.parse_args()
    spec = json.loads(args.tasks.read_text())
    tasks = spec['tasks'][:args.limit or None]
    out = args.out / f"runs-{args.endpoint}-{args.model.replace(':', '_')}-{args.arm}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        # Keep only clean records so failed calls (timeouts, quota
        # exhaustion) are retried on resume instead of counted done.
        kept = [json.loads(line) for line in out.read_text().splitlines()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept))
        done = {r['id'] for r in kept}
    with out.open('a') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            prompt = build_prompt(task, args.arm, local.resolve(spec['tree']), spec['noise_pool'])
            start = time.perf_counter()
            try:
                reply = ENDPOINTS[args.endpoint](prompt, args.model, args.timeout)
            except Exception as error:  # timeout, connection: record, keep going
                reply = {'text': '', 'usage': None, 'cost_usd': None,
                         'operational_error': type(error).__name__}
            record = {'id': task['id'], 'family': task['family'], 'arm': args.arm,
                      'endpoint': args.endpoint, 'model_requested': args.model,
                      'prompt_chars': len(prompt),
                      'wall_seconds': round(time.perf_counter() - start, 2), **reply}
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s", flush=True)


if __name__ == '__main__':
    main()
