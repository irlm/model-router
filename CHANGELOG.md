# Changelog

The widget's version is `mod/.claude-plugin/plugin.json`; the directory publishes a new version when it
rises. Earlier versions are the `widget x.y.z:` commits in the git log.

## 0.24.0 — 2026-11-10

- `/router prune skills`: the skills nothing on this machine loaded in the window are listed name-only (Claude Code's
  `skillOverrides` in `~/.claude/settings.json`: the name stays, `/name` works, the description leaves every request —
  here 42 skills, about 4k tokens a request). A dry run lists them; `move` writes it; `revert` removes exactly what
  was written (`<config>/model-router/skills-pruned.json` keeps the record), and a skill you overrode by hand is never
  touched. A plugin's skills are left alone, since they leave the list only with their plugin. `/router prune all
  [move|revert]` does the agents and the skills in one (`tools/prune_skills.py --agents`). The skills suggestion in the
  pane names this first. `tools/fixed_text.py` reports every unused entry, not only the eight largest.

## 0.23.0 — 2026-11-10

- The monitor has a `[ Routing ]` frame, between the graph and the events: one line per agent of the run with what
  the Agent call asked for → what it ran on (`inherit → haiku low`), the family, the decision (auto, routed, kept,
  escalated) and its evidence (`measured 214/216, $0.0046/success`; "family not decided yet"; "no measured family
  covers it"); the main session's effort gear within the run (down to the measured effort, back up after tool
  errors); and, once every agent has ended, the run's cost on the decisions against the as-asked figure — the same
  tokens re-priced at catalog prices and labelled `est`, since the as-asked run never happened. The text view and
  the saved report (`## Routing`) carry the same lines. A long run shows the five lines that moved the most
  (escalations first, then by what the routing changed) with "N more"; `r` in the pane, or `/router monitor top` against
  `/router monitor`, switches between the five and every line. While agents still run the cost line says "so far". An
  agent now keeps what its call asked for, the decision and its tokens (state shape `live-9`).
- Tests: the paths the engine hands back on Windows (`D:\home\me\…`) are compared in POSIX form, which is what made the
  widget's first CI run on the Windows runner fail (two tests).

## 0.22.0 — 2026-11-09

An audit of the repository, fixed in one pass:

- The classifier is one rule in two places, kept identical by a test: the widget's `matchFamily` and the ledger's
  `classify` now check in the same order (browser, lookup, research, fix) and a prompt that asks for a code change
  (`fix`, `bug`, `implement`, …) is never a research note, in both; the ledger no longer counts a `Plan` agent as
  code-explore work, since the widget does not route it (what is counted and what is acted on agree again).
- Every tool resolves `<CLAUDE_CONFIG_DIR or ~/.claude>` through `tools/claude_home.py`; `tools/usage_scan.py`,
  which the ledger runs, read `~/.claude/projects` whatever `CLAUDE_CONFIG_DIR` said.
- Transcripts last written before the window began are skipped unread (the 30-day figures cannot be in them), so a
  years-old `~/.claude/projects` is not parsed on every refresh; the files that are read are closed (the
  ResourceWarning in the tests, and a handle that blocks a move or delete on Windows).
- What could not be read is said: Details lists `not read: rate limits (…)`, `context size`, `marketplace file`,
  `saved runs` with the reason, instead of a pane that shows no limits and looks healthy.
- The second tick also runs while the main session's own turn runs, so its elapsed time and cursor in the monitor
  move between tool calls. A Python that failed is probed again at the next refresh instead of being kept for the
  session. `known_marketplaces.json` with a byte-order mark parses. A report asked before `session.start` named
  the folder no longer targets `/docs/runs`. The command's argument hint lists every verb.
- Tests: the overrides and the routed log under a Windows working directory (`C:\Users\me\proj` → `C--Users-me-proj`);
  the keyword lists of the widget and the ledger compared; the widget's tests run on Windows and macOS in CI, not
  only Ubuntu. `GAPS.md` rewritten as the list of what is still open; what the 2026-10-31 plan asked for and has been
  done is summarised under it.

## 0.21.2 — 2026-11-09

