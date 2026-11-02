# model-router widget

A Claude Code mod that shows, on every machine you run Claude Code on, which model and
effort each kind of agent work is routed to (from the model-router benchmark), whether
that routing is still applied and still true here, and lets you re-check it with one key.

What you see:

- A status line under the prompt: `router: 5h 37% · 7d 62% · 2 suggestions · /router · 12:01`.
  The percentages are the subscription's rate-limit windows as the last API response reported
  them. Then the count of things to check and of suggestions, or `router ok`.
- `/router` opens a pane with, top to bottom: the rate-limit windows; the families table (default
  model and effort, evidence, cost per success, whether the family's regression sample can run on
  this machine, the last check); the agent files (applied or drifted), price freshness, ledger
  dates, the timer; the things to check; what the last 30 days consumed (main sessions by model
  and effort, subagent calls by kind); and the suggestions.

Suggestions say where the same work could consume less of the subscription. Catalog prices are
API-equivalent dollars, which on a subscription measure rate-limit headroom. Each suggestion
carries its evidence and a kind:

- `measured`: a decided family covers that kind of work (a fact lookup on a general-purpose
  agent instead of the routed Web Researcher).
- `extrapolated`: measured on the benchmark's tasks, applied to sessions it did not measure
  (main sessions at xhigh effort: the sweep found xhigh costs 1.3 to 1.5 times low for the same
  fixes, on tasks every effort solved).
- `unmeasured`: the stake is known, no cheaper model is (research reports on general-purpose
  agents; Fable in main sessions, where the measured families saw Opus equal at 37 to 40 percent
  of the cost). These say what to measure next, or what to try and compare in the next ledger.

The numbers come from `tools/consumption.py` (the local transcripts, last 30 days, with the
effort of each request) and the rules in `tools/status.py`, where every ratio is a named
constant with the cell it came from.

Routing each Agent call. When the main model starts a task through the Agent tool, the widget
looks at the agent type and the prompt. If a measured family covers that kind of task (a read-only
code search on Explore, a short fact lookup, a browser flow, a fix with the test runner in the
loop) and the call asks for something dearer than the family's decision (the main model by
inheritance, or an explicit bigger model), it acts by the "Route Agent calls" option:

- `ask` (the default): a question in the terminal with three answers: the measured model and
  effort with its evidence (`haiku low (measured 214/216, $0.005/success)`), keep what was asked,
  or always route for this session. A dismissed question keeps the call; so does a run with no
  one to ask.
- `auto`: the call is rewritten and a toast says so.
- `off`: nothing.

Nothing unmeasured is touched: a research report, a design, a review, a plan keep their model
(no blind downgrade). A call to an agent whose file already carries the routed model and effort is
left alone. For a fix with a runner the prompt gets one line asking the agent to run the test
command before finishing, since the 72/72 was measured with the runner in the loop. The pane and
`/router check` list the calls routed this session with their decision; `/router routing
ask|auto|off` switches the mode for the session, `/config` for good. The keyword lists that
classify a prompt are the same as `tools/consumption.py`'s, so what the ledger counts and what the
router acts on agree. The main session's own model is not touched: a mod can set a subagent's
model per call, the main model only `/model` can.

Buttons and verbs (`/router <verb>`):

| Button | Verb | Runs |
|---|---|---|
| | `routing ask\|auto\|off` | sets how Agent calls are routed for this session |
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

### Windows

Native Windows, from PowerShell or CMD. Inside WSL it is Linux: follow the steps above there.

1. Tools, once: [Git for Windows](https://git-scm.com/downloads/win) (git, which the install and
   the buttons use, and Git Bash for Claude Code's Bash tool); Python 3 (the python.org installer
   with "Add python.exe to PATH" ticked, or `winget install Python.Python.3.13`); the GitHub CLI
   (`winget install GitHub.cli`, then `gh auth login` and `gh auth setup-git`, so git can read the
   private repository); Claude Code (PowerShell: `irm https://claude.ai/install.ps1 | iex`).
2. Clone where the default path points. `~` is your profile folder on Windows, so the default
   `~/Projects/Github/model-router` means `C:\Users\<you>\Projects\Github\model-router`:

   ```powershell
   git clone https://github.com/irlm/model-router "$env:USERPROFILE\Projects\Github\model-router"
   ```

   Any other folder works too: install the mod, then set "model-router checkout" in `/config` to
   that folder, written as Windows writes it (`D:\src\model-router`).
3. At the prompt of a Claude Code session, as above:
   `/plugin install model-router --marketplace irlm/model-router`.

What differs on Windows. `python3` and `python` may be the Microsoft Store placeholders that
print "Python was not found" and fail; the mod skips a name that does not answer `Python 3` and
tries the next, down to `py`, the launcher the python.org installer adds. When none answers, the
status line says `no Python 3 on PATH`, and the "Python command" option names the one to use.
The ledger timer is a Linux systemd unit; on Windows the ledger runs when you press `l` in the
pane (or `/router ledger`), and the pane says so instead of advising the timer. Re-check can run
web_research, which needs only the `claude` CLI; the kernel families need Linux, and repo_fix
needs its clone and worktrees set up by hand. The scripts read and write UTF-8 on every platform:
the mod runs them with `PYTHONUTF8=1`, and each file read, write and git call names the encoding
itself, so they behave the same from a plain PowerShell window.

Which families can run here depends on the fixtures: web research needs only the `claude`
CLI; find_feature needs the linux-v6.12 tree; repo_fix needs a repo config (`bench/repo_fix/repos/<name>.json`, local) with its clone
and worktrees; fix_bug and write_tests need a kernel worktree and KUnit build and run by hand.
The pane says which, and why not.
