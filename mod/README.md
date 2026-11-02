# model-router widget

A Claude Code mod that shows, on every machine you run Claude Code on, which model and
effort each kind of agent work is routed to (from the model-router benchmark), whether
that routing is still applied and still true here, and lets you re-check it with one key.

What you see:

- A status line under the prompt (the host prefixes the plugin's name):
  `5h 37% · 7d 62% · routed 2 · saved $7 since 11-02 · $25 to save · 1 to check · /router`.
  The percentages are the subscription's rate-limit windows as the last API response reported
  them; `routed` is what the router rewrote this session; `saved` is what the transcripts show
  since the last recorded change; `to save` is what the suggestions add up to per window; `to
  check` counts the advice. Each part appears only when it has something to say. The "Status
  line" option in `/config` makes it `minimal` (windows, routed, to check) or `off`.
- `/router` opens a pane with, top to bottom: the rate-limit windows as bars; one line on the
  checkout; the window's spend as a daily sparkline; the families table (default model and effort,
  a success bar with the evidence, cost per success, whether the family's regression sample can run
  on this machine, the last check); the things to check; the suggestions, largest saving first, each
  with its share of the window's spend as a bar; the Agent calls routed this session. The glance
  shows three items per section and one line per item, cut to the pane's width; Details shows all
  of it, and `/router check` prints the full text. While a job runs (Re-check, Ledger, Apply, Pull)
  the pane shows only that job's output, and the summary returns when it ends. `Details` (`d`) adds the long sections: the
  agent files (applied or drifted), price freshness, ledger dates, the timer, what the last 30 days
  consumed (main sessions by model and effort, subagent calls by kind), and each suggestion's
  basis and action. `/router check` prints everything as text.

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
| Details / Less | | shows or hides the pane's long sections |
| | `mark <note>` | records a change you made by hand (effort, model), so the saving is counted from now |
| Refresh | `check` | `tools/status.py` (also prints the table as text) |
| Fetch origin | `fetch` | the same after `git fetch`, so behind/ahead are current |
| Re-check routing | `update` | `tools/update.py`: `regress.py` on every family that can run here, then commit and push the entry (`--no-commit` in the marketplace clone) |
| Ledger now | `ledger` | `tools/ledger.py --commit` (`--stdout` in the marketplace clone: the entry goes to the pane) |
| Apply agents | `apply` | `apply_agents.py`: write routing.json's model and effort into the agent files you have in `~/.claude/agents`; installs `agents/web-researcher.md` from the repository when missing; agent files you do not have are absent and skipped |
| Pull | `pull` | `git pull --ff-only` |

Setup on a machine: Python 3 on PATH (`python3`, `python` or `py`), git, and the `claude` CLI; then,
at the prompt of a terminal session:

```
/plugin install model-router --marketplace irlm/model-router
```

Answer `y` to add the marketplace, then pick the user scope. That is the whole setup. No credential
is needed: the marketplace is a public repository and git clones it anonymously. The clone the
install makes is a full checkout of this repository, and the widget reads from it whenever no
checkout of your own is at the path in `/config` ("model-router checkout", default
`~/Projects/Github/model-router`); the pane's first line then says `marketplace clone`. In that
clone nothing is committed: "Ledger now" prints the entry into the pane instead of writing it,
"Re-check routing" keeps its results local, and "Pull" is the same `git pull` that
`/plugin marketplace update model-router` does.

A checkout of your own is for the benchmark, the ledger timer and changing the code: clone the
repository to the default path, or anywhere and set the path in `/config`.

Agent calls are classed by agent type first, then by the prompt: code searches (Explore, Plan,
Codebase Onboarding Engineer), fact lookups (Web Researcher, or a short prompt asking for one
thing), browser flows (an agent whose name says browser, Evidence Collector, or a prompt that
reads as driving a page), code reviews, research reports, code changes, other. The first three
map to measured families and can carry a measured suggestion; the others never get a downgrade
suggested. A suggestion whose known saving is under $0.50 per window is not shown.

### After a change: what was really saved

A projected saving is the benchmark's number applied to your window. After a change, the pane
shows what your own transcripts saved since it, per unit of the same work:

- each class of Agent call (code searches, fact lookups, ...): cost per call before and after the
  change, times the calls after it, with the models on each side;
- main sessions: cost per message before and after (same unit; the mix of work can differ, so
  read it as a trend, not a receipt), and the top model/effort rows.

Next to each class stands the family's last regression verdict: the cheaper model still does the
work here. Projected, realized, regress: three checks on one line of the pane, for example
`since 2026-11-02 10:40 (apply: agents: web-researcher.md), 3 days: saved $7.70 · projected $25 per 30d · regress find_feature ok`.
Details shows the per-class and main-session lines.

A change is recorded in `~/.claude/model-router/changes.jsonl` (never in the repository) by Apply
agents when it writes a file, by `/router routing auto` or "Always route this session", and by
`/router mark <note>` for changes the widget does not make itself, such as `claude --effort low`
or `claude --model opus` from today. Each change is measured in its own window: from it to the next change (or to now), against the
stretch before it back to the previous change. The pane line shows the latest; Details lists the
earlier ones with their own numbers. `python3 tools/changes.py list` prints the log.

### Windows

Native Windows, from PowerShell or CMD. Inside WSL it is Linux: follow the steps above there.

1. Tools, once: [Git for Windows](https://git-scm.com/downloads/win) (git, which the install and
   the buttons use, and Git Bash for Claude Code's Bash tool); Python 3 (the python.org installer
   with "Add python.exe to PATH" ticked, or `winget install Python.Python.3.13`); Claude Code
   (PowerShell: `irm https://claude.ai/install.ps1 | iex`). No GitHub account or GitHub CLI is
   needed: the repository is public.
2. At the prompt of a Claude Code session, as above:
   `/plugin install model-router --marketplace irlm/model-router`. The widget then reads the
   install's own clone; nothing else to set up.
3. Only for the benchmark or to change the code: clone where the default path points. `~` is your
   profile folder on Windows, so the default `~/Projects/Github/model-router` means
   `C:\Users\<you>\Projects\Github\model-router`:

   ```powershell
   git clone https://github.com/irlm/model-router "$env:USERPROFILE\Projects\Github\model-router"
   ```

   Any other folder works too: set "model-router checkout" in `/config` to that folder, written as
   Windows writes it (`D:\src\model-router`).

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
