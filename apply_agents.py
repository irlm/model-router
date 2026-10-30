"""Apply (or revert) routing.json to the Claude Code agent files.

For each file named in routing.json["agents"], set `model:` and `effort:` in
the YAML frontmatter. Only those two keys are touched; everything else in the
file is left byte-identical. `--revert` removes the two keys (no agent file
had either key before routing v1, verified 2026-10-30 over 184 files).

Usage: python3 apply_agents.py [--agents-dir ~/.claude/agents] [--revert] [--dry-run]
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS = ('model:', 'effort:')


def rewrite(text, model, effort, revert):
    lines = text.split('\n')
    if lines[0] != '---':
        raise ValueError('no frontmatter')
    end = lines.index('---', 1)
    front = [l for l in lines[1:end] if not l.startswith(KEYS)]
    if not revert:
        front += [f'model: {model}', f'effort: {effort}']
    return '\n'.join(['---', *front, '---', *lines[end + 1:]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agents-dir', type=Path, default=Path.home() / '.claude/agents')
    ap.add_argument('--routing', type=Path, default=HERE / 'routing.json')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    agents = json.loads(args.routing.read_text())['agents']
    missing = [f for f in agents if not (args.agents_dir / f).exists()]
    if missing:
        raise SystemExit(f'missing agent files: {missing}')
    for name, route in agents.items():
        path = args.agents_dir / name
        before = path.read_text()
        after = rewrite(before, route['model'], route['effort'], args.revert)
        state = 'unchanged' if after == before else ('would change' if args.dry_run else 'changed')
        if not args.dry_run and after != before:
            path.write_text(after)
        print(f"{state:12} {name}: {'removed' if args.revert else route['model'] + ' / ' + route['effort']} ({route['family']})")


if __name__ == '__main__':
    main()
