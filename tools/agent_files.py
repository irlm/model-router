"""Where the agent files are on this machine.

Claude Code reads ~/.claude/agents and every folder under it, so a collection checked out by category
keeps its files one level down (agents/testing/testing-api-tester.md) and they are agents all the same.
routing.json names a file by its file name only; this finds it wherever it sits.
"""
from pathlib import Path


def locate(agents_dir, file):
    """The path of the agent file with this file name: at the top of the folder when it is there, else
    the first one (by path) in a folder under it; None when this machine does not have it."""
    agents_dir = Path(agents_dir)
    top = agents_dir / file
    if top.exists():
        return top
    found = sorted(agents_dir.rglob(file)) if agents_dir.is_dir() else []
    return found[0] if found else None


def is_agent(path):
    """A Markdown file with a `name:` in its frontmatter: what Claude Code loads as an agent. A README or
    a CONTRIBUTING.md that a collection ships beside its agents has none."""
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False
    if not text.startswith('---'):
        return False
    return any(line.startswith('name:') for line in text.split('\n---', 1)[0].splitlines()[1:])


def count(agents_dir):
    """How many agent files the folder holds, the folders under it included."""
    agents_dir = Path(agents_dir)
    return sum(1 for p in agents_dir.rglob('*.md') if is_agent(p)) if agents_dir.is_dir() else 0
