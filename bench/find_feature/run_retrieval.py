"""Run K3 retrieval arms against one endpoint. Receipt-first.

Arms:
  M  mechanical packet: evidence built blind by mech_packet.py from the
     question text alone; single-turn, no tools (K1 arm-B contract).
  T  tools: the agent CLI runs INSIDE the pinned kernel tree with its
     file/search tools enabled (web off) and answers the same JSON.
Usage: python3 run_retrieval.py --endpoint E --model M --arm M|T
"""
import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

import mech_packet
import run_probe  # SCHEMAS, QUESTIONS, ENDPOINTS (single-turn, no tools)

ABSTAIN = ('If you cannot determine the answer with certainty, answer '
           '"unknown". Guessing is worse than unknown.')


def question_for(task):
    return run_probe.QUESTIONS[task['family']].format(
        name=task['name'], file=task.get('file', ''),
        candidates=json.dumps(task.get('candidates', [])),
        subject=task.get('subject', ''))


def build_prompt_m(task, tree):
    packet = mech_packet.build_packet(tree, task['family'], task['name'],
                                      task.get('candidates'))
    return '\n\n'.join([
        'You answer questions about the Linux kernel v6.12 source tree.',
        'You have no tools, commands, or file access in this session; '
        'answer directly from this message only.',
        'Use ONLY the mechanical search report below. ' + ABSTAIN,
        'Reply with ONLY a JSON object of the form: '
        + run_probe.SCHEMAS[task['family']],
        'Question: ' + question_for(task),
        packet,
    ])


def build_prompt_t(task):
    return '\n\n'.join([
        'You answer questions about the Linux kernel v6.12 source tree.',
        'You are inside a full checkout of Linux v6.12 (your current '
        'working directory). Use your file and search tools to answer. '
        'Do not use the web. Do not modify any files.',
        ABSTAIN,
        'Reply with ONLY a JSON object of the form: '
        + run_probe.SCHEMAS[task['family']],
        'Question: ' + question_for(task),
    ])


def call_claude_t(prompt, model, timeout, tree):
    proc = subprocess.run(['claude', '-p', '--output-format', 'json',
                           '--model', model, '--max-turns', '15',
                           '--effort', 'medium',
                           '--allowed-tools', 'Read Glob Grep'],
                          cwd=tree, input=prompt, text=True,
                          capture_output=True, timeout=timeout)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return {'text': proc.stdout, 'usage': None, 'cost_usd': None,
                'operational_error': 'invalid-endpoint-response'}
    return {'text': data.get('result', ''), 'usage': data.get('usage'),
            'cost_usd': data.get('total_cost_usd'),
            'num_turns': data.get('num_turns'),
            'operational_error': 'endpoint-error' if data.get('is_error') else None}


def call_codex_t(prompt, model, timeout, tree):
    proc = subprocess.run(['codex', 'exec', '--skip-git-repo-check', '-s',
                           'read-only', '-', '--color', 'never'],
                          cwd=tree, input=prompt, text=True,
                          capture_output=True, timeout=timeout)
    return {'text': proc.stdout, 'usage': None, 'cost_usd': None,
            'operational_error': None if proc.returncode == 0 else 'endpoint-error'}


def call_agy_t(prompt, model, timeout, tree):
    proc = subprocess.run(['agy', '-p', prompt, '--model', model,
                           '--output-format', 'json', '--sandbox',
                           '--dangerously-skip-permissions'],
                          cwd=tree, text=True, capture_output=True,
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
            'cost_usd': None, 'num_turns': data.get('num_turns'),
            'operational_error': None if data.get('status') == 'SUCCESS'
            else data.get('status', 'endpoint-error')}