- The main session's panel in the monitor shows whenever fewer than two agents are *at work*. 0.21.0 counted the
  finished agents that keep their tail, so after a run of two or more agents the panel stayed hidden until the next
  run began; the session's own tool calls were going unseen between runs.

## 0.21.1 — 2026-11-09

- A prompt that runs a test command is not a research note. "Run pytest and report the failures" on a general-purpose
  agent matched `report` and was routed to the research family (Sonnet low) in a real session; the classifier now
  skips the research match when the prompt names a test runner, and the keyword is `a report` / `the report` /
  `report on`, not the bare word. The same change in `tools/consumption.py`, so the ledger counts it the same way.

## 0.21.0 — 2026-11-09

- The run monitor draws the main session before any agent runs, instead of one line saying nothing has run: the
  `00 main session` box carries its state (`● WORKING` while a turn runs, `● IDLE` after) with the turns and cost so
  far, and the main session has a live panel of its own (its last tool calls, an error in red, how long the turn
  has run or idle since when), shown whenever fewer than two agents are at work. Agents hang under the box as they
  spawn, as before. A Windows session with the monitor open and no subagent yet looked dead; it was waiting.

## 0.20.1 — 2026-11-08

- The glance keeps only what is acted on: the header bar with three dim facts under it (the repository, the
  30-day spend, the routed count), Session live, Agents, Limits, To check, and the top three suggestions with a
  count of the rest. Details (d) shows every section, as before; `/router check` prints them all.

## 0.20.0 — 2026-11-08

- The main pane drawn like the run monitor: a header bar (the session's turns, cost, cache hit, context and model
  on the right; the loaded version under it), then every section in its own frame with a title, the border in the
  section's colour (Session live cyan, Agents green while any runs, Limits green/yellow/red by the fullest
  window, To check yellow, Routed cyan), the job's output in a frame of its own (cyan while it runs, red when it
  failed), and the buttons in a footer with a new `g` that opens the monitor. The lines inside are exactly what
  `/router check` prints: the producers are shared, only the framing changed.

## 0.19.2 — 2026-11-08

- Tests only: 0.19.1 shipped with one expectation in the wrong order (rebuilt runs come back by start time), so its
  CI run is red; nothing in the widget or the tools changed.

## 0.19.1 — 2026-11-08

- Runs rebuilt from the transcripts: a call made inside a subagent's own transcript now joins the run of the
  call that spawned it, under it, as the live graph draws it, instead of standing as a one-agent run of its own
  (`/router runs import --rebuild` redoes the imported files). Every run time is local, the same clock the run
  folders are named by: the list, the history and the reports said UTC while the folders said local.

## 0.19.0 — 2026-11-08

- Runs. The agents a prompt spawns are one run (a resume or a nested spawn joins its parent's run); a named task
  (`/router task start <name>` … `/router task end`) groups everything under it across prompts. The monitor
  shows the current run alone, names it under the header (its place among the session's runs, its words, agents,
  cost, ended or running, saved), and `h` lists the session's runs to pick one, with `c` back to the current.
- Runs are saved: when a run's last agent ends (or the task is ended) its JSON goes to
  `<config>/model-router/runs/<day>/<time>-<words>.json` with every agent, its answer and the events; `/router
  runs` lists what is saved, `/router runs show <id>` prints one, `/router runs import [--days N]` rebuilds runs
  for the days before the widget watched from the transcripts' Agent calls (prompts, models, costs; no timing).
- Reports: `/router monitor save [id]` (or `s` in the pane) writes the run into the project as
  `docs/runs/<day>-<words>.md`: what was asked, the graph as text, the agents with model, effort, cost and
  outcome, their answers, the events. New `tools/runs.py` behind the list, show, export and import.

## 0.18.1 — 2026-11-08

- An agent stopped before it answered (aborted by the person or the session) was drawn as DONE; it is now
  STOPPED, in red like a failure, counted apart in the header ("1 failed, 1 stopped"), with its own event line.

## 0.18.0 — 2026-11-08

- The run monitor is drawn: a header bar, the graph as real boxes with a border in the state's colour (cyan
  for the main session, green at work, yellow quiet, red failed, dim when done) placed on a grid, a column
  per depth and a centred tree down the rows, the arrows between them in box-drawing glyphs weighted by the
  context sent with the token label on the branch; beside it, when the pane is 130 columns or wider, the live
  panels of the agents at work (their last tool calls, a blinking cursor), under it when narrower; the event
  log in its own frame; a footer with `g` (the same run as text lines, the earlier view) and `m` (the main
  pane). `/router monitor` still prints the text drawing. Not drawn, by design: a blocked state or dependency
  arrows, since the engine reports who spawned whom, not who waits on whom.

