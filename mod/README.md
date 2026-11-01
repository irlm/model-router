# model-router widget

A Claude Code mod that shows, on every machine you run Claude Code on, which model and
effort each kind of agent work is routed to (from the model-router benchmark), whether
that routing is still applied and still true here, and lets you re-check it with one key.

What you see:

- A status line under the prompt: `router ok · v1.1 · 3 families checkable here · Claude Code 2.1.316 · 12:01`,
  or `router: 2 to check · /router` when something is worth doing.
- `/router` opens a pane: the families table (default model and effort, evidence, cost per
  success, whether the family's regression sample can run on this machine, the last check),
  the agent files (applied or drifted), price freshness, the ledger dates, the timer, and
  the list of things to check.

Buttons and verbs (`/router <verb>`):

| Button | Verb | Runs |
|---|---|---|
| Refresh | `check` | `tools/status.py` (also prints the table as text) |
| Fetch origin | `fetch` | the same after `git fetch`, so behind/ahead are current |
| Re-check routing | `update` | `tools/update.py`: `regress.py` on every family that can run here, then commit and push the entry |
| Ledger now | `ledger` | `tools/ledger.py --commit` |
| Apply agents | `apply` | `apply_agents.py`: write routing.json's model and effort into `~/.claude/agents` |
| Pull | `pull` | `git pull --ff-only` |

Setup on a machine:

1. Clone the model-router repository (private) to `~/Projects/Github/model-router`, or set the
   path in `/config` under model-router after installing.
2. Python 3 on PATH (`python3`, `python` or `py`), git, and the `claude` CLI.
3. Install the mod from the repository's marketplace, at the prompt of a terminal session:

```
/plugin install model-router --marketplace irlm/model-router
```

Answer `y` to add the marketplace, then pick the user scope. A private repository installs
only for GitHub accounts that can read it and whose machine already has a git credential
for github.com (`gh auth login` then `gh auth setup-git`, or an SSH key).

Which families can run here depends on the fixtures: web research needs only the `claude`
CLI; find_feature needs the linux-v6.12 tree; repo_fix needs a repo config (`bench/repo_fix/repos/<name>.json`, local) with its clone
and worktrees; fix_bug and write_tests need a kernel worktree and KUnit build and run by hand.
The pane says which, and why not.
