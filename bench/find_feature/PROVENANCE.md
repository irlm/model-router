# Provenance

Copied verbatim from the author's earlier evaluation repository (2026-10-10):

- `run_probe.py`, `run_retrieval.py`, `grade.py`, `grade_semantic.py`, `mech_packet.py`, `oracle.py`, `tasks.py`, `gen_semantic.py`, `README.md` from `benchmarks/kernel_probe/`
- `tasks/lexical.json` from `results/kernel-retrieval/tasks.json` (48 tasks: exists 24, fields 12, refs 12; string-verified truth)
- `tasks/semantic.json` from `results/kernel-semantic/tasks.json` (24 tasks: callers 12, dispatch 12; hand-classified truth, mechanically re-checked)

Both task files point at the pinned Linux v6.12 tree in `$KERNEL_TREE` (commit adc218676). The tree is not copied.

New in this repo: `run_agent.py` (adds `--effort`, explicit model ids, trials, task-id selection) and `../../report.py` (cost per correct task, tail cost, turns). The copied runners are kept for reference and for the no-tools arms; the copied `main()` default paths do not apply here.
