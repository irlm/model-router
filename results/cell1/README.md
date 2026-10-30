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

## Next iterations (cheap, running)

1. Haiku low, trials 2 and 3: variance.
2. Haiku medium, trial 1: the effort lever on the cheapest model.
3. Prefix test: one trivial call with and without the 184 agent files, to size the per-session
   cache write that dominates every bill.
