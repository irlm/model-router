# Routing v1: which model, at which effort, for which kind of agent work

Decided 2026-10-30 from three families measured on our own tasks (`results/cell1`, `results/cell2`),
revised the same day after cell 3 (harder bugs, `results/cell3`), cell 4 (browser flows,
`results/cell4`), cell 5 (the same browser flows on the user's own store, `results/cell5`),
cell 6 (the code families repeated over two to three trials, `results/cell6`) and cell 7 (the first
non-Anthropic model through its own harness, `results/cell7`), and on 2026-11-01 after cell 8
(a bug-fix family on the user's own TypeScript repo with the effort sweep of Opus and Fable, a web
research family with a citation checker, intervals in the rule, `results/cell8`).
Machine-readable copy: `routing.json`, written by `decide.py` from the receipts; the decision table
at the end of this file is generated the same way. Applied to the agent files with `apply_agents.py`.
This is version 1.1. It covers six families and says "no decision" for the rest.

## Before v1

Every subagent inherited the main conversation's model, Fable 5.1, at effort `xhigh`
(`effortLevel` in `~/.claude/settings.json`). That is the most expensive setting on every axis,
and none of the four measured families needed it.

## The rules

| Family | Default | Step-up | Escalation rule | Evidence (all at effort low) |
|---|---|---|---|---|
| **Find a feature in a huge codebase.** Locate code, callers, struct fields, dispatch targets with search tools. No writes. | `haiku`, `low` | `sonnet`, `low`, when a 1-in-80 wrong answer costs more than 18x the session | None. Misses are confident answers, so there is no failure signal to trigger on. | Haiku 214/216 over 3 trials (98.8%; medium effort 213/216, bought nothing). Sonnet 144/144 over 2 cold trials. Fable 72/72. Cold cost per task $0.0067 / $0.119 / $0.578. OpenAI `gpt-6-luna` through the Codex CLI: 209/216 over 3 trials at $0.0005 per task, below the bar, the same two caller tasks wrong every time (`results/cell7`). |
| **Fix a bug with a failing test.** The test names the failing case; the agent reads and edits. | `haiku`, `low`, **with the test runner in the loop** | None needed | Not needed with the runner: 21/21 at every tier. Without a runner no tier is reliable when there may be more than one defect, and a bigger model fails the same way. | Single-site bugs, no runner: Haiku 29/30 over 3 trials (the miss a confident wrong guess on a bug it had fixed in trial 1), Sonnet 20/20, Fable 20/20 ($0.012 / $0.155 / $0.72 per task). Hard tier, 11 hidden-helper and 10 two-site bugs: with runner Haiku 63/63 over 3 trials, Sonnet 42/42 and Fable 42/42 over 2 ($0.0145 / $0.19 / $0.89 per task); without runner 16 / 14 / 16 of 21, every miss a partial fix that stopped after one defect (`results/cell3`, `results/cell6`). |
| **Write tests for a function.** Success = builds, passes on the real code, fails on a seeded bug. | `haiku`, `low`, **with the test runner in the loop** | None needed | Not needed: with the runner every tier is 10/10 | With runner Haiku 30/30 over 3 trials, Sonnet 20/20 and Fable 20/20 over 2, at $0.026 / $0.28 / $1.57 per task. Without runner 5 / 7 / 4 of 10, cost per success $0.049 / $0.370 / $4.58. Every tier ships wrong expected values when it cannot run (`results/cell2`, `results/cell6`). |
| **Drive a web page through a checklist in a real browser.** Sign in, add, edit, delete, sign out through the Chrome extension tools; judge each numbered item by what is on screen; report pass/fail per item. | `haiku`, `low` | None needed. Retry a flow whose request log shows it did not finish (a browser disconnect); do not step up. | None: Haiku matched Sonnet item for item on both apps. The misses were one lenient reading by Fable, four over-strict readings by Sonnet, and four browser disconnects in 76 store runs, on all three tiers (the shared Chrome was closed by hand); no model missed a planted defect in a flow it finished. | Toy app, 11 flows (10 planted defects plus a clean app, 9 items, truth from a scripted user): Haiku 33/33 over 3 trials, Sonnet 11/11, Fable 10/11; every run drove the whole flow. Cost per flow $0.035 / $0.427 / $2.26; wall 91 s / 76 s / 140 s (`results/cell4`). The author's own Go web store, 15 flows (14 defects plus clean, 10 items): Haiku 30 of 32 runs (2 trials plus reruns), Sonnet 26 of 31, Fable 15 of 16. Every Haiku and Fable miss was the shared browser being closed mid-flow, and every cut flow was rerun correct; among flows that finished Haiku 30/30, Fable 15/15, Sonnet 26/30 (an extra fail on the item next to the defect). Cost per flow $0.038 / $0.48 / $2.55; wall 147 s / 131 s / 222 s (`results/cell5`). |
| **Fix a bug with a failing test in the user's own repo** (a private TypeScript repo with vitest; the transfer check for the row above). | `haiku`, `low`, **with the test runner in the loop** | None needed | Not needed with the runner: 24/24 on every Claude tier at every effort. | 24 single-line mutants the suite catches, one per source file. With runner: Haiku 72/72 over 3 trials ($0.0071 per task), Sonnet 24/24 ($0.097), Opus 5.5 24/24 at low, high and xhigh ($0.18 / $0.19 / $0.23), Fable 5.1 24/24 at low, high and xhigh ($0.48 / $0.56 / $0.73). Without runner Haiku 22/24. A paraphrased prompt: 24/24. `gpt-6-luna` through Codex 20/24, two of its fixes break the type check (`results/cell8`). |
| **Look up a technical fact on the web and cite the page.** Search, read, answer with the URLs actually read. | `haiku`, `low` | None needed | None: every tier finds the fact with a real source. A right answer with no usable source (`right-unsourced`) is the failure to watch; one in 78 Haiku runs. | 18 fact questions plus 8 whose truth is fetched live at grading time (latest versions). Answer by pattern, every cited URL fetched and searched for the evidence. Haiku 76/78 over 3 trials ($0.022 per task), Sonnet 26/26 ($0.062), Opus 5.5 26/26 at low and xhigh ($0.12 / $0.16), Fable 5.1 26/26 at low and xhigh ($0.30 / $0.38). Measures lookup with sources, not synthesis (`results/cell8`). |
| **Everything else** (review, design, writing, research synthesis, exploratory browser testing, data work) | `inherit` (unchanged) | | | No evidence. Not routed. |

Prices are list API prices from `catalog/models.json` (Haiku 5.5 $0.10/$0.50, Sonnet 5.5 $2/$10,
Fable 5.1 $10/$50 per million in/out, Opus 5.5 $4/$20). Opus 5.5 was measured only in cell 8 (the
effort sweep); on the kernel families Sonnet already saturated everything, so it could not change a
decision there.

## Cross-family rules

1. **Effort low first.** Two sweeps now. Haiku on find-feature: medium bought nothing. Opus 5.5 and
   Fable 5.1 on the user's own repo with the test runner: low, high and xhigh all fix 24/24; xhigh
   costs 1.3x (Opus) and 1.5x (Fable) of low and runs 35-50% longer, through more output tokens and
   turns, not better answers (cell 8). No family needed more than low on any tier. This is also the
   setting the main sessions run on (`effortLevel` xhigh), which no agent file changes.
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
   get few, long sessions. The 184 agent files were about 17k of that prefix on every model; since
   2026-11-01 the 179 never called are moved aside (`tools/prune_agents.py`, `results/prefix`:
   40k -> 23k tokens on a trivial call).
   Browser flows are the exception: 40 to 50 tool calls per session, each re-reading the context,
   so cache reads dominate (about $1.50 of Fable's $2.26 per flow). There, tokens per session
   matter as much as the session count. Both point at Haiku. The prefix belongs to the harness,
   not the model: OpenAI's tier at the same list price as Haiku, run through the Codex CLI (about
   31k tokens of prefix, nearly all cached), cost $0.0005 per find-feature task against Haiku's
   $0.0046 through Claude Code (cell 7). For short tasks the harness sets the floor.
5. **Retry before step-up when the run did not finish.** A browser disconnect or a tool failure
   shows in the checker's log (cell 5: `drove` not `full`). That run gets a retry on the same tier;
   a bigger model does not fix a lost browser tab (the four disconnects fell on all three tiers).
6. **The user overrides.** Precedence, from the Claude Code docs: the per-invocation `model`
   on an Agent call, then the agent file's `model`/`effort`, then `CLAUDE_CODE_SUBAGENT_MODEL`,
   then the main conversation's model. Anything above this file wins.

## Where the rules live

- `decide.py`: computes the defaults from the receipts with one rule (the cheapest candidate, by
  cost per success, whose 95% Wilson lower bound is at or above the best lower bound minus 0.02;
  runs the harness lost are retried, not judged; `--rule point` is the v1 rule on the raw rate, and
  the two agree on every family today) and writes `routing.json` plus the decision table at the end
  of this file, with the interval and pass^k per cell. The rows above are prose and must agree with
  it; they did on 2026-11-01. It also lists, per unmeasured catalog model, which families are worth
  running and what that would cost.
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
  | `testing-evidence-collector.md` | browser_flow | haiku / low, plus: drive every checklist step in the browser, judge by what is on screen, report pass/fail per item with evidence; if the browser disconnects, mark the steps that did not run as not_run and say where the flow stopped |
  | `web-researcher.md` (new, 2026-11-01) | web_research | haiku / low, plus: answer from pages read in this session, cite only pages actually opened, say so when none states it. The transcripts' research calls went to the built-in general-purpose agent, which no file can route; this file is the way to route them. |

  The 179 agent files no transcript ever called are in `~/.claude/agents.unused` (`tools/prune_agents.py
  --revert` restores them); `product-manager.md`, the one custom agent ever called, stays as it was.
  `CLAUDE_CODE_SUBAGENT_MODEL` is not set, on purpose: it would downgrade unmeasured families.

## Assumptions to keep in view

- The code evidence was from one C codebase (Linux 6.12) with KUnit as the checker. Cell 8 tested
  the transfer on the user's own TypeScript repo with vitest (a private tree): the
  fix-bug decision held, 72/72 for Haiku at low with the runner, and the bigger models bought nothing
  at any effort. The browser family had the same test in cell 5 on the author's own Go web store. The
  write-tests and find-feature rows are still kernel-only.
- The browser row is three Haiku trials and one Sonnet and Fable trial of 11 toy-app flows, plus
  two trials of 15 flows on the user's store, all with an explicit numbered checklist. The agent file it
  is applied to (`testing-evidence-collector.md`) also asks for Playwright screenshots, visual
  judgement and "a minimum of 3 to 5 issues" per report; none of that was measured. If that agent
  is used for visual review rather than checklist flows, treat it as unmeasured.
- The `claude` CLI is logged in with a claude.ai subscription. `cost_usd` in the receipts is the
  API-equivalent price, not a bill; on a subscription the saving is rate-limit headroom.
- Trials per cell: find-feature three (Haiku) and two (Sonnet); the code families three (Haiku)
  and two (Sonnet, Fable) after cell 6; the toy browser flows three (Haiku); the store flows two
  (Haiku, Sonnet). 10 to 72 tasks per family. Anthropic's bar for a production cutover is about 50
  cases and 5 trials; find-feature is past it for Haiku, the others are not, and every repeat so
  far pointed the same way as the first trial.

## When to re-check, and what to run

- A new model id (`python3 catalog/discover.py`): add its price to the catalog, run
  `python3 decide.py --dry-run` to see which families it is worth running and what that costs (a
  model can only win a family by being cheaper than the default, or by being perfect where the
  default is not), run those families, then `decide.py` and `apply_agents.py`. Old receipts stay valid.
- A price change: edit `catalog/models.json`, run `report.py` and `decide.py`. Receipts carry token
  counts, so nothing is re-run.
- A routed family misbehaving in use: run that family's cell for the tier in use and the next one up.
- A new family measured: add a row here and to `routing.json`, then `apply_agents.py`.
- A Claude Code update, or monthly: `python3 regress.py` runs each decided default on a sample of its
  own tasks and flags a family whose successes are improbable under the decided rate; it records the
  binary's version and the prefix. `tools/ledger.sh` writes what the machine actually ran (subagent
  calls by type, tokens and cost by model) to `ledger/`, so the routing is checked against use.