## 0.17.0 — 2026-11-08

- The run monitor, after a first real run: an agent the engine resumes under the same id (a hand-back, a
  follow-up) is a new run of the same box ("03 general-purpose · run 2"), not a new agent, and a child hangs
  under the run that was active when it spawned, so it is drawn once; the whole box carries its state's
  colour (green at work, yellow quiet, red failed); wider boxes so the cost is not cut; the top border as wide
  as the rest; when fewer than two agents run, the last finished keep their tail in the live section.

## 0.16.2 — 2026-11-08

- Python 3.10's argparse drops the `--` that 0.16.1 put before the overrides script's words, so `/router prefer`
  still failed there; the script now splits the words after `--` off itself before parsing.

## 0.16.1 — 2026-11-08

- The routed log was never written and `/router prefer` could not set an override: the project key is the cwd
  with its slashes as dashes, so it begins with a dash, and argparse took it for an option ("expected one
  argument"). The key now travels as `--project=KEY` to the routed log and after `--` to the overrides script.
  Found with 0.15.1's toast of the first failed write.

## 0.16.0 — 2026-11-08

- The run monitor, a second pane (`/router monitor`): the session's agents as a graph, the main session at the
  root and each agent a box under the one that spawned it, the arrow weighted by the context it was sent
  (estimated from the prompt at 4 characters a token: heavy from 16k, medium from 4k, light below), the box
  carrying its state (RUNNING, QUIET after a minute without a request, DONE with its cost, FAILED), model and
  effort, elapsed and request count; under it the live tail of the agents at work (their last tool calls,
  an error in red) and the run's event log (spawned by whom, done in how long for how much, failed why).
  The same second tick as the agents block redraws it while any agent runs; the command prints the text too.

## 0.15.1 — 2026-11-08

- The pane says which widget version is loaded, and in yellow when the checkout already has another
  (`/reload-plugins` loads it): a pane that looks unchanged after a release no longer leaves the question open.
  `tools/release.py` refuses a tag while the module's version constant and plugin.json differ.
- Failures that were silent now say so: a spawn or routing hook that fails toasts its reason and lets the call
  run as asked; the routed log's first write failure of the session is toasted with its reason (routing stands).

## 0.15.0 — 2026-11-08

- Routing no longer rewrites the Agent tool's input. The decision is kept for the spawn the call makes
  (`agent.spawn` gets the model, and the prompt note for `repo_fix`) and for the subagent's own requests
  (`turn.step` gets the effort). In auto mode a tool input a plugin changes loses the classifier's review
  and the call is bounced once ("issue the Agent call once more"); every routed call paid that bounce.
  The agents block shows the routed effort from the spawn on. Ask, off, escalation and the routed log
  are unchanged.

## 0.14.1 — 2026-11-08

- The agents block names itself before any subagent has run: the full pane and `/router check` carry one
  dim line saying where the rows will appear; the glance stays as short as before.

## 0.14.0 — 2026-11-08

- The agents block: the subagents running in this session, one row each like a connection monitor
  (type, model and effort, measured family, task, requests so far, elapsed), children under their
  parent, a spinner in the header while any runs, a row quiet for a minute in yellow, the glance capped
  at 6 rows with "+N more"; a finished agent shows its cost and folds into the header's done count
  (failed ones counted). From `agent.spawn`, `turn.step` and `turn.complete`; a 1-second tick while
  agents run moves the clocks. `/router check` prints the same rows as text.

## 0.13.0 — 2026-11-08

- The pane opens with the session live: turns and their cost as a sparkline, cache hit, the effort gear per
  turn (`·` session, `↓` measured, `↑` back up after errors, `?` would have), the Agent calls routed and
  the families escalated, and the plan gauge (saved of projected). Figures come from the engine's own
  per-turn usage (`turn.complete`), priced from the catalog; no transcript read.
- Main-session effort control (`/router effort advise|auto|off`, `mainEffort` in /config; default advise):
  a prompt that reads as a measured family (a fact lookup, a browser flow, a fix with the test runner)
  runs its requests at the family's measured effort in auto mode; after 3 tool errors in the turn the
  requests go back to the session's own effort ("use the max when the task requires it"). Advise mode
  shows what it would have done and the estimate (results/cell8 effort ratios on the output).
- Escalation with evidence for Agent calls: a routed call that fails, or one re-issued within 10 minutes
  with the same words, escalates its family for the session; the next calls run as asked, the pane and
  the routed log say why (`escalated`).
- The glance shows less: the families line and the long suggestions header moved under Details.
- CI runs `claude plugin validate mod` and `claude plugin test mod`.
- Regression check 2026-11-08 on Claude Code 2.1.319: web_research 6/6 on haiku low.

## 0.12.0 — 2026-11-08

- `/router doctor`: the installation piece by piece (Claude Code, Python, git, checkout, widget version
  and tag, config dir, routed agents applied or missing, agent files loaded and parked, pinned sources,
  transcripts), each `ok` or `to do` with the step; `python3 tools/status.py --doctor` at a terminal.
- Agent files from outside this repository are pinned to their source commit (`/router agents pin <url>`);
  `/router agents check` shows what changed upstream as a diff with flags (a URL, a shell download, a
  secret's name or path, an instruction to hide or to ignore earlier ones, invisible Unicode, a `tools:`
  grant); `/router agents update` takes the unflagged changes, a flagged one only by name with
  `--accept-flags`. Nothing pulls an agent file on its own. A hand edit to a pinned file gets a "to check"
  line; `apply_agents.py` writing one does not.
- Versions are git tags `v<version>`: `python3 tools/release.py` checks the CHANGELOG entry and the clean
  tree, then tags; a version without its tag is a "to check" line; the tests keep plugin.json and the
  newest CHANGELOG entry equal.
- `/router agents` arguments are validated before anything runs (a URL or path for pin, `name.md` for update).
- After `/router prune move`, the agent-list line says the files are parked and that the next sessions
  show the shorter list, instead of asking for the move again.
- Install from a checkout without a push (`claude plugin marketplace add <checkout>`): Claude Code
  reads the widget from the folder; a commit shows after `/reload-plugins`. Documented in both READMEs.

## 0.11.0 — 2026-11-08

- `/router setup`: first run on a machine installs the routed agents and says what the pane shows.
- `/router prune [move|revert]`: the agent files nothing on this machine called, listed, parked in
  `~/.claude/agents.unused` (folders kept), restored.
- What every request carries (agent list, skill list, hook text, MCP instructions, loaded skill bodies),
  measured from the transcripts, with `learned` suggestions; the skill-list line sends you to
  `/skill-doctor` first (Claude Code 2.1.261+ has it) and adds what it lacks.
- Returns after an idle hour get their own line per project, whatever the session size, with what
  Claude Code's own idle compaction (2.1.299+, from 200k tokens) covers and what it does not.
- Agent files in folders under `~/.claude/agents` are found by status, apply and prune.
- `CLAUDE_CONFIG_DIR` honoured by every tool (`tools/claude_home.py`).
- Transcripts without the listing rows are said so under "to check" instead of showing zeros; the rows
  as each Claude Code version writes them are fixtures under `tools/fixtures/`.
- The saving is given as a share of the window's spend too; the consumption figures say they are a
  floor (side requests are not in the transcripts).
- Without Python the pane names the install command for the OS.

## 0.10.1 — 2026-11-03

- The status line shows the context size from the first turn; the per-turn cost joins it from the
  warning size.

## 0.10.0 — 2026-11-03

- A prompt that reads as a different task in a session re-reading a lot per turn gets the numbers and
  an offer to compact down to it.