def call_grok_t(prompt, model, timeout, tree):
    # Prompt file lives OUTSIDE the tree the agent explores.
    with tempfile.TemporaryDirectory(prefix='k3-grok-') as holder:
        prompt_file = Path(holder) / 'prompt.txt'
        prompt_file.write_text(prompt)
        cmd = ['grok', '--prompt-file', str(prompt_file), '--output-format',
               'json', '--max-turns', '15', '--disable-web-search',
               '--always-approve']
        if model != 'default':
            cmd += ['--model', model]
        proc = subprocess.run(cmd, cwd=tree, text=True, capture_output=True,
                              timeout=timeout)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return {'text': proc.stdout + proc.stderr[:300], 'usage': None,
                'cost_usd': None, 'operational_error': 'invalid-endpoint-response'}
    return {'text': data.get('text', ''), 'usage': data.get('usage'),
            'cost_usd': data.get('total_cost_usd'),
            'num_turns': data.get('num_turns'),
            'operational_error': None if proc.returncode == 0 else 'endpoint-error'}


T_ENDPOINTS = {'claude': call_claude_t, 'codex': call_codex_t,
               'agy': call_agy_t, 'grok': call_grok_t}


def restore_tree(tree):
    """Return git-status dirt (empty if clean) and undo any of it.
    grok has no read-only mode; truth integrity beats trusting it."""
    dirt = subprocess.run(['git', 'status', '--porcelain'], cwd=tree,
                          text=True, capture_output=True,
                          stdin=subprocess.DEVNULL).stdout
    if dirt:
        subprocess.run(['git', 'checkout', '--', '.'], cwd=tree,
                       capture_output=True, stdin=subprocess.DEVNULL)
        for line in dirt.splitlines():
            if line.startswith('??'):
                target = Path(tree) / line[3:].strip()
                if target.is_file():
                    target.unlink()
    return dirt


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parents[2]
    ap.add_argument('--tasks', type=Path,
                    default=here / 'results/kernel-retrieval/tasks.json')
    ap.add_argument('--endpoint', required=True,
                    choices=sorted(run_probe.ENDPOINTS))
    ap.add_argument('--model', required=True)
    ap.add_argument('--arm', required=True, choices=['M', 'T'])
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--out', type=Path,
                    default=here / 'results/kernel-retrieval')
    args = ap.parse_args()
    if args.arm == 'T' and args.endpoint not in T_ENDPOINTS:
        raise SystemExit(f'{args.endpoint} has no tool harness')
    spec = json.loads(args.tasks.read_text())
    tree = spec['tree']
    tasks = spec['tasks'][:args.limit] if args.limit else spec['tasks']
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / (f"runs-{args.endpoint}-"
                      f"{args.model.replace(':', '_')}-{args.arm}.jsonl")
    kept = []
    if out.exists():
        kept = [json.loads(l) for l in out.read_text().splitlines()]
        kept = [r for r in kept if not r.get('operational_error')]
        out.write_text(''.join(json.dumps(r) + '\n' for r in kept))
    done = {r['id'] for r in kept}
    with out.open('a') as sink:
        for task in tasks:
            if task['id'] in done:
                continue
            start = time.perf_counter()
            try:
                if args.arm == 'M':
                    prompt = build_prompt_m(task, tree)
                    reply = run_probe.ENDPOINTS[args.endpoint](
                        prompt, args.model, args.timeout)
                else:
                    prompt = build_prompt_t(task)
                    reply = T_ENDPOINTS[args.endpoint](
                        prompt, args.model, args.timeout, tree)
            except Exception as error:
                prompt = ''
                reply = {'text': '', 'usage': None, 'cost_usd': None,
                         'operational_error': type(error).__name__}
            if not reply.get('operational_error') and not (reply.get('text') or '').strip():
                reply['operational_error'] = 'empty-response'
            record = {'id': task['id'], 'family': task['family'],
                      'arm': args.arm, 'endpoint': args.endpoint,
                      'model_requested': args.model,
                      'prompt_chars': len(prompt),
                      'wall_seconds': round(time.perf_counter() - start, 2),
                      **reply}
            if args.arm == 'T':
                dirt = restore_tree(tree)
                if dirt:
                    record['tree_dirty'] = dirt[:500]
            sink.write(json.dumps(record) + '\n')
            sink.flush()
            print(task['id'], record.get('operational_error') or 'ok',
                  f"{record['wall_seconds']}s",
                  f"turns={record.get('num_turns')}", flush=True)


if __name__ == '__main__':
    main()
