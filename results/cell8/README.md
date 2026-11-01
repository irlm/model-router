# Cell 8 (2026-11-01): the user's own repo, the effort axis, web research, and the prefix

Everything GAPS.md listed as missing on our side, done in one day and measured. Tables: `tables.md`
(from `report.py`, catalog prices). Receipts: `runs/repo_fix`, `runs/repo_fix_pb`, `runs/web_research`.

## 1. The agent files were 17k tokens of every request

179 of the 184 files in `~/.claude/agents` had never been called in any transcript. `tools/prune_agents.py`
moved them aside (reversible). A trivial Haiku call went from 38.8k-40.7k input tokens to 22.7k-24.6k on
the same Claude Code version (`results/prefix`). That is paid on every turn of every session.

## 2. Bug fix on the user's own TypeScript repo: the runner matters, the model and the effort do not

`bench/repo_fix` on a private TypeScript repository of the author's (9k lines, 343 vitest tests, so not in
any training set). `make_tasks.py` mutated one source line at a time (105 tries, 48 caught by the suite),
24 tasks spread one per source file, 1 to 14 failing tests each. The agent gets the failing output and
the test command; the grader reruns the suite on the patched tree.

| Cell | Fixed | Cost per success | Turns | Wall |
|---|---|---|---|---|
| Haiku low, runner, 3 trials | 72/72 | $0.0071 | 7.4 | 42 s |
| Sonnet low, runner | 24/24 | $0.097 | 7.7 | 53 s |
| Opus 5.5 low, runner | 24/24 | $0.178 | 6.8 | 50 s |
| Opus 5.5 high, runner | 24/24 | $0.189 | 6.3 | 44 s |
| Opus 5.5 xhigh, runner | 24/24 | $0.231 | 8.1 | 67 s |
| Fable 5.1 low, runner | 24/24 | $0.481 | 7.6 | 63 s |
| Fable 5.1 high, runner | 24/24 | $0.556 | 7.8 | 70 s |
| Fable 5.1 xhigh, runner | 24/24 | $0.729 | 9.9 | 94 s |
| Haiku low, no runner | 22/24 | $0.0077 | 6.1 | 16 s |
| gpt-6-luna low, runner (Codex) | 20/24 | $0.0063 | 13.6 | 27 s |
| Haiku low, runner, paraphrased prompt | 24/24 | $0.0080 | 8.0 | 58 s |

What it says:

- **The effort axis buys nothing here and costs 30-50%.** Opus and Fable fix every task at every
  effort; xhigh is 1.3x (Opus) and 1.5x (Fable) the cost of low and 35-50% slower, through more
  output tokens and more turns (Fable 1,260 output tokens at low, 2,508 at xhigh), not better answers.
  This is the lever the main sessions run on (effortLevel xhigh in settings.json).
- **The transfer assumption held.** Haiku at low with the runner, the routing v1 default decided on
  Linux and KUnit, is 72/72 on the user's TypeScript repo with vitest, at 1/25 of Opus and 1/70 of
  Fable per task.
- **The runner finding transferred too, smaller.** Without the runner Haiku is 22/24 (one wrong fix,
  one gave up); on the kernel's hard tier it was 16/21. These are single-line bugs with a pointed
  failing test, so there is less to get wrong.
- **Wording:** the paraphrased prompt (`--prompt-variant b`) changed nothing in the result and 10% in
  cost. The kernel cell 7 effect was on a harder prompt.
- **Codex / gpt-6-luna:** 20/24 with the runner, and two of its "fixes" pass the tests but break the
  type check (`tsc`): it edits around the symptom. Cheapest per success on paper, below the bar.
- **Type check:** three Haiku runs on task 02 pass the suite but fail `tsc` (the grader records it).
  The suite is the truth the family is defined on; a type-clean requirement would be a stricter tier.

## 3. Web research: every model finds the fact with a real source; Haiku costs 1/17 of Fable xhigh

`bench/web_research`: 18 fact questions (PostgreSQL and DuckDB defaults and limits, RFC numbers,
Docker, Kubernetes, AWS) plus 8 live questions whose truth is fetched at grading time (latest
PostgreSQL, kernel, Node LTS, Go, Rust, DuckDB, vitest, Python). The grader checks the answer by
pattern, then fetches every cited URL and looks for the evidence in its text. No judge model.

| Cell | Correct | Cost per success | Wall |
|---|---|---|---|
| Haiku low, 3 trials | 76/78 | $0.022 | 17 s |
| Sonnet low | 26/26 | $0.062 | 12 s |
| Opus 5.5 low | 26/26 | $0.121 | 13 s |
| Opus 5.5 xhigh | 26/26 | $0.160 | 25 s |
| Fable 5.1 low | 26/26 | $0.303 | 17 s |
| Fable 5.1 xhigh | 26/26 | $0.379 | 27 s |

Haiku's two misses: one right answer with no source listed (`right-unsourced`), one vague version
("v26.x" for the Node LTS). No model answered a live question from memory: with the web tools in hand,
the current version came back every time. The user's research subagents run today on the session
model at xhigh, i.e. the last row.

The family measures lookup with sources, which is what the transcripts' general-purpose calls mostly
were. It does not measure synthesis or report writing; that needs a rubric grader calibrated by a
human read, which is still open.

**Pricing fix found here:** the web tools fetch pages through a second model and bill that content as
uncached input that Claude Code's summed `usage` block leaves out, so the catalog price of a Haiku
research task was 5x too low. Receipts now keep the per-model `modelUsage` block and `catalog/price.py`
prices from it (plus $0.01 per web search); the receipts from before that change are priced by the
CLI's own figure. On every non-web receipt the two agree to the cent.

## 4. Grading under load is not grading

The first grading pass ran while six agent sessions were running vitest on the same machine. vitest's
default 5 s test timeout failed one DOM test and one CLI test at random, and 28 fixes were marked
"still failing" (a hand re-run of one Opus patch: 343/343). The grader now runs with 120 s timeouts,
re-runs a failing suite once and needs the failure to repeat, and it never shares a worktree with a
runner. All 28 came back fixed. The task set itself was re-checked with long timeouts: every recorded
failing test reproduces.

## 5. The decision

`decide.py` now scores a candidate by the lower bound of the 95% Wilson interval (`--rule lower`),
so thin evidence cannot win a family; no family flipped. New rows: repo_fix = Haiku low with the test
runner ($0.0071, 72/72, pass^3 1.00); web_research = Haiku low ($0.022, 76/78, pass^3 0.92). Applied: a
new agent file `~/.claude/agents/web-researcher.md` (model haiku, effort low), since the research calls
in the transcripts went to the built-in general-purpose agent, which no file can route. The
minimal-change engineer stays on fix_bug (Haiku low with the runner), now confirmed on the user's own
repo.

What this cell does not settle: whether effort matters on tasks these models do not already solve
(every runner cell is at the ceiling), and research beyond lookup.

## Cost of this cell

About $75 catalog-equivalent for the repo_fix sweep (Fable $42, Opus $14, Sonnet $2, Haiku $1, Codex
$0.13 token-only), $28 for research. Haiku's repeat trials and the paraphrase together cost under $1.
