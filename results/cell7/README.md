# Cell 7: the first non-Anthropic model, through its own harness (2026-10-30)

The find-feature family (72 tasks, string-verified truth, agent with search tools in the pinned
Linux v6.12 tree) run on OpenAI's cheapest tier, `gpt-6-luna`, through the Codex CLI
(`codex exec --json`, ChatGPT login), three trials at low reasoning effort. The same checker, the
same prompts, the same receipt shape (`bench/common/harness.py`); only the agent program and the
model differ. Receipts: `runs/find_feature/runs-gpt-6-luna-low-t*.jsonl`.

`decide.py` chose this run: `gpt-6-luna` is the one catalog model not dearer than the current
default (Haiku, same list price), so it is the only one that could change a decision on cost, and
find-feature is the cheapest family to run it on (about $0.04 per trial).

## Result

| Model, harness | Correct / 216 (3 trials) | Per trial | Cost per correct | Wall per task | Turns | Context per task |
|---|---|---|---|---|---|---|
| claude-haiku-5-5, Claude Code | 214 (0.991) | 70, 72, 72 | $0.0046 (trial 1 cold: $0.0067) | 6.4 s | 3.0 | 27k written + 61k read from cache |
| gpt-6-luna, Codex CLI | 209 (0.968) | 70, 69, 70 | $0.0005 | 4.3 s | 2.2 | 2.8k uncached + 28k cached |

Both models cost $0.10 / $0.50 per million tokens. The 9x gap in cost per task is the harness, not
the model: every Claude Code session carries about 95k tokens of fixed prefix (system prompt,
tools, the 184 agent files), 27k of it written to cache at twice the input price; a Codex session
carries about 31k, nearly all cached. For a two-tool task the prefix is the bill.

## The misses

Seven in 216, and they are not noise. The same two caller tasks fail in every trial with the same
answer each time:

| Task | Truth (files that call the symbol) | gpt-6-luna, all three trials | Haiku |
|---|---|---|---|
| callers-08 | include/linux/string.h, io_uring/register.c, mm/vmstat.c | the last two only | all three |
| callers-09 | drivers/gpio/gpio-sim.c, lib/string_helpers.c, lib/vsprintf.c | the first and last only | all three |

The pattern: one shell search, then an answer; the file that also holds the symbol's definition
(or an inline wrapper in a header) is dropped as "the definition", although it contains a real
call too. Haiku opened the files and kept them. The seventh miss is one abstention in trial 2
(`fields-04`). Haiku's two misses over three trials were different tasks each time.

## Reading

1. **The rule keeps Haiku.** The family's bar is the best rate (1.000, Sonnet and Fable) minus
   0.02; Haiku is at 0.991, gpt-6-luna at 0.968. Cheaper by 9x, but below the bar, and the misses
   are systematic on caller questions, which is what this family is for. `decide.py` says so from
   the receipts; nothing was hand-picked.
2. **Cross-provider numbers are comparable on the checker, not on the tool loop.** Codex has its
   own tools (a shell) inside a sandbox; Claude Code was limited to Read, Glob and Grep. Both had
   what the task needs. The cost difference is mostly the fixed prefix each harness sends, which
   is a real part of the bill either way.
3. **What it would take for this model to win a family:** the same rate as the default. On
   find-feature that means the caller tasks. A different prompt wording ("include files that also
   define the symbol") would probably fix these two, but the prompt is fixed across models on
   purpose; changing it would be a new cell for every model.
4. **Applying a non-Anthropic winner** is a separate problem: Claude Code agent files can only
   name Anthropic models. If this model had won, `routing.json` would record it and the agent
   files would still get the cheapest Anthropic candidate above the bar, with a note.

## Limits

- One family, one model, one provider. Since 2026-10-31 every runner takes `--harness`: the code
  families run Codex in a workspace-write sandbox with the build directory as an extra writable
  root. The runner arm does not work inside that sandbox: it blocks ptrace, and KUnit's UML kernel
  needs it (the same suite ran 15/15 directly and "0 tests, 1 error" under the sandbox), so
  `--kunit` through Codex needs `--codex-full-access`, which drops the sandbox and is never the
  default. The browser families need the Claude-in-Chrome tools, which Codex does not have, so they
  offer only Claude Code.
- Codex cannot be held to a turn limit or a tool list, only to its sandbox (read-only here).
- Codex ran on a ChatGPT login; the dollars are the API list price for the tokens it reported.
