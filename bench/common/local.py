"""Machine-local settings: where the fixtures live on this machine. Read from local/config.json,
which is not in git (local/README.md says what goes there). Every key is optional; a missing one
means "not set up on this machine", and the status pane says which family that blocks.

  kernel_tree       the pinned Linux v6.12 tree the find_feature and fix_bug tasks point at ($KERNEL_TREE)
  kernel_worktrees  the directory of kernel worktrees and KUnit build dirs ($KERNEL_WT)
  skip_projects     fragments of ~/.claude/projects directory names that are benchmark sessions on this
                    machine, not the user's own work; the ledger and consumption scans leave them out

MODEL_ROUTER_KERNEL_TREE and MODEL_ROUTER_KERNEL_WT in the environment override the file.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'local/config.json'
# Directories the benchmark itself creates: temp dirs of the web research and prefix runs, the browser
# runs, and the evaluation clones of the user's repos (README: ~/Projects/Github/model-router-evaluation).
OWN_MARKERS = ('model-router-runs', 'model-router-evaluation', 'tmp-prefix', 'tmp-web-research-', 'tmp-research-synthesis-',
               'tmp-browser', 'scratchpad')
_cfg = None


def cfg():
    global _cfg
    if _cfg is None:
        _cfg = json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else {}
    return _cfg


def kernel_tree():
    return os.environ.get('MODEL_ROUTER_KERNEL_TREE') or cfg().get('kernel_tree') or ''


def kernel_worktrees():
    return os.environ.get('MODEL_ROUTER_KERNEL_WT') or cfg().get('kernel_worktrees') or ''


def resolve(path):
    """Expand $KERNEL_TREE, $KERNEL_WT and ~ in a path from a task file. An unset placeholder stays
    as it is, so a missing fixture shows up as a path that does not exist, not as a wrong one."""
    s = str(path)
    if '$KERNEL_WT' in s and kernel_worktrees():
        s = s.replace('$KERNEL_WT', kernel_worktrees())
    if '$KERNEL_TREE' in s and kernel_tree():
        s = s.replace('$KERNEL_TREE', kernel_tree())
    return os.path.expanduser(s)


def skip_projects():
    """Fragments of transcript project-directory names that belong to benchmark sessions."""
    return OWN_MARKERS + tuple(cfg().get('skip_projects', []))
