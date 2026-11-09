# Changelog

The widget's version is `mod/.claude-plugin/plugin.json`; the directory publishes a new version when it
rises. Earlier versions are the `widget x.y.z:` commits in the git log.

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
