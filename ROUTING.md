# Routing v1: which model, at which effort, for which kind of agent work

Decided 2026-10-30 from three families measured on our own tasks (`results/cell1`, `results/cell2`),
revised the same day after cell 3 (harder bugs, `results/cell3`).
Machine-readable copy: `routing.json`. Applied to the agent files with `apply_agents.py`.
This is version 1. It covers three families and says "no decision" for the rest.

## Before v1

Every subagent inherited the main conversation's model, Fable 5.1, at effort `xhigh`
(`effortLevel` in `~/.claude/settings.json`). That is the most expensive setting on every axis,
and none of the three measured families needed it.

## The rules

| Family | Default | Step-up | Escalation rule | Evidence (all at effort low) |
|---|---|---|---|---|
| **Find a feature in a huge codebase.** Locate code, callers, struct fields, dispatch targets with search tools. No writes. | `haiku`, `low` | `sonnet`, `low`, when a 1-in-80 wrong answer costs more than 18x the session | None. Misses are confident answers, so there is no failure signal to trigger on. | Haiku 214/216 over 3 trials (98.8%; medium effort 213/216, bought nothing). Sonnet 144/144 over 2 cold trials. Fable 72/72. Cold cost per task $0.0067 / $0.119 / $0.578. |
| **Fix a bug with a failing test.** The test names the failing case; the agent reads and edits. | `haiku`, `low`, **with the test runner in the loop** | None needed | Not needed with the runner: 21/21 at every tier. Without a runner no tier is reliable when there may be more than one defect, and a bigger model fails the same way. | Single-site bugs: 10/10 on every tier, no runs ($0.012 / $0.149 / $0.748 per task). Hard tier, 11 hidden-helper and 10 two-site bugs: with runner 21/21 on every tier ($0.014 / $0.197 / $0.885 per task); without runner 16 / 14 / 16 of 21, every miss a partial fix that stopped after one defect (`results/cell3`). |
| **Write tests for a function.** Success = builds, passes on the real code, fails on a seeded bug. | `haiku`, `low`, **with the test runner in the loop** | None needed | Not needed: with the runner every tier is 10/10 | With runner 10/10 on every tier at $0.025 / $0.287 / $1.51 per task. Without runner 5 / 7 / 4 of 10, cost per success $0.049 / $0.370 / $4.58. Every tier ships wrong expected values when it cannot run. |
| **Everything else** (review, design, writing, browser flows, data work) | `inherit` (unchanged) | | | No evidence. Not routed. |

Prices are list API prices from `catalog/models.json` (Haiku 5.5 $0.10/$0.50, Sonnet 5.5 $2/$10,
Fable 5.1 $10/$50 per million in/out). Opus 5.5 was not measured: it sits between Sonnet and
Fable, and Sonnet already saturated every family.

## Cross-family rules

1. **Effort low first.** The one effort sweep (Haiku, find-feature) showed medium buying nothing.
   No family needed more than low on any tier.
2. **A checker before a bigger model.** Two families now show it. Write-tests: Haiku with a test
   runner beat Fable without one on quality (10/10 vs 4/10) and cost per success (180x). Fix-bug,
   hard tier: Haiku with the runner 21/21 at $0.014, Fable without it 16/21 at $1.127 per success
   (80x). If an agent can be given build or tests, do that before raising its model.
3. **No blind downgrade.** Where there is no mechanical checker, a cheap model's miss is silent.
   Unmeasured families stay on `inherit` until they are measured.
4. **Count sessions, not tokens, on expensive models.** Each new headless session pays about
   95k tokens of fixed Claude Code prefix, 27k of it written to cache: about $0.0055 on Haiku,
   $0.11 on Sonnet, $0.55 on Fable before any work (`results/cell1/PREFIX.md`). For short tasks
   that is over 90% of the bill. Many short sessions belong on Haiku; an expensive model should
   get few, long sessions. The 184 agent files are about 17k of that prefix on every model.
5. **The user overrides.** Precedence, from the Claude Code docs: the per-invocation `model`
   on an Agent call, then the agent file's `model`/`effort`, then `CLAUDE_CODE_SUBAGENT_MODEL`,
   then the main conversation's model. Anything above this file wins.

## Where the rules live

- `routing.json`: the same table, for scripts and agents to read.
- Agent files (`~/.claude/agents/*.md`): `model:` and `effort:` frontmatter, plus a marked
  "Routing rule" paragraph after the frontmatter where cell 3 showed the instruction matters more
  than the model (run the tests before finishing). Set by `python3 apply_agents.py`, removed by
  `python3 apply_agents.py --revert`. Applied:

  | Agent file | Family | Set to |
  |---|---|---|
  | `engineering-codebase-onboarding-engineer.md` | find_feature | haiku / low |
  | `engineering-minimal-change-engineer.md` | fix_bug | haiku / low, plus: run the covering tests before finishing, keep going if they still fail |
  | `testing-api-tester.md` | write_tests | haiku / low, plus: run every test you write before finishing |

  The other 181 files are untouched. `CLAUDE_CODE_SUBAGENT_MODEL` is not set, on purpose: it
  would downgrade unmeasured families.

## Assumptions to keep in view

- All evidence is from one C codebase (Linux 6.12) with KUnit as the checker. The rules are
  applied to generic agents on the assumption that the family transfers to other languages and
  test runners. That is the main thing v2 should test on one of the user's own projects.
- The `claude` CLI is logged in with a claude.ai subscription. `cost_usd` in the receipts is the
  API-equivalent price, not a bill; on a subscription the saving is rate-limit headroom.
- Cells 2 and 3 are one trial per cell, 10 to 21 tasks per family. Anthropic's bar for a production
  cutover is about 50 cases and 5 trials. The find-feature family is past that bar for Haiku; the
  other two are calibrations that all pointed the same way.

## When to re-check, and what to run

- A new model id (`python3 catalog/discover.py`): run the three families for that model only,
  `python3 report.py`, and compare cost per success. Old receipts stay valid.
- A price change: edit `catalog/models.json`. Receipts carry token counts, so the cost columns can
  be recomputed; `report.py` does not do that yet (it reads the CLI's `cost_usd`). That is a v2 item.
- A routed family misbehaving in use: run that family's cell for the tier in use and the next one up.
- A new family measured: add a row here and to `routing.json`, then `apply_agents.py`.

## What v1 does not decide

- Bugs that need a design change rather than a local fix: not measured (cell 3 covered hidden
  helpers, cross-file callees and two-defect tasks).
- Browser flows driven through Chrome MCP: no family yet.
- Code review, architecture, writing: no checker, so no measured family; stays on `inherit`.
- Non-Anthropic models: priced in the catalog, never run.
