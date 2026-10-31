"""Run one headless agent session on a named harness and return one receipt shape.

A harness is the agent program that owns the tool loop. Each adapter maps the
harness's own output to the same fields, so the checkers and catalog/price.py
never see which harness ran:
  text               the final answer
  usage              Anthropic-style token fields: input_tokens (uncached),
                     cache_read_input_tokens, cache_creation_input_tokens,
                     output_tokens, plus the harness's raw block
  cost_usd           the harness's own figure, or None (then the catalog prices it)
  num_turns          the harness's count, or an approximation (see each adapter)
  model_used         what the harness says it ran
  operational_error  None, or why the session is not a verdict
  harness            'claude' | 'codex'

  claude  Claude Code, `claude -p --output-format json`. Tools are an allow-list.
  codex   OpenAI Codex CLI, `codex exec --json` (ChatGPT login or API key). Tools
          are whatever Codex has (a shell, file edits) inside its sandbox:
          read-only, or workspace-write when `write=True`. A tool list cannot
          be enforced, so a Codex run in a "no runner" arm can still build and
          test. Receipts record that under harness_note. No turn limit either;
          the timeout bounds the session.
"""
import json
import subprocess

CODEX_EFFORT = {'low': 'low', 'medium': 'medium', 'high': 'high', 'xhigh': 'xhigh', 'max': 'xhigh'}


def call_claude(prompt, model, effort, max_turns, tools, timeout, cwd, chrome=False):
    cmd = ['claude', '-p', '--output-format', 'json', '--model', model,
           '--max-turns', str(max_turns), '--effort', effort, '--allowed-tools', tools]
    if chrome:
        cmd.insert(2, '--chrome')
    proc = subprocess.run(cmd, cwd=str(cwd), input=prompt, text=True, capture_output=True, timeout=timeout)
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return {'harness': 'claude', 'text': proc.stdout[-2000:], 'stderr': proc.stderr[-500:],
                'usage': None, 'cost_usd': None, 'operational_error': 'invalid-endpoint-response'}
    return {'harness': 'claude', 'text': data.get('result', ''), 'usage': data.get('usage'),
            'cost_usd': data.get('total_cost_usd'), 'num_turns': data.get('num_turns'),
            'duration_ms': data.get('duration_ms'),
            'model_used': ','.join(sorted((data.get('modelUsage') or {}).keys())),
            'permission_denials': data.get('permission_denials'),
            'operational_error': 'endpoint-error' if data.get('is_error') else None}


def call_codex(prompt, model, effort, max_turns, tools, timeout, cwd, write=False):
    cmd = ['codex', 'exec', '--skip-git-repo-check', '--json', '--ephemeral', '--color', 'never',
           '-C', str(cwd), '-m', model, '-c', f'model_reasoning_effort="{CODEX_EFFORT.get(effort, "low")}"',
           '-s', 'workspace-write' if write else 'read-only', '-']
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), input=prompt, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return {'harness': 'codex', 'text': (e.stdout or '')[-2000:] if isinstance(e.stdout, str) else '',
                'usage': None, 'cost_usd': None, 'operational_error': 'timeout'}
    messages, items, usage, err = [], {}, None, None
    for line in proc.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        t = ev.get('type')
        if t == 'item.completed':
            item = ev.get('item') or {}
            items[item.get('type', '?')] = items.get(item.get('type', '?'), 0) + 1
            if item.get('type') == 'agent_message':
                messages.append(item.get('text', ''))
            elif item.get('type') == 'error':
                err = err or item.get('message')
        elif t == 'turn.completed':
            usage = ev.get('usage')
        elif t in ('error', 'turn.failed'):
            err = (ev.get('error') or {}).get('message') or ev.get('message') or 'turn.failed'
    norm = None
    if usage:
        cached = usage.get('cached_input_tokens', 0) or 0
        norm = {'input_tokens': max(0, (usage.get('input_tokens', 0) or 0) - cached),
                'cache_read_input_tokens': cached, 'cache_creation_input_tokens': 0,
                'output_tokens': usage.get('output_tokens', 0) or 0,
                'output_tokens_details': {'reasoning_output_tokens': usage.get('reasoning_output_tokens', 0)},
                'codex': usage}
    fatal = err if (err and not messages) or proc.returncode != 0 else None
    return {'harness': 'codex', 'text': messages[-1] if messages else '', 'usage': norm, 'cost_usd': None,
            'num_turns': sum(items.values()), 'items': items, 'model_used': model,
            'stderr': proc.stderr[-500:] if fatal else '', 'harness_warning': err if (err and not fatal) else None,
            'harness_note': 'codex: own tools in a sandbox, tool list and turn limit not enforced; tools asked: ' + tools,
            'operational_error': ('endpoint-error: ' + fatal[:120]) if fatal else None}


ADAPTERS = {'claude': call_claude, 'codex': call_codex}


def run(harness, prompt, model, effort, max_turns, tools, timeout, cwd, **kw):
    return ADAPTERS[harness](prompt, model, effort, max_turns, tools, timeout, cwd, **kw)
