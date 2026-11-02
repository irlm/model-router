# local: what stays on this machine

The repository is generic: no project names, no home paths, no code from anyone's own
repositories. What is particular to a machine or to its owner's repositories lives here and in
the paths `.gitignore` lists, and never gets committed.

`local/config.json` (copy `config.example.json`) says where the fixtures are on this machine:

| key | what |
|---|---|
| `kernel_tree` | the pinned Linux v6.12 tree the find_feature and fix_bug task files point at as `$KERNEL_TREE` |
| `kernel_worktrees` | the kernel worktrees and KUnit build directories, `$KERNEL_WT` (one per run in flight) |
| `skip_projects` | fragments of `~/.claude/projects` directory names that are benchmark sessions here, so the ledger and the consumption scan leave them out of "your own work" |

Fixtures on the owner's own repositories, kept out of git:

- `bench/repo_fix/repos/<name>.json`: a repository of your own for the repo_fix family
  (`example.json` shows the shape), its `tasks.json` and `mutants.json` made by `make_tasks.py`,
  and the receipts under `runs/repo_fix/`. The decision and the tables (`results/cell8`,
  `routing.json`) are committed; the source lines the tasks quote are not.
- `bench/own_app_flow/`: the browser-flow family on the author's own web app (a scripted user as
  the oracle, planted defects behind an environment variable), with its receipts under
  `runs/own_app_flow/`. One app, one fixture; `bench/browser_flow/` is the generic family in the
  same shape, with a toy app anyone can run.

A new machine with none of this set up still gets the widget, the ledger, the consumption scan
and the web_research regression (it needs only the `claude` CLI); the pane says which other
family is blocked and why.
