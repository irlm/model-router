# Cell 6: repeat trials of the code families (2026-10-30)

Cells 2 and 3 decided the two code families on one trial each. This cell repeats them: trial 2 for
all three models, trial 3 for Haiku (the routed tier). Same tasks, same prompts, same checkers
(a real KUnit build and run per receipt), same worktrees per model. Three families:

- **Easy bug fixes** (`bench/fix_bug`, 10 single-site bugs, the failing test names the function,
  no runner for the agent).
- **Hard bug fixes with the runner** (`bench/fix_bug` hard tier, 21 tasks: 11 hidden helpers, 10
  two-site bugs; the agent may run the paired KUnit suite).
- **Write tests with the runner** (`bench/write_tests`, 10 functions; success = the suite builds,
  passes on the real code and fails on the seeded bug; the agent may run its suite).

Receipts: `runs/fix_bug`, `runs/fix_bug_hard`, `runs/write_tests` (`-t2`, `-t3`); grades:
`grades.json`; tables: `tables.md`. Costs are catalog prices from the receipts' token counts.

## Result

Per trial: correct / n, cost per success, mean wall time per task.

| Family | Model | Trial 1 | Trial 2 | Trial 3 | All trials |
|---|---|---|---|---|---|
| Easy bug fixes, no runner | Haiku | 10/10, $0.012, 28 s | 9/10, $0.013, 23 s | 10/10, $0.011, 20 s | 29/30 |
| | Sonnet | 10/10, $0.149, 12 s | 10/10, $0.160, 16 s | | 20/20 |
| | Fable | 10/10, $0.748, 26 s | 10/10, $0.702, 17 s | | 20/20 |
| Hard bug fixes, with runner | Haiku | 21/21, $0.014, 47 s | 21/21, $0.014, 37 s | 21/21, $0.015, 38 s | 63/63 |
| | Sonnet | 21/21, $0.197, 40 s | 21/21, $0.183, 27 s | | 42/42 |
| | Fable | 21/21, $0.885, 48 s | 21/21, $0.905, 44 s | | 42/42 |
| Write tests, with runner | Haiku | 10/10, $0.025, 91 s | 10/10, $0.025, 102 s | 10/10, $0.027, 103 s | 30/30 |
| | Sonnet | 10/10, $0.287, 66 s | 10/10, $0.272, 67 s | | 20/20 |
| | Fable | 10/10, $1.508, 134 s | 10/10, $1.640, 165 s | | 20/20 |

The no-runner arms of the hard tier and of write-tests were not repeated: cell 2 and cell 3 showed
them failing on every tier (16 / 14 / 16 of 21 hard bugs, 5 / 7 / 4 of 10 test suites), and the
routing requires the runner.

## The one miss

Haiku, easy tier, trial 2, `string_unescape`: the seeded bug flips `!=` to `==` in the escape
check. In trial 1 Haiku made the one-character fix and wrote that it could not build. In trial 2
it made a different, plausible change (a `break` after the stray backslash) and wrote a confident
summary; the test still fails. Same bug, same model, no way to check, two different answers. This
is the no-runner failure mode from cell 3 showing up on an easy bug. Sonnet and Fable fixed it
both times.

## Reading

1. **With the runner, the saturation holds across trials.** Hard bugs: 42/42 for Sonnet and
   Fable, 63/63 for Haiku. Write-tests: 20/20 for Sonnet and Fable, 30/30 for
   Haiku. Cost per success moved by under 10% between trials on every tier.
2. **The runner matters even on easy bugs.** Haiku without it is 29/30 on the easy tier
   over three trials; the miss is a confident wrong guess. Sonnet and Fable are 20/20 at 12x and
   60x the cost. The cheaper way to close that gap is the runner, not the bigger model: with it,
   Haiku is clean on the harder tier.
3. **Routing decision: unchanged.** Fix-bug and write-tests stay on Haiku at effort low with the
   test runner in the loop. `decide.py` reaches the same answer from the receipts.

## Limits

- 10 to 21 tasks per family, two to three trials. Anthropic's bar for a production cutover is
  about 50 cases and 5 trials.
- One C codebase (Linux 6.12) and one test framework (KUnit). Transfer to other languages and
  runners is the open assumption in ROUTING.md; the browser family has had that test (cell 5),
  the code families have not.
- Trial 2 and 3 sessions ran on the same day as trial 1, so prompt caches were partly warm;
  per-task cost is a little lower than a cold run on the long-context tasks.
