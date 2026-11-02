"""Harness ablation of the fixed prefix: the input tokens of a one-turn Haiku call under a few harness
settings, so the cost floor of every short task is known per setting, not assumed. Each setting is
measured n times (default 2). Writes results/prefix/ablation-<date>.md and prints it.

Settings: baseline (Read only, MCP off, empty cwd); all tools; MCP on (whatever is configured here);
a 500-word CLAUDE.md in the cwd; the agent files moved aside (~/.claude/agents, restored afterwards).

  python3 tools/prefix_ablation.py [--n 2]
Run it alone: no other benchmark run in flight, since the agents directory is moved for one setting.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
CLAUDE = shutil.which('claude') or 'claude'
AGENTS = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / 'agents'


def call(extra, cwd):
    p = subprocess.run([CLAUDE, '-p', '--output-format', 'json', '--model', 'claude-haiku-5-5', '--effort', 'low', '--max-turns', '1', *extra],
                       input='Reply with the single word OK.', capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180, cwd=cwd)
    start = p.stdout.find('{')
    u = json.loads(p.stdout[start:])['usage']
    return u['input_tokens'] + u['cache_creation_input_tokens'] + u['cache_read_input_tokens']


def measure(name, extra, cwd, n):
    rows = []
    for _ in range(n):
        try:
            rows.append(call(extra, cwd))
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
            rows.append(None)
            print(f'{name}: {type(e).__name__}', file=sys.stderr)
    print(f'{name:28} {rows}', flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=2)
    args = ap.parse_args()
    cfg = Path(tempfile.mkdtemp(prefix='prefix_cfg_'))
    no_mcp = cfg / 'no-mcp.json'
    no_mcp.write_text('{"mcpServers": {}}', encoding='utf-8')
    empty = tempfile.mkdtemp(prefix='prefix_')
    base = ['--allowed-tools', 'Read', '--strict-mcp-config', '--mcp-config', str(no_mcp)]
    out = {}
    out['baseline (Read, MCP off)'] = measure('baseline', base, empty, args.n)
    out['all tools (MCP off)'] = measure('all tools', ['--strict-mcp-config', '--mcp-config', str(no_mcp)], empty, args.n)
    out['MCP on (as configured here)'] = measure('MCP on', ['--allowed-tools', 'Read'], empty, args.n)
    with_md = tempfile.mkdtemp(prefix='prefix_md_')
    (Path(with_md) / 'CLAUDE.md').write_text('# Project notes\n\n' + ('This project follows the usual conventions. ' * 60) + '\n', encoding='utf-8')
    out['CLAUDE.md of 500 words in cwd'] = measure('CLAUDE.md 500 words', base, with_md, args.n)
    if AGENTS.exists():
        aside = AGENTS.with_name('agents.ablation')
        AGENTS.rename(aside)
        try:
            out['agent files moved aside'] = measure('no agent files', base, empty, args.n)
        finally:
            aside.rename(AGENTS)
    agents_n = len(list(AGENTS.glob('*.md'))) if AGENTS.exists() else 0
    today = datetime.date.today().isoformat()
    lines = [f'# Prefix ablation {today}', '',
             f'Input tokens of a one-turn Haiku call (input + cache write + cache read), {args.n} calls per setting; '
             f'{agents_n} agent files in ~/.claude/agents at the time. The baseline is what regress.py records.', '',
             '| Setting | Tokens per call |', '|---|---|']
    for k, v in out.items():
        lines.append(f"| {k} | {', '.join(str(x) for x in v)} |")
    b = [x for x in out['baseline (Read, MCP off)'] if x]
    if b:
        lines += ['', 'Against the baseline:']
        for k, v in out.items():
            vv = [x for x in v if x]
            if vv and k != 'baseline (Read, MCP off)':
                lines.append(f'- {k}: {sum(vv) / len(vv) - sum(b) / len(b):+.0f} tokens')
    text = '\n'.join(lines) + '\n'
    (HERE / 'results/prefix').mkdir(parents=True, exist_ok=True)
    (HERE / 'results/prefix' / f'ablation-{today}.md').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
