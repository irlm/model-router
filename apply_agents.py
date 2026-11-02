"""Apply (or revert) routing.json to the Claude Code agent files.

For each file named in routing.json["agents"], set `model:` and `effort:` in
the YAML frontmatter and, when the entry has an `instruction`, a marked
paragraph right after the frontmatter. Nothing else in the file is touched.
A file you do not have is absent and skipped, unless the repository ships it
as a template in agents/ (web-researcher.md): then it is installed first.
`--revert` removes the two keys and the paragraph (no agent file had either
key before routing v1, verified 2026-10-30 over 184 files).

Usage: python3 apply_agents.py [--agents-dir ~/.claude/agents] [--revert] [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'tools'))
import changes  # noqa: E402
TEMPLATES = HERE / 'agents'   # agent files the repository ships, installed when missing
KEYS = ('model:', 'effort:')
MARK = '<!-- model-router -->'


def rewrite(text, model, effort, revert, instruction=None):
    lines = text.split('\n')
    if lines[0] != '---':
        raise ValueError('no frontmatter')
    end = lines.index('---', 1)
    front = [l for l in lines[1:end] if not l.startswith(KEYS)]
    body = lines[end + 1:]
    for i, l in enumerate(body):  # drop an earlier instruction line and its blank line
        if l.startswith(MARK):
            del body[i:i + 2 if i + 1 < len(body) and body[i + 1] == '' else i + 1]
            break
    if not revert:
        front += [f'model: {model}', f'effort: {effort}']
        if instruction:
            lead = 0
            while lead < len(body) and body[lead] == '':
                lead += 1
            body = body[:lead] + [f'{MARK} **Routing rule (model-router, ROUTING.md):** {instruction}', ''] + body[lead:]
    return '\n'.join(['---', *front, '---', *body])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agents-dir', type=Path, default=Path.home() / '.claude/agents')
    ap.add_argument('--routing', type=Path, default=HERE / 'routing.json')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    agents = json.loads(args.routing.read_text(encoding='utf-8'))['agents']
    done = []
    absent = []
    for name, route in agents.items():
        path = args.agents_dir / name
        install = False
        if path.exists():
            before = path.read_text(encoding='utf-8')
        elif args.revert or not (TEMPLATES / name).exists():
            absent.append(name)
            continue
        else:
            before = (TEMPLATES / name).read_text(encoding='utf-8')
            install = True
        after = rewrite(before, route['model'], route['effort'], args.revert, route.get('instruction'))
        if install:
            state = 'would install' if args.dry_run else 'installed'
        else:
            state = 'unchanged' if after == before else ('would change' if args.dry_run else 'changed')
        if not args.dry_run and (install or after != before):
            args.agents_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(after, encoding='utf-8')
            done.append(name)
        print(f"{state:13} {name}: {'removed' if args.revert else route['model'] + ' / ' + route['effort']} ({route['family']})")
    if absent:
        print(f"skipped {len(absent)} agent file(s) not on this machine: {', '.join(absent)}")
    if done:
        # The change log: from now on the widget counts what the transcripts save (tools/changes.py).
        e = changes.add('revert' if args.revert else 'apply', 'agents: ' + ', '.join(done))
        print(f"change recorded at {e['at']}: the pane counts the saving from here")


if __name__ == '__main__':
    main()
