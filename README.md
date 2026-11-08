# model-router

**The objective.** Pay for the model a task needs, not for the model the session happens to be on,
and know what that saved. Agent work inside Claude Code (code searches, fact lookups, browser flows,
bug fixes, research notes) runs by default on the session's model, usually the dearest one. Most of
it does not need that model, but nobody should guess which: the downgrade has to be measured, routed
automatically, and checked afterwards on the person's own work.

**The method, in the order it runs.**

1. A family per kind of work, each with a checker in code (a test suite, an answer pattern, a fetched
   page), so success is never an opinion.
2. Every model and effort runs the same tasks; each receipt is priced at list API prices from
   `catalog/models.json`. On a subscription those dollars measure rate-limit headroom.
3. The metric is cost per success, so failures are paid for. The rule (`decide.py`): the cheapest
   candidate whose Wilson lower bound reaches the best one minus 0.02; thin evidence cannot win.
4. No blind downgrade: work no family measures keeps the session's model.
5. The widget (`mod/`) routes each Agent call to the decision (ask, auto or off), shows the rate-limit
   windows, the 30-day consumption and the suggestions, each with the kind of evidence behind it:
   measured, extrapolated, unmeasured, learned.
6. After a change, the saving is measured on your own transcripts, per unit of the same work, next to
   the projection and the regression check: projected, realized, regress. A thin window says so.
7. Learned per machine and project: calls that struggle (re-issued, error-heavy, failed) against your
   own baseline, with a threshold you set; an override per project steps up where that project needs it.
8. Kept honest over time: a regression check on every Claude Code update, a monthly ledger, a
   paraphrase check, a contamination control on a private tree, the prefix measured under the
   harness settings.

**Install, on any machine with Python 3, git and the `claude` CLI**, at the prompt of a session:

```
/plugin install model-router --marketplace irlm/model-router
```

then restart Claude Code and run `/router setup` once. One user-scope install serves the terminal, the desktop app's local sessions
and VS Code on that computer; cloud sessions on claude.ai/code do not load local plugins. To update:
`claude plugin marketplace update model-router`, `claude plugin update model-router@model-router`,
restart. `mod/README.md` has the pane, the commands, Windows, updating and the reasoning behind
every number it shows.

**Why this is not built in.** Claude Code's documentation (read 2026-11-03) describes only manual
levers for a subagent's model: the agent file's `model` and `effort`, the Agent tool's `model`
parameter, `CLAUDE_CODE_SUBAGENT_MODEL`, `/model`, `opusplan` (by plan mode, not by kind of work) and
fallback chains on overload. No automatic per-task router, and the advice is "route tasks to
lower-cost models like Haiku" without a rule for which tasks. This repository is the rule, with the
numbers, and the check that it holds for you.

**Where it stands (2026-11-03).** Six families decided from measurements (`ROUTING.md`): code
searches, bug fixes with the runner, tests with the runner, browser flows, fact lookups, all Haiku at
effort low; research notes Sonnet at low (`results/cell9`: Haiku missed the bar on citations, 16/18).
The find-feature families on a private tree gave 100% for every tier, so the kernel being in the
training data does not explain the result; a paraphrase moved nothing; the prefix of every request is
22.7k tokens here, 1.9k of it the MCP connector. Cell 8 (`results/cell8`) found that xhigh effort
costs 1.3-1.5x low for the same 24/24 fixes, and that the unused agent files cost 17k tokens on every
request (`results/prefix`). `GAPS.md` lists what is still open.

## The loop

```
catalog/discover.py      new or delisted model ids, stale prices        (run after a launch)
catalog/models.json      the prices, with a verified date and a source   (a human fills in a new price)
bench/<family>/run_agent.py   run a family for one model x effort, receipts with token counts
bench/<family>/grade.py       the mechanical checker (KUnit build, scripted user, string truth)
report.py                grades every receipt and prices it from the catalog (no judge model)
decide.py                the rule: cheapest candidate whose Wilson lower bound is at or above the best minus a margin
apply_agents.py          writes the decision into the agent files you have in ~/.claude/agents/ (--revert undoes); installs agents/web-researcher.md when missing
regress.py               after a Claude Code update or monthly: each default on a small sample, binomial check
tools/ledger.py          monthly: what this machine actually ran (subagent calls, tokens, cost), from the transcripts
tools/prune_agents.py    moves the agent files no transcript ever called out of the prefix, in whatever folder they sit (reversible)
tools/fixed_text.py      what every request carries whatever the task (agent list, skill list, hook text, loaded skill bodies) and what it cost, from the transcripts
tools/claude_home.py     where Claude Code keeps its files (~/.claude, or CLAUDE_CONFIG_DIR)
tools/fixtures/          transcript rows as each Claude Code version writes them, content replaced: the format test
tools/status.py          where the routing stands on this machine, what is worth doing, and the suggestions (text or --json)
tools/consumption.py     the last 30 days of interactive work by model and effort, every Agent call priced and classified
tools/update.py          re-check: regress.py on every family whose fixtures exist here, then commit and push
mod/                     the Claude Code widget: status line + /router pane over the scripts above
```

