# Prefix after pruning the agent files (2026-11-01)

Same trivial call twice before and twice after `tools/prune_agents.py` moved 179 of the 184 files in
`~/.claude/agents` to `~/.claude/agents.unused` (kept: the one agent ever called in a transcript, Product
Manager, and the four files routing.json routes). `claude -p --model claude-haiku-5-5 --effort low
--max-turns 1 --allowed-tools Read`, prompt "Reply with the single word OK.", cwd with no CLAUDE.md,
Claude Code 2.1.314.

| | input | cache write | cache read | total prefix | cost (catalog) |
|---|---|---|---|---|---|
| before, call 1 | 2 | 29,380 | 11,383 | 40,765 | $0.0060 |
| before, call 2 | 2 | 27,454 | 11,382 | 38,838 | $0.0056 |
| after, call 1 | 2 | 8,699 | 13,961 | 22,662 | $0.0019 |
| after, call 2 | 2 | 0 | 22,660 | 22,662 | $0.0002 |

Claude Code updated itself to 2.1.316 between the two pairs, so the pairs were repeated on 2.1.316 with the
179 files restored and then pruned again: 38,809 and 40,735 tokens with 184 files, 24,588 and 22,662 with 5.
The agent list was about 17k tokens of every request (matches `results/cell1/PREFIX.md`), 40-44% of this
minimal prefix. It is paid on every turn of every session as a cache read, and again as a cache write
whenever the cache has expired. Reverse with `python3 tools/prune_agents.py --revert`.

## Connectors are the other variable (2026-11-01)

The same trivial call measured 22,688 and 24,617 tokens minutes apart. The difference is the
claude.ai Claude Docs connector: when it connects before the first request, its instructions
and three tool definitions (about 1,900 tokens) are in the prompt; when it does not, they are
not. The widget plugin (`mod/`) adds nothing: with `--strict-mcp-config` the figure is 22,688
with the plugin enabled and 22,690 disabled. `regress.py` now measures the prefix with MCP
servers skipped, so the ledger tracks the agent files and the engine, not connector timing.
