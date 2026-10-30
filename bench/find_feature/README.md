# kernel_probe — K1: hallucination vs context on a 40M-line codebase

Tests whether context discipline moves a model from fabricating to
correct on the Linux kernel — a codebase no model can hold, so every
ungrounded answer is a guess. Stdlib + ripgrep only.

## Ground truth (oracle.py)

Every fact is string-verifiable against a pinned tree (Linux v6.12):

- **real function** — definition line extracted from a .c file;
  **bait** — a mutated name with ZERO whole-word occurrences anywhere
  in the tree (any mention disqualifies it at generation time).
- **struct fields** — only structs whose entire body our parser
  understands (no preprocessor lines, no nesting); anything else is
  rejected rather than half-parsed.
- **references** — small files verifiably containing `name(`;
  **clean negatives** — same-directory files with zero occurrences of
  the name at all.

## Tasks (tasks.py)

Deterministic from a seed: 12 real + 12 bait existence questions,
12 struct-field questions, 12 which-files-reference questions, each
with fixed context regions. `python3 tasks.py --tree <kernel-dir>`.

## Arms (run_probe.py)

- **Z** — no source. Honest answer for most tasks is "unknown".
- **B** — the task's minimal relevant source regions.
- **A** — B plus deterministic noise files to ~3x the context
  (capped 70k chars so every prompt fits agent-CLI argv limits):
  does irrelevant bulk degrade grounded answers?

Endpoints: `ollama` (local HTTP), `claude` (CLI), `codex` (CLI).
Resumable: completed task ids in the output JSONL are skipped.

```
python3 run_probe.py --endpoint ollama --model qwen2.5-coder:7b --arm Z
```

## Grading (grade.py)

Per answer: `correct | wrong | abstained | hallucination |
unparseable`. **Hallucination is reserved for confident fabrication**
(bait claimed to exist, invented struct field, naming a verified-clean
file). Missing true items is `wrong` — incompleteness is a different
failure from fabrication, and the distinction is the point of K1.

## Tests

`python3 tests/test_kernel_probe.py` — 8 tests over a synthetic mini
tree (definition vs declaration, bait absence, struct parser
accept/reject, refs/negatives, all grading edge cases).

Results: ../../results/kernel-probe/RESULTS.md
