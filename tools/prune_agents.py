"""Move the agent files nobody calls out of ~/.claude/agents, reversibly.

Every file in ~/.claude/agents adds its description to the prefix of every
request Claude Code sends (about 60 tokens per file; 184 files were 10-17k
tokens, and Claude Code warns above 15k). The transcripts say which agents
were ever called (tools/usage_scan.py counts the same thing), so this keeps:
  - every agent named in an Agent/Task call in any local transcript,
  - every agent routing.json routes (apply_agents.py needs the files),
  - anything passed with --keep,
and moves the rest to ~/.claude/agents.unused/ (same file names). `--revert`
moves them all back. `--dry-run` only lists. Nothing is deleted.

Usage: python3 tools/prune_agents.py [--dry-run] [--revert] [--keep NAME ...]
"""
import argparse
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
TRANSCRIPTS = Path.home() / '.claude/projects'


def called_agents():
    names = {}
    for f in TRANSCRIPTS.glob('**/*.jsonl'):
        for line in f.open(errors='replace'):
            if '"subagent_type"' not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            m = r.get('message') or {}
            if r.get('type') != 'assistant' or not isinstance(m.get('content'), list):
                continue
            for it in m['content']:
                if isinstance(it, dict) and it.get('type') == 'tool_use' and it.get('name') in ('Agent', 'Task'):
                    st = (it.get('input') or {}).get('subagent_type')
                    if st:
                        names[st] = names.get(st, 0) + 1
    return names


def frontmatter_name(path):
    text = path.read_text(errors='replace')
    m = re.search(r'^name:\s*(.+?)\s*$', text, re.M)
    return m.group(1).strip().strip('"\'') if m else path.stem


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agents-dir', type=Path, default=Path.home() / '.claude/agents')
    ap.add_argument('--routing', type=Path, default=HERE / 'routing.json')
    ap.add_argument('--keep', nargs='*', default=[], help='extra agent names or file names to keep')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    unused = args.agents_dir.with_name(args.agents_dir.name + '.unused')
    if args.revert:
        files = sorted(unused.glob('*.md')) if unused.exists() else []
        for f in files:
            print('restore', f.name)
            if not args.dry_run:
                shutil.move(str(f), str(args.agents_dir / f.name))
        print(f'{len(files)} files {"would be " if args.dry_run else ""}restored to {args.agents_dir}')
        return
    called = called_agents()
    routed = set(json.loads(args.routing.read_text()).get('agents', {}).keys()) if args.routing.exists() else set()
    keep_names = set(called) | set(args.keep)
    kept, moved = [], []
    for f in sorted(args.agents_dir.glob('*.md')):
        name = frontmatter_name(f)
        why = ('called %d times' % called[name]) if name in called else ('routed by routing.json' if f.name in routed else
               'kept by --keep' if (name in keep_names or f.name in keep_names) else None)
        if why:
            kept.append((f.name, why))
        else:
            moved.append(f.name)
    for name, why in kept:
        print(f'keep  {name}: {why}')
    print(f'{len(moved)} files {"would move" if args.dry_run else "move"} to {unused}')
    if not args.dry_run:
        unused.mkdir(exist_ok=True)
        for name in moved:
            shutil.move(str(args.agents_dir / name), str(unused / name))
    print('called agents in the transcripts:', dict(sorted(called.items(), key=lambda x: -x[1])))


if __name__ == '__main__':
    main()