## The widget

`mod/` is a Claude Code mod (hooks module) that runs on Linux, macOS and Windows alike, since it
runs inside Claude Code: a status line under the prompt (`router ok · v1.1 · 3 families checkable
here · Claude Code 2.1.316 · 12:01`, or `router: 2 to check · /router`), and `/router` opens a pane
with the families table, the agent files, price freshness, the ledger dates and buttons that run
`tools/update.py`, `tools/ledger.py --commit`, `apply_agents.py` and `git pull`. Install on a machine
with Python 3, git and the `claude` CLI, at the prompt of a terminal session:

```
/plugin install model-router --marketplace irlm/model-router
```

That is the whole setup: the install clones this repository (the marketplace) and the widget reads
from that clone. A checkout of your own, for the benchmark or the code, is an option in `/config`
(default `~/Projects/Github/model-router`; on Windows `~` is `C:\Users\<you>`). To update:
`claude plugin marketplace update model-router`, then `claude plugin update model-router@model-router`,
then restart Claude Code (`mod/README.md`, "Updating", says what changes before and after the restart).
`mod/README.md` has the Windows steps (Git for Windows, Python 3, then the same install line) and the
rest; `claude plugin validate mod` and `claude plugin test mod` check the mod, `python3 tools/test_status.py`
the data side (classifier, suggestions, per-change savings), `python3 bench/common/test_harness.py` the runners.

The widget also routes each Agent call: when a measured family covers the task and the call asks
for a dearer model than the decision, it asks you, rewrites the call (auto) or stays out (off), per
the "Route Agent calls" option; nothing unmeasured is touched. The pane also shows the subscription's rate-limit windows, what the last 30 days consumed (main
sessions by model and effort from the transcripts, each Agent call priced and classified) and
suggestions: where the same work could consume less, each labelled `measured`, `extrapolated`
or `unmeasured` with the cell its number comes from. The monthly ledger keeps the same 30-day
table, so a change of habit shows up as a change between entries.

- **Receipts hold tokens, not dollars.** A price change is a catalog edit plus `report.py`; nothing
  is re-run. `report.py --prices other.json` prices everything under a what-if catalog.
- **A new model is run only where it can change the decision:** `decide.py` lists, per catalog
  model with no receipts, the families where it is not dearer than the current default (or where the
  default is below the ceiling), cheapest family first, with the expected cost of that run.
- **Thin evidence cannot win a family.** A candidate is scored by the lower bound of the 95% Wilson
  interval of its rate (`decide.py --rule lower`, the default): 10/10 scores 0.72, 63/63 scores 0.94.
  The table also shows pass^k, the chance that every trial of a task succeeds.
- **Runs the harness lost are retried, not judged.** A lost browser tab or a CLI failure is
  `incomplete` or `operational`; `decide.py` leaves those out of the rate.
- **Harnesses.** `bench/common/harness.py` runs a session on Claude Code (`claude -p`, Anthropic
  models) or on the OpenAI Codex CLI (`codex exec`, OpenAI models) and returns one receipt shape, so
  the checkers never see which harness answered. Every runner takes `--harness`. The code families
  run Codex in a workspace-write sandbox with the build directory as an extra writable root. A
  runner arm (`--kunit`) through Codex also needs `--codex-full-access`: the Codex sandbox blocks
  ptrace, so KUnit's UML kernel cannot boot inside it, and dropping the sandbox lets the model act
  as your user on the whole machine, so it is never the default. The browser families offer only
  harnesses that have a browser (`harness.CAPABILITIES`), which today means Claude Code.
  `python3 bench/common/test_harness.py` checks the adapters' command lines without calling anything. Claude Code agent files can only name Anthropic models, so `apply_agents.py`
  applies the cheapest Anthropic candidate above the bar even when another provider wins a family;
  `routing.json` says when that happened.

## Layout

- `ROUTING.md`, `routing.json`: the decision (model and effort per task family, with the evidence)
  in prose and for scripts. The decision table in `ROUTING.md` is generated by `decide.py`.
