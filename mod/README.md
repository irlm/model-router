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
- `auto`: the subagent runs on the decided model and effort and a toast says so.

The decision is applied on the subagent itself, never on the Agent tool's input: the spawn the call
makes gets the model (`agent.spawn`) and each of the subagent's requests gets the effort (`turn.step`).
A tool input a plugin rewrites loses auto mode's review and the call is bounced once with "issue the
call once more"; the Agent call here stays as the model wrote it, so auto mode's verdict stands.
- `off`: nothing.

Nothing unmeasured is touched: a research report, a design, a review, a plan keep their model
(no blind downgrade). A prompt that names a test runner or asks for a code change is never read as a
research note, however it is worded ("run pytest and report", "compare the parsers and fix the bug"). A call to an agent whose file already carries the routed model and effort is
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

**From a checkout, without a push** (developing the widget, or trying a commit before it is on
GitHub): at a terminal,

```
claude plugin marketplace add ~/Projects/GitHub/model-router
claude plugin install model-router@model-router --scope user
```

Claude Code then reads the widget from that folder's `mod/` directly (`claude plugin list` prints
`Read from: .../model-router/mod`): a commit there shows at the next session start or after
`/reload-plugins`, with no `plugin update`. `claude plugin marketplace remove model-router` takes the
local marketplace out when you switch to the GitHub one.

**First run on a machine: `/router setup`, then `/router doctor` to see each piece as ok or to do.** It installs the routed agent files the repository ships
(`apply_agents.py`), then says what the pane shows: the yellow "to check" lines are things to do, not
failures (a fresh machine has "agent web-researcher.md not installed yet" until apply runs); a
suggestion line is an estimate with its basis under Details; in ask mode the router asks before it
moves an Agent call. When many agent files sit in `~/.claude/agents`, it points to `/router prune`.

### The session live, and the effort gear

The first lines of the pane are the session as it runs, from the engine's own per-turn figures
(`turn.complete` carries each turn's tokens and model; priced from the catalog, cache writes at the
1h multiplier), so nothing is read from disk for them:

```
this session · 12 turns · $1.84 · cache hit 93% · ctx 148k · fable-5-1 high
  $/turn   ▁▂▁▃▂▁▂▆▂▁▁▂  max $0.41 · 1 turn with 3+ tool errors
  effort   ··↓↓··↑·····          auto: 2 at the measured effort (est $0.05 less), 1 back up after errors
  agents   3 calls · 2 routed · escalated: find_feature (a call routed to haiku low failed)
  plan     saved $13 of $72 projected ███░░░░░░░ 18% · since 10-30
```

The effort strip is one mark per turn: `·` ran at the session's effort, `↓` at a measured family's
effort, `↑` went back up inside the turn after 3 tool errors, `?` would have gone down (advise mode).
The plan gauge is what the transcripts show saved since the last change against what the suggestion
projected: the same two numbers as "After a change", as a bar.

**Agents running.** While subagents run, the block under the live lines lists them the way a
connection monitor lists connections:

```
▘ agents running 2 · done 5 ($0.31, 1 failed)
  | Explore                haiku low   find_feature   find the parser                     4 steps    12s
  | general-purpose        fable high  unmeasured     compare three queues                9 steps    48s
    └ | Web Researcher     haiku low   web_research   look up the RFC                     2 steps     5s
  ✓ Explore                haiku low   find_feature   find the schema loader              6 steps    20s  $0.02
```

One row per agent: its type, the model and effort it runs at, the measured family its prompt read as,
the task, requests so far and elapsed time; a child under the agent that spawned it. The spinner moves
in the header only; a row with no request for a minute turns yellow with `quiet`; the glance shows six
rows and `+N more running, slowest …` (Details lists all). A finished agent shows its cost (known only
when the run ends: the engine reports tokens per completed turn, nothing mid-run, so no tokens-per-second
is shown) and folds into the header's `done` count, `failed` counted separately. The rows come from
`agent.spawn`, `turn.step` and `turn.complete`; a one-second tick runs only while agents run.

**The pane's look.** Since 0.20.0 the main pane is drawn like the monitor: a header bar with the session's
figures, each section in a titled frame whose border carries its colour (Limits turn yellow at half a window and
red at 80%, Agents green while any runs, To check yellow), the job output framed, the buttons in a footer. The
text inside each frame is what `/router check` prints, line for line. The glance shows the header with the repository,
the spend and the routed count under it, Session live, Agents, Limits, To check and the top three suggestions; Details
(`d`) adds every other section.

