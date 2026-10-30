# Cell 3: harder bug fixing, with and without a test runner (2026-10-30)

One trial, 21 tasks, three models at low effort, two arms. Every grade is a real UML kernel build
plus the kernel's own KUnit run; no judge model. Receipts: `runs/fix_bug_hard/`; grades and the
per-site analysis: `grades.json`, `sites.json` next to them; tables: `tables.md`.

## The tasks (`bench/fix_bug/tasks-hard.json`, made by `make_hard_tasks.py`)

- **Hidden helper (11):** one operator mutation in a function that no test case names: a static
  helper in the same file (`get_range`, `unescape_octal`, `unescape_hex`, `escape_*`) or a callee
  in another file (`_parse_integer_limit`, `_parse_integer_fixup_radix` in `lib/kstrtox.c`, reached
  from the `cmdline` suite). The failing output points at a function that is correct.
- **Two-site (10):** two verified single-site mutations in two different functions covered by the
  same suite. Fixing one leaves the suite failing.
- Every task was kept only if the tree compiled and booted, the suite reported `[FAILED]`, and
  the restored tree passed. Candidates that combined the `memparse` mutation with another produced
  no KTAP output at all (the kernel did not get far enough to run tests) and were discarded.
- The prompt gives the suite name and the real failing output, and does not say how many defects
  there are. The `no runs` arm has Read/Glob/Grep/Edit. The `runner` arm may also run exactly
  `python3 tools/testing/kunit/kunit.py ...` against its own build directory.

## Result

| Model | Arm | Hidden fixed / 11 | Two-site fixed / 10 | All / 21 | Cost per task | Cost per success | Turns | Wall |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | no runs | 11 | 5 | 16 | $0.012 | $0.016 | 6.4 | 27 s |
| claude-sonnet-5-5 | no runs | 11 | 3 | 14 | $0.171 | $0.256 | 6.5 | 22 s |
| claude-fable-5-1 | no runs | 11 | 5 | 16 | $0.859 | $1.127 | 6.3 | 31 s |
| claude-haiku-5-5 | runner | 11 | 10 | 21 | $0.014 | $0.014 | 9.2 | 47 s |
| claude-sonnet-5-5 | runner | 11 | 10 | 21 | $0.197 | $0.197 | 9.9 | 40 s |
| claude-fable-5-1 | runner | 11 | 10 | 21 | $0.885 | $0.885 | 8.0 | 48 s |

For comparison, the single-site tier (cell 2, no runs): 10/10 on every tier at $0.012 / $0.149 / $0.748.

## What the misses were

All 17 misses are two-site tasks, and every one of them is a partial fix: the agent restored one of
the two functions and stopped (`sites.json`: no receipt left both sites broken; Haiku's one
textually-unrestored site on `get_option+get_options` was an equivalent rewrite and the suite passed).
None abstained; every miss returned a patch and a summary describing it as the fix. The site left
behind was most often the second-hop or cross-file one (`_parse_integer_*` in `lib/kstrtox.c`,
`strcspn`, `string_escape_mem`), but Sonnet also left the first-hop `get_option` twice.

## Reading

1. **A bigger model does not fix the "fixed one, declared done" habit.** Without a runner Fable
   and Haiku tie at 16/21 and Sonnet is below both at 14/21. The misses are a stopping decision,
   not a capability gap: the same tiers that solved every cross-file hidden-helper bug stopped
   after one site on the two-site bugs.
2. **The runner fixes it at every tier.** 21/21 for Haiku, Sonnet and Fable. It costs about three
   more turns and 10 to 15% more per task. Haiku with the runner, $0.014 per success, against Fable
   without it, $1.127 per success: 80x, with a better result.
3. **Hidden helpers and cross-file callees do not separate the tiers.** All 11 solved by every
   model in both arms. One or two hops from the failing test is well within every tier's reach.
4. **The escalation rule is moot for this family.** With the runner, Haiku does not fail, so there
   is nothing to escalate. Without the runner, Sonnet fails the same way Haiku does, so escalating
   would not help either.
5. **The cheap tier plus a checker wins outright again.** This is the second family (after
   write-tests) where it holds, and the first where the bigger model's failure count equals the
   small model's.

## What this changes in `ROUTING.md`

The fix-bug family moves from provisional to decided: `haiku` at `low`, with the agent able to run
the tests before it finishes. Without a runner, no tier is reliable when there may be more than
one defect, so the rule for that case is "give it the runner", not "give it a bigger model".

## Limits

- One trial, 21 tasks. Same-task repeats would show variance; same-day repeats are cache-warm.
- All at low effort. An effort sweep on the `no runs` arm was not run because the `runner` arm
  dominates it at every tier for about 10% more cost.
- Mutations are operator flips in `lib/`. Bugs that need a design change were not measured.
- The failing output of a two-site task lists failing cases from both sites. That hint did not
  make the agents look for a second defect.