## What v1 does not decide

- Bugs that need a design change rather than a local fix: not measured (cell 3 covered hidden
  helpers, cross-file callees and two-defect tasks).
- Browser testing without a checklist (exploratory), visual judgement from screenshots, and
  JavaScript-heavy or scrolling pages: not measured. Cells 4 and 5 covered checklist flows on
  server-rendered apps (a toy and the user's store), read as text.
- Code review, architecture, writing, research synthesis: no checker, so no measured family; stays
  on `inherit`. Web research is measured only as lookup with sources (cell 8).
- Effort on tasks the models do not already solve: every runner cell is at the ceiling, so cell 8
  shows xhigh buying nothing there, not that it never does.
- Non-Anthropic models: one measured. OpenAI's `gpt-6-luna` through the Codex CLI on find-feature,
  209/216 over three trials at a tenth of Haiku's cost per task, below the bar on the same two caller
  tasks every time (`results/cell7`). The dearer OpenAI tiers and Opus cannot change a decision under
  the rule, so they were not run. A non-Anthropic winner could not be applied to Claude Code agent
  files anyway; `routing.json` would record it and the files would get the best Anthropic candidate.

## Decision table

<!-- decide:start -->
_Generated by `python3 decide.py` (margin 0.02, min trials 1, rule lower, catalog prices). Rate = successes over judged runs; runs the harness lost are retried, not judged. CI = 95% Wilson interval of the rate; with rule `lower` the bar is the best lower bound minus the margin, so thin evidence cannot win. pass^k = chance that all k trials of a task succeed, k = trials per task._

| Family | Default | Needs | Rate (judged runs) | 95% CI | pass^k | Cost per success | Step-up | Bar (lower) | Candidates |
|---|---|---|---|---|---|---|---|---|---|
| find_feature | **haiku**, low | - | 214/216 = 0.991 | 0.97-1.00 | pass^3 0.97 | $0.0046 | sonnet low ($0.117) | 0.954 | fable low 72/72 (1.000, CI 0.95-1.00) $0.5779 8 s; haiku low 214/216 (0.991, CI 0.97-1.00, pass^3 0.97) $0.0046 6 s; haiku medium 213/216 (0.986, CI 0.96-1.00, pass^3 0.96) $0.0057 7 s; sonnet low 144/144 (1.000, CI 0.97-1.00, pass^2 1.00) $0.1173 6 s; gpt-6-luna low 209/216 (0.968, CI 0.93-0.98, pass^3 0.96) $0.0005 4 s |
| fix_bug | **haiku**, low | the test runner in the loop (KUnit) | 63/63 = 1.000 | 0.94-1.00 | pass^3 1.00 | $0.0145 | none | 0.923 | fable low 16/21 (0.762, CI 0.55-0.89) $1.1270 31 s; fable low+kunit 42/42 (1.000, CI 0.92-1.00, pass^2 1.00) $0.8948 46 s; haiku low 16/21 (0.762, CI 0.55-0.89) $0.0158 27 s; haiku low+kunit 63/63 (1.000, CI 0.94-1.00, pass^3 1.00) $0.0145 41 s; sonnet low 14/21 (0.667, CI 0.45-0.83) $0.2564 22 s; sonnet low+kunit 42/42 (1.000, CI 0.92-1.00, pass^2 1.00) $0.1902 34 s |
| write_tests | **haiku**, low | the test runner in the loop (KUnit) | 30/30 = 1.000 | 0.89-1.00 | pass^3 1.00 | $0.0259 | none | 0.866 | fable low 4/10 (0.400, CI 0.17-0.69) $4.5774 168 s; fable low+kunit 20/20 (1.000, CI 0.84-1.00, pass^2 1.00) $1.5736 149 s; haiku low 5/10 (0.500, CI 0.24-0.76) $0.0490 93 s; haiku low+kunit 30/30 (1.000, CI 0.89-1.00, pass^3 1.00) $0.0259 99 s; sonnet low 7/10 (0.700, CI 0.40-0.89) $0.3705 50 s; sonnet low+kunit 20/20 (1.000, CI 0.84-1.00, pass^2 1.00) $0.2792 66 s |
| browser_flow | **haiku**, low | - | 63/63 = 1.000 | 0.94-1.00 | pass^2 1.00 | $0.0367 | none | 0.923 | fable low 25/26 (0.962, CI 0.81-0.99) $2.6294 189 s, 1 lost to the harness; haiku low 63/63 (1.000, CI 0.94-1.00, pass^2 1.00) $0.0367 116 s, 2 lost to the harness; sonnet low 37/41 (0.902, CI 0.77-0.96) $0.5278 118 s, 1 lost to the harness |
| repo_fix | **haiku**, low | the test runner in the loop (vitest) | 72/72 = 1.000 | 0.95-1.00 | pass^3 1.00 | $0.0071 | none | 0.929 | fable high+vitest 24/24 (1.000, CI 0.86-1.00) $0.5560 70 s; fable low+vitest 24/24 (1.000, CI 0.86-1.00) $0.4806 63 s; fable xhigh+vitest 24/24 (1.000, CI 0.86-1.00) $0.7288 94 s; haiku low 22/24 (0.917, CI 0.74-0.98) $0.0077 16 s; haiku low+vitest 72/72 (1.000, CI 0.95-1.00, pass^3 1.00) $0.0071 42 s; opus high+vitest 24/24 (1.000, CI 0.86-1.00) $0.1890 44 s; opus low+vitest 24/24 (1.000, CI 0.86-1.00) $0.1783 50 s; opus xhigh+vitest 24/24 (1.000, CI 0.86-1.00) $0.2306 67 s; sonnet low+vitest 24/24 (1.000, CI 0.86-1.00) $0.0966 53 s; gpt-6-luna low+vitest 20/24 (0.833, CI 0.64-0.93) $0.0063 27 s |
| web_research | **haiku**, low | - | 76/78 = 0.974 | 0.91-0.99 | pass^3 0.92 | $0.0219 | none | 0.891 | fable low 26/26 (1.000, CI 0.87-1.00) $0.3034 17 s; fable xhigh 26/26 (1.000, CI 0.87-1.00) $0.3791 27 s; haiku low 76/78 (0.974, CI 0.91-0.99, pass^3 0.92) $0.0219 17 s; opus low 26/26 (1.000, CI 0.87-1.00) $0.1205 13 s; opus xhigh 26/26 (1.000, CI 0.87-1.00) $0.1601 25 s; sonnet low 26/26 (1.000, CI 0.87-1.00) $0.0620 12 s |
<!-- decide:end -->