**The run monitor** (`/router monitor`) is the same run drawn as a graph, in its own pane. The main session is
the root box (cyan); each agent is a box to the right of the one that spawned it, placed on a grid (a column per
depth, a centred tree down the rows), its border in the state's colour: green at work, yellow QUIET after a
minute without a request, red FAILED, dim when DONE with its cost. The arrow from spawner to child is weighted by
the context the child was sent, estimated from the prompt at 4 characters a token (`━━` from 16k, `──` from 4k,
`┄┄` below) with the estimate labelled on the branch. An agent the engine resumes under the same id (a hand-back,
a follow-up) is a new run of the same box, "03 general-purpose · run 2", and a child hangs under the run that
was active when it spawned. Beside the graph, when the pane is 130 columns or wider (under it when narrower),
the live panels of the agents at work: their last tool calls as the engine saw them (a command, a file read, a
search), an error in red, a blinking cursor while the agent runs; when fewer than two run, the last finished
keep their panel. Then the run's event log (spawned on what by whom, done in how long for how much, failed why).
Between the graph and the events, `[ Routing ]` says what the routing did to this run: one line per agent, what the
call asked for → what it ran on (`inherit → haiku low`), the family, the decision and its evidence (`measured 214/216,
$0.0046/success`, or why it was left alone: no measured family, a family not decided yet, escalated); the main session's
effort gear within the run; and, once every agent has ended, `run on the decisions: $0.21 · as asked, est: $0.38` — the
same tokens re-priced at catalog prices, an estimate by construction, since the as-asked run never happened. A long
run shows the five lines that moved the most (escalations first, then the routed calls by what the routing changed) and
"N more"; `r` shows every line (`/router monitor top` prints the five, `/router monitor` all).
`g` switches to the same run as text lines, one line one row, which `/router monitor` also prints; `m` opens the
main pane. Before any agent has run the main session is drawn alone: its box says `● WORKING` while a turn runs and
`● IDLE` after, with the turns and cost so far, and a panel of its own lists the main session's last tool calls
(shown whenever fewer than two agents are at work); agents hang under the box as they spawn. Nothing here is a dependency graph of the task: the engine reports who spawned whom, not who waits
on whom, so no box is marked blocked and no waiting arrow is drawn.

