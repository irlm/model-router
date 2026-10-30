# Cell 2: bug-fix and write-tests families, Claude models at low effort (2026-10-30)

One trial per cell, 10 tasks per family, agent with tools inside its own git worktree of the pinned
Linux v6.12 tree. Every grade is a real UML kernel build plus the kernel's own KUnit run; no judge
model. Receipts: `runs/fix_bug/`, `runs/write_tests/`; grades: `grades.json` next to them; tables:
`tables.md`.

## Family: fix a seeded kernel bug (suite name and failing output only, no test runs)

| Model | Effort | Fixed / 10 | Cost per task | Turns mean | Wall mean |
|---|---|---|---|---|---|
| claude-haiku-5-5 | low | 10 | $0.012 | 5.9 | 28 s |
| claude-sonnet-5-5 | low | 10 | $0.149 | 4.6 | 12 s |
| claude-fable-5-1 | low | 10 | $0.748 | 4.7 | 26 s |

Saturated. Every model found the function from the failing test, read it, and fixed the single-site
bug without being able to run anything. Haiku needed about one more turn. The family cannot rank
models until it has harder bugs (multi-site, cross-file, no test naming the function).

## Family: write a KUnit suite for a kernel function

Two variants. `noexec`: the agent cannot build or run. `kunit`: the agent may run exactly
`python3 tools/testing/kunit/kunit.py ...` against its own build directory and is told a suite that
fails on the current code is worthless. Success means the suite builds, passes on the real code,
and fails on the hidden seeded bug.

| Model | Variant | Success / 10 | Other outcomes | Cost per success | Cost per task | Turns mean | Wall mean |
|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | noexec | 5 | 4 wrong expectations, 1 compile fail | $0.049 | $0.025 | 7.0 | 94 s |
| claude-sonnet-5-5 | noexec | 7 | 2 wrong expectations, 1 compile fail | $0.370 | $0.259 | 6.4 | 50 s |
| claude-fable-5-1 | noexec | 4 | 5 wrong expectations, 1 compile fail | $4.58 | $1.83 | 10.9 | 168 s |
| claude-haiku-5-5 | kunit | 10 | | $0.025 | $0.025 | 11.0 | 91 s |
| claude-sonnet-5-5 | kunit | 10 | | $0.287 | $0.287 | 9.4 | 66 s |
| claude-fable-5-1 | kunit | 10 | | $1.51 | $1.51 | 8.9 | 134 s |

"Wrong expectations" is `fails-on-correct-code`: a suite of 11 to 41 cases with 1 or 2 wrong
expected values. In 10 of those 11 suites the remaining cases still caught the seeded bug
(`detects=True` in the grades), so the test design was fine and the arithmetic was off. The one
compile failure per model is the same mistake on `get_option`: a KUnit assertion macro misuse that
gives "invalid initializer" in `include/kunit/test.h`.

## Reading

1. **The checker in the loop is worth more than the model.** Haiku with KUnit: 10 of 10 at $0.025
   per success. Fable without it: 4 of 10 at $4.58 per success. That is a 180x cost gap in the
   cheap model's favour, with a better result.
2. **Not a small-model weakness.** Without the checker, Fable did worst. It writes the largest suites
   (16 KB, up to 41 cases) and each extra expectation is one more chance to be wrong.
3. **The checker does not raise cost per task.** It adds 2 to 4 turns, but the final suites are
   smaller and the models stop re-reading; Fable's cost per task fell from $1.83 to $1.51.
4. **Escalation is measurable here, and it is not needed.** With the checker every tier is at 10/10,
   so the cheapest tier wins outright. The "run cheap, escalate on failure" rule is only worth
   measuring where the cheap model plus checker still fails; this family has not shown such a case.
5. **Fixed overhead still dominates short sessions.** Cache reads per session: 200k to 540k tokens;
   cache writes about 40k to 53k. See `../cell1/PREFIX.md`.

## What this cell would say, if it were the decision (it is not yet)

- Family "fix a bug with a failing test": `claude-haiku-5-5` at low effort, no evidence yet that
  anything more is needed. Re-check with harder bugs before trusting it.
- Family "write tests": any model, provided the agent can run the tests. Default
  `claude-haiku-5-5` at low effort with the test runner available; without a runner, do not use
  any model for this, because every one of them ships wrong expectations.
- Cross-family: give agents a checker before giving them a bigger model.

## Limits

- One trial per cell, ten tasks per family. Same-task repeats would show variance; same-day repeats
  are cache-warm and not comparable on cost.
- All cells at low effort. An effort sweep on the `noexec` variant was not run because the `kunit`
  variant already dominates it at every tier.
- Bash was restricted to the kunit command; a real agent would have `make`, `git` and more.
- The Fable `noexec` arm hit the 30-turn cap once (max turns 31 includes the final reply).
