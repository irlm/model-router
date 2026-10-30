# Cell 1: find-feature family, Claude models at low effort (2026-10-29)

One trial. 72 tasks (48 lexical with string-verified truth, 24 semantic with hand-classified truth)
run as an agent with Read/Glob/Grep inside the pinned Linux v6.12 tree, web off, 15-turn cap.
Receipts: `runs/runs-<model>-low-t1.jsonl`. Tables: `tables.md`, `grades.json`.

## Result

| Model | Effort | correct / 72 | API-equiv cost total | cost per correct task | turns mean | wall mean |
|---|---|---|---|---|---|---|
| claude-haiku-5-5 | low | 70 | $0.47 | $0.0067 | 2.8 | 6.2 s |
| claude-sonnet-5-5 | low | 72 | $8.58 | $0.119 | 2.4 | 6.0 s |
| claude-fable-5-1 | low | 72 | $41.61 | $0.578 | 2.5 | 8.3 s |

Zero hallucinations, zero abstentions, zero operational errors in 216 calls. Haiku's two misses:

- `fields-06`: wrong field list for a struct (grounded wrong, not fabrication).
- `callers-10`: named `lib/string_helpers.c` as a caller when it holds only the definition
  (the lexical-confusion case the semantic family exists to catch).

## What drives the cost

Mean tokens per call, every model: cache write about 27,500, cache read about 68,000, fresh input
under 40, output about 220 (Haiku 500, it thinks more at low effort).
The task itself is a few hundred tokens. The rest is the fixed Claude Code prefix (system prompt,
tool schemas, the 184 user agent definitions, skills), of which about 27,500 tokens are re-written
to cache on every new session at the 1-hour rate (2x input price). On Fable that write alone is
about $0.55 of the $0.58 per call. Model choice changes the price of that overhead, not the task.

## What this cell decides, and what it does not

- For this family, Sonnet and Fable at low effort are saturated: 72/72 both. Fable buys nothing
  here at 4.9x Sonnet's cost. Haiku at low effort misses 2.8% at 1/18 of Sonnet's cost.
- There is no cheap failure signal in a lookup task: Haiku's misses were confident answers, not
  "unknown". So "run cheap, escalate on failure" cannot be applied to this family. Escalation
  needs a checker (tests, compile), which the test-writing and bug-fix families will have.
- One trial per cell. Whether Haiku's 70/72 is a stable 97% or noise around 100% is unknown; the
  earlier run of Haiku, in the author's previous evaluation repository, at medium effort scored 72/72 on the same tasks.

## Iterations (2026-10-29 and 2026-10-30)

| Model | Effort | Trials | Correct | Cold cost per task | Note |
|---|---|---|---|---|---|
| claude-haiku-5-5 | low | 3 | 214 of 216 | $0.0067 | misses: fields-06, callers-10 (trial 1 only) |
| claude-haiku-5-5 | medium | 3 | 213 of 216 | $0.0065 | misses: refs-05, refs-10 (trial 2), fields-06 (trial 3) |
| claude-sonnet-5-5 | low | 2 | 144 of 144 | $0.119 and $0.115 | trial 2 ran the next day, cache cold again |
| claude-fable-5-1 | low | 1 | 72 of 72 | $0.578 | |

- Haiku lands at 98.8% over 432 calls at either effort; medium effort did not help it. The misses are
  scattered, except `fields-06`, which it missed twice in six trials.
- Sonnet is 144 of 144 over two cold trials; its cost per task is stable across days.
- Repeat trials run on the same day reuse the prompt cache written by trial 1 (identical conversations
  read everything, see `PREFIX.md`), so same-day repeat costs are lower and not comparable.
- Prefix test: see `PREFIX.md`. About 95k tokens of fixed prefix per new session on every model,
  27k of it written at the 1-hour cache rate; the 184 agent files are about 17k of it.

## What this cell would say, if it were the decision (it is not yet)

Family "find a feature in a huge codebase, agent with search tools":

- Default: `claude-haiku-5-5` at low effort, 98.8% over 432 calls, about 1/18 of Sonnet's cost per
  session and 1/86 of Fable's. Medium effort buys nothing here.
- Step-up when a 1-in-80 miss is expensive: `claude-sonnet-5-5` at low effort, 144 of 144 over two
  cold trials. Fable bought nothing on this family at 4.9x Sonnet's cost.
- No escalation rule: lookup answers carry no failure signal (misses were confident, not "unknown").
- Still open before deciding: the family is saturated for Sonnet and Fable, so it cannot rank them. Harder families with a checker (write tests,
  fix bugs, browser flows) are where the models will separate and where escalation can be measured.
