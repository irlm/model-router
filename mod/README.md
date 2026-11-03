# model-router widget

A Claude Code mod that shows, on every machine you run Claude Code on, which model and
effort each kind of agent work is routed to (from the model-router benchmark), whether
that routing is still applied and still true here, and lets you re-check it with one key.

What you see:

- A status line under the prompt (the host prefixes the plugin's name):
  `5h 37% · 7d 62% · routed 2 · saved $7 since 11-02 · up to $25 less last 30d ($25 measured) · 1 to check · /router`.
  The percentages are the subscription's rate-limit windows as the last API response reported
  them; `routed` is what the router rewrote this session; `saved` is what the transcripts show
  since the last recorded change (what happened); `up to $N less last 30d` is what the suggestions add
  up to for the window that was, a look back and not a forecast, with the measured part named, since the
  rest is extrapolated or unmeasured; `to check` counts the advice. Each part appears only when it has something to say. The "Status
  line" option in `/config` makes it `minimal` (windows, routed, to check) or `off`.
- `/router` opens a pane whose glance is numbers that compare, one line each: the rate-limit
  windows as bars; one line on the checkout; the window's spend as a daily sparkline with the
  struggled and routed counts; the last change, with a before/after bar pair per class of Agent call
  and for main sessions (cost per call, cost per message), against the stretch just before the
  change and against the baseline before the first change; the suggestions, numbered, each with
  its estimate and what the transcripts show since the change (not applied, too early, holding,
  below estimate, wrong so far); one line on the families; the things to check. Details adds the
  families table, the weekly slots (spend, calls, struggled, routed), the consumption, each
  suggestion's basis and action, the earlier changes, what was learned on this machine, and the
  calls routed this session. Lines are cut to the pane's width; `/router check` prints the full text. While a job runs (Re-check, Ledger, Apply, Pull)
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
| | `prefer <class> <model> <effort>` | sets an override for this project: calls of that class run on that model and effort, before the family default |
| | `prefer clear <class>`, `prefer` | removes one, lists this project's |
| | `dismiss <n or id>`, `undismiss <id>` | hides a suggestion you judge wrong (by its number in the pane); Details lists the dismissed ones |
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

### Updating

The widget has two parts that update separately: the mod (the pane, the status line, the router
hook: the code Claude Code loads at start) and the repository it reads (the scripts, the routing,
the prices, the results). From a terminal on any machine:

```
claude plugin marketplace update model-router
claude plugin update model-router@model-router
```

The first pulls the repository (the marketplace clone); the second installs the mod's new version
from it. Then exit Claude Code and open it again: "Restart to apply changes" is literal, a running
session keeps the mod it started with. Inside a session, `/plugin` has the same two steps as menus.

What you see before the restart: the scripts and data are already new, and Refresh runs them
fresh, so new classes, suggestions and advice appear at once; the pane layout, the status line and
the router hook stay old until the restart. That mix is normal.

The pane's first line says which version of the repository it reads (`repo <commit>`), and `behind`
when origin has newer commits after a Fetch. In the marketplace clone, Pull is the same `git pull`
the marketplace update runs; in a checkout of your own, Pull updates it and the mod version you
run comes from the plugin update, not from the checkout. On Windows the commands are the same, in
PowerShell or CMD.

To see which version of the mod is loaded: `/plugin` lists installed plugins with their versions;
the marketplace's `mod/.claude-plugin/plugin.json` has the newest one. If the install ever looks
stuck, `claude plugin uninstall model-router@model-router` and the install line again is a clean
reset; the change log, the agent files and `/config` options are not in the plugin and survive it.

- `learned`: from this machine's own transcripts, not the benchmark: a project whose calls of one
  class struggle more than the rest of your work, or sessions that keep hitting the context boundary.

Agent calls are classed by agent type first, then by the prompt: code searches (Explore, Plan,
Codebase Onboarding Engineer), fact lookups (Web Researcher, or a short prompt asking for one
thing), browser flows (an agent whose name says browser, Evidence Collector, or a prompt that
reads as driving a page), code reviews, research reports, code changes, other. Code searches, fact
lookups, browser flows and research reports map to measured families and can carry a measured
suggestion; the others never get a downgrade suggested. A suggestion whose known saving is under $0.50 per window is not shown.

### Learned from your own sessions

The benchmark decides per kind of work. Your projects ask differently, and one of them may need more
than the decided model. So the scan also reads, per project and class of Agent call on this machine,
how many calls struggled: re-issued within the session (the same ask again, in other words), three or
more tool errors inside the subagent's work, or a failed result. The threshold is yours ("Struggle
threshold" in `/config`, default 25%) and the baseline is yours too: a cell is flagged only with at
least eight calls, at or above the threshold, and at twice the rate of the rest of your work on this
machine. So "too many" means more than your own other projects, on this computer, under this account.

A flagged cell is a `learned` suggestion that names the project and lists under Details what struggled,
because tool errors from the web are not the model's fault. If it is the task, step up for that project
only: `/router prefer research-synthesis opus low`. That writes an override into
`~/.claude/model-router/overrides.json` (never the repository), the router applies it before the
family default, in ask or auto mode, and the change is recorded so the pane counts what it saved.
`/router prefer clear <class>` undoes it.

Sessions that keep hitting the context boundary (compactions) are reported per project as well; the
suggestion there is to split the work, since a model change does not move the boundary.

### The cache, and switching between tasks

The prompt cache is on Anthropic's side, keyed by the exact prefix of a request, with a time to live of
five minutes by default and one hour where the session says so. Nothing in Claude Code or here creates
it; every turn re-reads the session's context from it at the cache-read price (a tenth of input or less)
and writes the new tail. Two things follow, both measured per project under Details:

- The fixed prefix (system prompt, tools, CLAUDE.md, agent files: `results/prefix`) is shared by every
  session and terminal on the account while the cache lives. `/clear` does not lose it; it drops only
  the conversation, which you do not want any more.
- A session that holds several unrelated tasks re-reads all of them on every turn. That is cheap per
  token and large in total: on the author's machine cache reads were 45% of main-session cost in 30
  days, and one session averaged 349k tokens per message. One session per task, in another terminal
  or through `claude --resume`, re-reads only its own context. Coming back to a session after the
  cache expired rewrites its whole context once (31 such returns in 30 days here, $38): come back within
  the hour, or let a background task do the waiting.

A project whose sessions re-read more than 150k tokens per message over 200 messages gets a `learned`
suggestion with the re-reading above 100k per message as its upper saving.

### After a change: what was really saved

A projected saving is the benchmark's number applied to your window. After a change, the pane
shows what your own transcripts saved since it, per unit of the same work:

- each class of Agent call (code searches, fact lookups, ...): the same work. The calls after the
  change are priced, token for token, at the rates of the model that did most of them before; that
  counterfactual minus what they really cost is the saving from the model change alone. Task size
  (a longer ask, more code to read) cancels out of it, and is shown beside it as tokens per call, with
  the price per million tokens on each side. What a different model does with the same ask (reads
  more, or less) does not cancel out; that is why the regression verdict stands next to it;
- main sessions: the same, per message, against the model and effort most messages ran on before.

A number that cannot mean anything yet says so on its line: too few messages and calls after the
change, or, for a change marked by hand, main sessions still on the same model and effort as
before (the mark records the date; the effort or model changes when you start a session with
`--effort low` or `--model opus`). The status line leaves such a number out.
Next to each class stands the family's last regression verdict: the cheaper model still does the
work here. Projected, realized, regress: three checks on one line of the pane, for example
`since 2026-11-02 10:40 (apply: agents: web-researcher.md), 3 days: saved $7.70 · projected $25 per 30d · regress find_feature ok`.
Details shows the per-class and main-session lines.

A change is recorded in `~/.claude/model-router/changes.jsonl` (never in the repository) by Apply
agents when it writes a file, by `/router routing auto` or "Always route this session", and by
`/router mark <note>` for changes the widget does not make itself, such as `claude --effort low`
or `claude --model opus` from today. Each change is measured in its own window, from it to the next change (or to now), in two ways: against
the stretch just before it (what that change did) and against the baseline before the first change
(what all the changes did together). The pane shows the latest change with both; Details lists the
earlier ones. The weekly slots under Details show the same window by time, regardless of changes.

Each suggestion carries its estimate and, once a change is recorded, what the transcripts show for its
scope since then, scaled to the window: `not applied` (the after side still runs what the suggestion
wants changed), `too early` (under a day or too few units), `holding` (real at or above half the
estimate), `below estimate`, `wrong so far` (dearer). You decide: `/router dismiss <n>` hides one you
judge wrong, and it stays listed under Details until `/router undismiss <id>`.
`python3 tools/changes.py list` prints the change log; `tools/routed_log.py list` what the router rewrote.

### Where it runs, and why it is not built in

One user-scope install serves the terminal, the desktop app's local sessions and the VS Code
extension on that computer (the docs: a plugin installed in one is available in the other two). The
pane draws in the terminal, in the desktop app's Code tab (not under WSL) and in the VS Code chat
panel from extension 2.1.299. Cloud sessions on claude.ai/code do not load the plugins installed on
your machine, so the widget does not reach them; Remote Control sessions run on your machine and do.

Claude Code itself offers only manual levers for a subagent's model (the docs read 2026-11-03):
`model` and `effort` in the agent file, the Agent tool's `model` parameter, the
`CLAUDE_CODE_SUBAGENT_MODEL` and `CLAUDE_CODE_SUBAGENT_EFFORT` variables, `/model`, `opusplan`
(Opus in plan mode, Sonnet to execute: by mode, not by kind of work) and fallback chains when a model
is overloaded. No page describes an automatic per-task router, and the advice is "route tasks to
faster, lower-cost models like Haiku" without saying which tasks. This widget is that rule with
numbers behind it, and the check that it holds on your own work.

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
