# Family: write tests for a kernel function (agent with tools)

Same ten functions as `fix_bug`. The agent must write a KUnit suite for one function into
`lib/agent_kunit.c`, which `wiring.py` has already added to `lib/Makefile` and `lib/Kconfig.debug`
as `CONFIG_AGENT_KUNIT_TEST`. The task's hidden bug is the K2 mutation of that function
(`mutated_function` in `tasks.json`, never shown to the agent).

## Two variants (`run_agent.py`)

- `noexec` (default): Read, Glob, Grep, Edit, Write. The agent cannot build or run anything.
- `--kunit`: the same plus Bash restricted to `python3 tools/testing/kunit/kunit.py ...`, an
  `agent.kunitconfig` in the worktree, and a per-model build directory outside the tree. The prompt
  gives the exact command and says a suite that fails on the current code is worthless.
  Receipts carry `variant` and the file name gets `-kunit`.

## Grader (`grade.py`)

In the `grade-tests` worktree, with the wiring applied and the agent's file in place:

1. Build and run on the pristine function. The suite must build and every case must pass.
2. Seed the hidden mutation and run again. The suite must now fail.

Outcomes: `catches-bug` (deliverable and finds the bug), `misses-bug` (passes on both),
`fails-on-correct-code` (wrong expectations; detail records whether it would still detect the bug),
`compile-fail`, `empty-suite`, `touched-other-files`, `abstained`, `operational`.
Totals come from kunit.py's "Testing complete. Ran N tests" line.
Grades are cached in `runs/write_tests/grades.json`, keyed by model, effort+variant, trial, task.

## Why this family matters

It is the first with a checker the agent could use. Without it, every model ships suites with a
few wrong expectations. With it, the question becomes whether a cheap model plus the checker reaches
the expensive model without it, which is the escalation question the routing strategy needs.
