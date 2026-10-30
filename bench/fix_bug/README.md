# Family: fix a bug in a large unfamiliar codebase (agent with tools)

Ten verified single-site bugs seeded into `lib/string.c`, `lib/string_helpers.c`, `lib/cmdline.c`
and `lib/siphash.c` of the pinned Linux v6.12 tree. Each mutation is kept only if it compiles, makes
its paired KUnit suite fail, and the restored file passes again (the earlier K2 evaluation, see
`k2-reference/`). `tasks.json` is that task set; `original_function` is oracle-only.

## Agent arm (`run_agent.py`)

- The model's own git worktree of the tree, with the bug seeded and committed, so `git` looks clean.
- Prompt: the suite name and the real failing KUnit output. Not the function, not the file.
- Tools: Read, Glob, Grep, Edit. No Bash: the agent cannot build or run the tests.
- Rule: do not touch test code. Reply with the changed files as JSON, or `{"unknown": true}`.
- Receipt: the agent's patch (`git diff`), changed files, usage, cost, turns, wall time.

## Grader (`grade.py`)

In the `grade-fix` worktree: seed the same mutation, `git apply` the agent's patch, build and run the
paired suite under UML with `kunitconfig`. Outcomes: `fixed`, `still-failing`,
`compile-or-boot-fail`, `touched-tests`, `no-change`, `abstained`, `operational`.
Grades are cached in `runs/fix_bug/grades.json`.

## Known limits

- Single-operator bugs with the failing test pointing at the function: every frontier model fixes
  them at low effort. The family does not separate models yet; harder bugs (multi-site, cross-file,
  no test naming the function) are the next step.
- One grade worktree, so grading is sequential.