- `catalog/`: `models.json` (models, API prices, verified date, source), `price.py` (prices a
  receipt's usage; matches the CLI's own figure to the cent on every Anthropic receipt so far),
  `discover.py` (live model lists per provider diffed against the catalog; needs the providers' keys).
- `bench/find_feature/`: find a feature in a huge codebase. Agent with file and search tools in a
  pinned Linux v6.12 tree, 72 tasks, string-verified truth.
- `bench/fix_bug/`: fix a bug with a failing KUnit test; 10 single-site tasks and 21 hard tasks
  (hidden helpers, two sites), with and without the runner in the loop.
- `bench/write_tests/`: write a KUnit suite for a function; success = builds, passes on the real code,
  fails on a seeded bug. With and without the runner.
- `bench/browser_flow/`: drive a small server-rendered app through a 9-item checklist in a real
  Chrome tab (Claude-in-Chrome tools), truth from a scripted user, 11 planted defects.
- `bench/own_app_flow/`: the same shape on the author's own Go web store, 10 items, 14 planted
  defects behind an environment variable, a separate Postgres with a small seed. A fixture on one app,
  so it stays local (see `local/README.md`); the receipts and tables of cell 5 are in.
- `bench/repo_fix/`: fix a bug with a failing test in one of the user's own repositories
  (`repos/<name>.json`, a local file, `example.json` shows the shape; the author's was TypeScript with vitest): `make_tasks.py` mutates one source
  line at a time and keeps the mutants the suite catches, the agent gets the failing output and the test
  command, `grade.py` reruns the suite on the patched tree. A private tree, so no training-data leak;
  `--prompt-variant b` asks the same thing in other words.
- `bench/research_synthesis/`: a 250-700 word research note that answers three of the web_research
  questions, each claim with the page read; graded in code by the same checker (cell 9: sonnet low).
- `bench/find_feature/private_tree.py`: the find_feature families on a repository of your own, truth by
  word search; the contamination control (cell 9: no effect). Its tasks and receipts stay local.
- `bench/web_research/`: look up one technical fact on the web and cite the page (18 questions, mostly
  PostgreSQL and DuckDB defaults and limits). `grade.py` checks the answer by pattern, then fetches every
  cited URL and looks for the evidence in its text: a right answer with a made-up or wrong URL is
  `right-unsourced`, not `correct`. `--self-test` checks the tasks' own sources.
- `bench/common/`: worktree and KUnit helpers, the harness adapters.
- `ledger/`: `usage-<date>.md` from `tools/ledger.py` and `regress-<tag>.md` from `regress.py`.
- `mod/`: the Claude Code widget (see The widget); `.claude-plugin/marketplace.json` at the root makes this repository its marketplace.
- `tools/`: `usage_scan.py` (the transcript scan behind `GAPS.md` and the ledger), `prune_agents.py`,
  `status.py`, `update.py`, `ledger.py` (`ledger.sh` wraps it for the timer), `install_ledger_timer.sh` (a monthly systemd user timer, `model-router-ledger.timer`, 1st of the month 09:00; installed 2026-11-01, `--remove` undoes it).
- `runs/<bench>/`: one receipt per call (`runs-<model>-<effort>[-kunit]-t<trial>.jsonl`). Committed.
- `results/<cell>/`: the tables and a short reading of each cell.

## Run a family, then decide

```bash
python3 bench/find_feature/run_agent.py --model claude-haiku-5-5 --effort low
python3 bench/find_feature/run_agent.py --model gpt-6-luna --effort low --harness codex
WT=$KERNEL_WT                    # local/config.json: kernel_worktrees
python3 bench/fix_bug/run_agent.py --model gpt-6-luna --effort low --harness codex \
    --worktree $WT/sonnet --tasks bench/fix_bug/tasks-hard.json --bench fix_bug_hard \
    --kunit --build-dir $WT/build-sonnet --codex-full-access   # any free worktree and build dir
python3 bench/repo_fix/run_agent.py --repo <name> --slot a --model claude-opus-5-5 --effort xhigh
python3 bench/repo_fix/grade.py --repo <name> --slot grade
python3 bench/web_research/run_agent.py --model claude-haiku-5-5 --effort low && python3 bench/web_research/grade.py
python3 report.py --out results/<cell>
python3 decide.py --dry-run        # the table and the plan; drop --dry-run to write routing.json and ROUTING.md
python3 apply_agents.py            # into the agent files; --revert undoes
```

`bench/repo_fix/repos/<name>.json` (local; `example.json` shows the shape) says how its clone and worktrees are set up (a clone of the
user's repo under `~/Projects/Github/model-router-evaluation/`, one worktree per run slot, the agent's
slot and the grader's slot never shared). The kernel code families need the kernel worktrees and build directories under
`$KERNEL_WT/` (one per run that is in flight at the
same time; they are named after the model that first used them); the browser families
need Chrome with the Claude extension, and the own-app fixture's `setup.sh` for the store.

## Caveats

- The `claude` CLI here is logged in with a claude.ai subscription, and `codex` with a ChatGPT
  account. Costs are the API-equivalent price of the tokens used, not a bill. The ranking between
  models is still valid; the dollars are what an API key would pay.
- Codex has its own tools inside a sandbox: a tool list and a turn limit cannot be enforced, so a
  Codex run in a "no runner" arm can still build and test. Receipts say so.
- Anthropic's bar for a production cutover is about 50 cases and 5 trials per configuration. The
  families here are 10 to 72 tasks with one to three trials; `decide.py --min-trials` raises the bar.
- Receipts keep Claude Code's per-model usage (`model_usage`) since 2026-11-01. The web tools fetch
  pages through a second model and bill that content as uncached input the summed `usage` block leaves
  out, so a web-tool receipt without the breakdown is priced by the CLI's figure (catalog/price.py says
  when). On every other receipt the catalog and the CLI agree to the cent.
- The fixed Claude Code prefix (system prompt, tools, the user's agent list) is identical across
  models and is part of every receipt. That is the real workload, so it stays in.
- The browser runs use the user's real Chrome. Closing it mid-run loses the flow (it is then retried).