**Runs, history and reports.** The monitor shows one run at a time: the agents the current prompt spawned (a
nested spawn or a resume joins its parent's run), or everything under a named task opened with `/router task
start <name>` and closed with `/router task end`, across as many prompts as it takes. The line under the header
names the run: its place among the session's runs, its words, agents and cost, whether it ended and was saved.
`h` lists the session's runs (pick one by its number; `c` returns to the current) and the runs saved on this
machine. A run is saved when its last agent ends (a task when it is ended): one JSON file under
`<config>/model-router/runs/<day>/`, with every agent, its final answer and the events, so a long day is many
small files rather than one growing pane. `/router runs` lists them, `/router runs show <id>` prints one, and
`/router runs import [--days N]` rebuilds the days before the widget watched from the transcripts' Agent calls
(prompt, model, cost; no per-second timing and no tool tail, which the engine reports only while the widget is
loaded). `/router monitor save [id]`, or `s` in the pane, writes a run into the project as
`docs/runs/<day>-<words>.md`: what was asked, the graph as text, the agents with model, effort, cost and
outcome, their answers, the events; the document to review a long investigation or hand to someone.

**Main-session effort** (`/router effort advise|auto|off`; `mainEffort` in `/config`, default
`advise`). The router routes Agent calls; the main session's requests it did not touch until now.
Before each main-loop request the engine lets a plugin name another effort (`turn.step`); the model
stays, since changing the model would re-write the cache. The rule: when the prompt reads as a
measured family (the same matcher as for Agent calls: a short fact lookup, a browser flow, a fix with
the test runner in the loop), the turn's requests run at that family's measured effort, `low` for every
family measured so far. Up: once the turn has hit 3 tool errors, the requests go back to the session's
own effort, the signal the transcripts' struggle measure is built on. Anything the matcher does not
recognise runs as the session has it. Advise mode changes nothing and says, per turn, what auto would
have done and the estimate: the cell8 effort ratios (high 1.06-1.16x of low, xhigh 1.30-1.52x) on the
turn's output cost, which is the part effort moves. Main sessions were not measured in the benchmark;
that is why the default is advise and the figure says `est`.

**Escalation for Agent calls.** A call the router moved down that failed (a tool error), or that the
main model re-issued within 10 minutes with mostly the same words, escalates its family for the rest of
the session: the next calls run as the main model asked, the routed log records `escalated` with the
reason, the pane shows it on the `agents` line. No call is re-run on its own: a second run doubles the
cost and may repeat an edit; the main model's own re-issue is the signal, and it is then left alone.

### Requirements and what it reads

Python 3 (3.10 or newer), git and the `claude` CLI on PATH; `CLAUDE_CONFIG_DIR` is honoured when
Claude Code runs with one. Without Python the pane says so, with the install command for your OS, and
nothing else runs: the data side (`tools/*.py`) reads your transcripts with it.

Everything stays on your machine. The widget reads `~/.claude/projects` (the transcripts: usage
numbers, Agent calls, the listing rows), `~/.claude/agents` and `~/.claude/plugins`; it writes the
routed agent files under `~/.claude/agents`, its own files under `~/.claude/model-router`
(overrides, dismissals, the change log, the routed log), and the ledger into the checkout when you
have one. Nothing is sent anywhere: no telemetry, no network call but `git fetch`/`pull` against the
repository and, in the benchmark, the model calls you start yourself.

The dollar figures are catalog prices for the tokens the transcripts record. They are a floor: the
side requests Claude Code makes (titles, summaries, the compaction itself) are not written there, as
cccost's author showed. On a subscription they are headroom, not a bill, so the status line and the
suggestions header give the saving as a share of the window's spend too.

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

### What every request carries

Before any task, each request carries the list of agent descriptions, the list of skill names and
descriptions, the text hooks add at session start and the instructions of the MCP servers. They are
written to the cache when a session starts and again when it comes back after the cache expired, and
re-read on every request in between. The transcripts record each list, so `tools/fixed_text.py`
counts their size (characters / 4, an estimate) and what carrying them cost in the window, and which
entries nothing on this machine used. Three `learned` suggestions come from it:

- **agent list**: the agents no Agent call named in the window, and their share of the cost.
  `tools/prune_agents.py` moves the agent files no transcript ever called to `~/.claude/agents.unused`,
  folders kept; Claude Code documents no setting that takes an agent out of the list.
- **skill list**: the skills never loaded, by the plugin they come with. A skill of your own leaves
  the list in `/skills` (`skillOverrides`) or with `disable-model-invocation: true`; a plugin's skills
  leave it only with the plugin, so the saving is an upper bound.
- **a loaded skill**: a skill's body stays in the session from its load to the next compaction. When
  re-reading it cost more than the floor, the line says how often it was loaded and how much of the
  body is shell in fenced blocks. From 30% it reads as a procedure a script could hold (a script is
  run, not read), and that share of the cost is the upper saving; under it the body is guidance and
  no saving is claimed. The line carries the digest of the body: a skill that changed is a new line,
  also after you dismissed the old one. Nothing rewrites a skill for you: no check here can say the
  rewritten skill still does its job.

`python3 tools/status.py` prints the four sizes and the loaded skills under "carried by every request".
Claude Code has part of this itself since 2.1.261: `/skill-doctor` lists the unused skills with what
each costs in context, in the `/plugin` manager's Stats tab. The skill-list suggestion sends you there
first; what it adds is the grouping by plugin, and the agent list, the hook text and the MCP
instructions, which `/skill-doctor` does not cover. Pruning agents: `/router prune` lists the files
nothing on this machine has called, `/router prune move` parks them in `~/.claude/agents.unused`
(folders kept), `/router prune revert` brings them back.

When the transcripts carry none of the listing rows (a Claude Code version that writes them
differently), the pane says so under "to check" instead of showing zeros. The rows as each version
writes them are kept as fixtures (`tools/fixtures/transcript-<version>.jsonl`, content replaced), so a
change breaks the tests here, not the numbers on a user's machine.

### Agent files from outside this repository

An agent file is instructions the model follows with your permissions, Bash included, so a change to
one is treated like a code change: nothing here pulls an agent file on its own. The files this
repository ships (`agents/`) are versioned with it. The others on your machine (a collection such as
`agency-agents`) are pinned: `/router agents pin <repository url>` clones the source shallowly, finds
each of your agent files by name in it and records the commit and a digest per file, with a copy of
the file as it came, under `~/.claude/model-router/`. From then on:

- `/router agents check` clones the source again and shows, per pinned file, the diff since the pin
  with flags on the added lines that deserve a second look: a URL, a shell download or exec (`curl`,
  `wget`, `base64`, `eval`, `sudo`, `rm -rf`), a secret's path or name (`~/.ssh`, `.env`, token,
  password, key), an instruction to hide something or to ignore earlier instructions, invisible
  Unicode, a `tools:` line that grants Bash or writing. A flag cannot clear or convict a change; a
  human reading the diff does that. The pane's "to check" says how many pinned files changed and how
  many are flagged; status never touches the network, only `check` and `update` do.
- `/router agents update` takes the unflagged changes and re-pins; a flagged file is taken only by
  name, `/router agents update <file.md> --accept-flags`, once you have read its diff. Then
  `/router apply` puts the routed model and effort back into the routed ones.
- A pinned file edited on disk by anything but `apply` or `update` gets a "to check" line (the digest
  of the last write this repository made is kept); a pin not checked in 30 days gets one too.

Forking the source gives no more safety than this: the merge is the same diff read by the same eyes,
and your own edits (model, effort, the test-running instruction) live in `routing.json` and are
re-applied, so no fork is needed to keep them. `python3 tools/agent_sources.py {pin,check,update,list}`
at a terminal does the same.

### Installation status

`/router doctor` lists the installation piece by piece, each `ok` or `to do` with the step: Claude Code
and its version, Python, git, the checkout (yours or the install's clone, behind origin or not), the
widget version and whether it is tagged, the config dir in use, the routed agent files (applied,
drifted, not installed yet, or not on this machine because nothing ships them), the agent files loaded
and parked, the agent sources pinned or not, and whether the transcripts in the window were read and
carried the listing rows. On a machine where `/router setup` was never run it says
`to do routed agents ... -> /router setup (runs apply)`. `python3 tools/status.py --doctor` prints the
same at a terminal.

### Versions

A version is a git tag `v<version>`, `<version>` being `mod/.claude-plugin/plugin.json`; the directory
publishes a version when the number rises. `python3 tools/release.py` checks that the version is the
newest `CHANGELOG.md` entry and the tree is clean, then tags HEAD; `git push --tags` publishes the tag.
A machine that wants to stay on a version checks it out in its clone (`git checkout v0.12.0`) and
skips "Pull". A committed version without its tag is a "to check" line in the pane.

### Coming back after the cache expired

The server cache lives an hour on a subscription (five minutes on an API key). A session resumed
after that re-writes its whole context at the cache-write price: on this machine four returns cost
$10 in a month, more than the lists above. From 200k tokens Claude Code 2.1.299+ compacts an idle
session by itself after about 54 minutes (`idleCompaction` in settings.json;
`CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS` lowers the bar to 100k; it needs the terminal open and the
machine awake), and 2.1.304+ warns on resume when the re-write would take a noticeable share of the
5-hour window. Below 200k nothing native helps, so a `learned` line per project counts the returns
after an idle hour and what they re-wrote; the move is `/compact` before leaving, or `/clear` when the
task is done. Above 200k the line says the native compaction should have run, and to check it is on.

### A different task in a big session

The widget watches each prompt you type. It keeps the words of the session's earlier prompts (seeded
from the transcript, so the first task counts) and the ticket ids they mention; a prompt whose words
are 70% new to the session, or that names a ticket the session has not seen, reads as a different
task. Words only: two tasks that share a vocabulary pass, and the same task said in new words may
not. When that happens in a session already re-reading more than the "Context warning" option
(default 100k tokens per turn), one question appears with the numbers: what this session re-reads
per turn and costs at the model's cache-read price, what a new window would, and the two over 50
turns. The answers: compact now, keeping only the new task (the widget asks the session to compact
with that instruction); send it here; or stop asking this session. The prompt is never dropped or
rewritten. The status line always shows the context size, `ctx 23k`, when the host reports it, and adds what
re-reading it costs per turn from the warning size on: `ctx 240k ($0.06/turn re-read)`; the pane
counts the switches seen and compacted. The same holds in the desktop app and VS Code: a new
window or tab is a new session, and that is the cheap way.

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

What else exists (checked 2026-11-08): ccusage and its forks read the same transcripts for cost
tables; claude-usage-analyzer (ccwhy) and cclint add suggestions and a lint of CLAUDE.md, hooks and
skills, with no saving estimated and nothing measured afterwards; Microsoft's TokenEconomizer prunes
unused tools into deny lists and learns repository facts; llm-router and AutoRouter route by
heuristics. None routes from a measured benchmark per kind of task, and none checks what a change
saved in the transcripts since; that is what this one does.

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
