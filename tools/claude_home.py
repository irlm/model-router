"""Where Claude Code keeps its files on this machine.

CLAUDE_CONFIG_DIR moves the whole folder (a second profile, a test machine); without it the folder is
~/.claude. Every path the tools read or write under it goes through here, read when asked, so a test or a
second profile changes it with the variable alone.
"""
import os
from pathlib import Path


def config_dir():
    return Path(os.environ.get('CLAUDE_CONFIG_DIR') or (Path.home() / '.claude'))


def agents_dir():
    """The agent files Claude Code loads, folders under it included."""
    return config_dir() / 'agents'


def unused_dir():
    """Where tools/prune_agents.py parks the agent files nothing calls (--revert brings them back)."""
    return config_dir() / 'agents.unused'


def projects_dir():
    """The transcripts, one folder per working directory."""
    return config_dir() / 'projects'
