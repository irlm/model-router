# Changelog

The widget's version is `mod/.claude-plugin/plugin.json`; the directory publishes a new version when it
rises. Earlier versions are the `widget x.y.z:` commits in the git log.

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
