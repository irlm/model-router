# model-router

**The objective.** Pay for the model a task needs, not for the model the session happens to be on,
and know what that saved. Agent work inside Claude Code (code searches, fact lookups, browser flows,
bug fixes, research notes) runs by default on the session's model, usually the dearest one. Most of
it does not need that model, but nobody should guess which: the downgrade has to be measured, routed
automatically, and checked afterwards on the person's own work.

Two parts, one repository: a **benchmark** that measures every model and effort on real agent work
and decides a routing per kind of task, and a **Claude Code widget** (`mod/`) that applies that
routing to each Agent call, watches the agents as they run, and shows what the subscription is
spending and what the routing saved.

## Install

On any machine with Python 3, git and the `claude` CLI, at the prompt of a Claude Code session:

```
/plugin install model-router --marketplace irlm/model-router
```

Restart Claude Code, then `/router setup` once (it installs the routed agent files) and `/router doctor`
to see each piece of the installation as ok or to do. One user-scope install serves the terminal, the
desktop app's local sessions and VS Code on that computer; cloud sessions on claude.ai/code do not load
local plugins. Windows works the same way (Git for Windows, Python 3, then the same line; `mod/README.md`,
"Windows", has the details).

To update, at a terminal:

```
claude plugin marketplace update model-router
claude plugin update model-router@model-router
```

then restart Claude Code (`/restart` on macOS and Linux). The pane names the widget version it runs and
says, in yellow, when a newer one is on disk waiting for a reload. From a checkout, without a push:
`claude plugin marketplace add <the checkout>` then `claude plugin install model-router@model-router`;
Claude Code reads the widget from that folder, so a commit shows at the next start or `/reload-plugins`.
`mod/README.md` has the pane, every command, the Windows steps, updating, and the reasoning behind every
number it shows; `CHANGELOG.md` what each version changed.

## What you see

**The status line**, under the prompt, says only what has something to say:
`5h 37% · 7d 62% · routed 2 · saved $7 since 11-02 · up to $25 less last 30d ($25 measured) · 1 to check · /router`.
The percentages are the subscription's rate-limit windows as the last API response reported them;
`routed` is what the router moved this session; `saved` is what your transcripts show since the last
recorded change; `to check` counts the advice. `/config` makes it `minimal` or `off`.

**The main pane** (`/router`) is a header bar and a set of titled frames, each border in the colour of
what it holds: Session live cyan, Agents green while any runs, Limits green, yellow or red by the
fullest window, To check yellow, a running job cyan and a failed one red. The glance shows what is acted
on; `d` (Details) adds every other section (Routing, By week, Consumption, Changes, Learned on this
machine, Routed). `/router check` prints the same lines as text. An example, figures invented:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ model-router  /  Model router           12 turns · $1.84 · cache hit 93% · ctx 148k · fable-5-1 high │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
widget 0.20.1 loaded
repo ~/Projects/Github/model-router · 255ce37 · clean
spend $61 last 30d
routed this session 2
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [ Session live ]                                                                                     │
│   $/turn   ▁▂▁▃▂▁▂▆▂▁▁▂  max $0.41 · 1 turn with 3+ tool errors                                      │
│   effort   ··↓↓··↑·····  auto: 2 at the measured effort (est $0.05 less), 1 back up after errors     │
│   agents   3 calls · 2 routed · escalated: find_feature (a call routed to haiku low failed)          │
│   plan     saved $13 of $72 projected ███░░░░░░░ 18% · since 10-30                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [ Agents ]                                                                                           │
│ ▘ agents running 2 · done 5 ($0.31, 1 failed)                                                        │
│   | Explore             haiku low   find_feature   find the parser           4 steps   12s           │
│   | general-purpose     fable high  unmeasured     compare three queues      9 steps   48s           │
│     └ | Web Researcher  haiku low   web_research   look up the RFC           2 steps    5s           │
│   ✓ Explore             haiku low   find_feature   find the schema loader    6 steps   20s  $0.02    │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [ Limits ]                                                                                           │
│ 5h  ███████░░░░░░░░░░░░░  37% used, resets 14:00                                                     │
│ 7d  ████████████░░░░░░░░  62% used, resets Thu 09:00                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [ To check ]                                                                                         │
│   agent web-researcher.md not installed yet · Apply agents (a)                                       │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [ Suggestions ]                                                                                      │
│   1. fact lookups on general-purpose → Web Researcher (haiku low)   up to $9 less    measured        │
│   2. main sessions at xhigh → high                                  up to $11 less   extrapolated    │
│   3. research notes on general-purpose → Sonnet low                 up to $5 less    measured        │
│   4 more under Details (d)                                                                           │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
 Refresh (r)  Fetch origin (f)  Re-check routing (u)  Details (d)  Monitor (g)  Ledger now (l)  Apply agents (a)  Pull (p)
```

- *Session live* is the session as it runs, from the engine's own per-turn figures: cost per turn as a
  sparkline, the effort strip (one mark per turn: `·` the session's effort, `↓` a measured family's,
  `↑` back up after 3 tool errors, `?` would have gone down in advise mode), the Agent calls with what
  was routed and what escalated, and the plan gauge: what the transcripts show saved since the last
  change against what the suggestion projected.
- *Agents* lists the subagents of this session the way a connection monitor lists connections: type,
  model and effort, the measured family the prompt read as, the task, requests so far, elapsed; a child
  under the agent that spawned it; a row a minute without a request turns yellow; a finished agent shows
  its cost and folds into the `done` count, failed and stopped counted apart.
- *Limits* are the rate-limit windows as bars. *To check* are things to do, not failures. What the widget
  could not read (the limits, the context size, the marketplace file, the saved runs) is listed under Details
  as `not read: … (reason)` rather than left blank. *Suggestions*
  say where the same work could consume less, each with its estimate and its kind of evidence:
  `measured`, `extrapolated` or `unmeasured`, with the cell its number comes from.

**The run monitor** (`/router monitor`, or `g` from the main pane) draws the current run as a graph in
a second pane: the main session at the root, each agent a box to the right of the one that spawned it,
a column per depth, the border in the state's colour (green at work, yellow quiet, red failed or
stopped, dim when done with its cost), the arrow weighted by the context the child was sent
(`━━` from 16k tokens, `──` from 4k, `┄┄` below, the estimate on the branch). Beside the graph, from
130 columns (under it when narrower), the live panels of the agents at work with their last tool calls,
an error in red; then the run's event log. A sketch:

```
┌ 00 main session ──────────────────┐
│ fable-5-1 high · 12 turns · $1.84 │
└─────────┬─────────────────────────┘
          ┗━━ ~18k ━━▶ ┌ 01 Explore ────────────────────────────────────────────────────────────┐
                       │ ● RUNNING   haiku low   find_feature   find the parser   4 steps   12s │
                       └─────────┬──────────────────────────────────────────────────────────────┘
                                 ┗┄┄ ~9 ┄┄▶ ┌ 02 Web Researcher ────────────────────────────────────────────────────┐
                                            │ ● DONE   haiku low   web_research   look up the RFC   2 steps   $0.02 │
                                            └───────────────────────────────────────────────────────────────────────┘

● 01 Explore / live                                   ● 02 Web Researcher / stopped  [DONE in 5s]
12:01:04  Grep "parse_config" tools                   12:00:58  WebFetch https://www.rfc-editor.org/rfc/rfc8446
12:01:07  ERROR $ python3 -m pytest -q                12:01:01  answer: RFC 8446

[ Event log ]
12:00:51  01 Explore spawned on haiku (~18k ctx)
12:00:52  02 Web Researcher spawned on haiku (~9 ctx) by 01
12:01:01  02 Web Researcher done in 5s, $0.02

 List (g)  History (3) (h)  Save report (s)  Model router (m)
```

Before any agent has run, the main session is drawn alone: its box says `● WORKING` while a turn runs
and `● IDLE` after, with the turns and cost so far, and its own live panel lists the main session's tool
calls; agents hang under it as they spawn. An agent the engine resumes under the same id (a hand-back, a
follow-up) is a new run of the same box, "02 Web Researcher · run 2"; a child hangs under the run active
when it spawned. Nothing here is a dependency graph: the engine reports who spawned whom, not who waits
on whom, so no box is marked blocked.

**Runs, tasks and reports.** The agents a prompt spawns are one run; `/router task start <name>` …
`/router task end` groups everything under a name across as many prompts as it takes. When a run's last
agent ends it is saved as one JSON file under `<config>/model-router/runs/<day>/`, with every agent, its
answer and the events. `h` in the monitor lists the session's runs and the ones saved on this machine;
`/router runs` lists them, `/router runs show <id>` prints one, `/router runs import [--days N]` rebuilds
the days before the widget watched from the transcripts. `/router monitor save [id]` (or `s`) writes a
run's report into the project as `docs/runs/<day>-<words>.md`: what was asked, the graph as text, the
agents with model, effort, cost and outcome, their answers, the events.

**Routing each Agent call.** When the main model starts a task through the Agent tool and a measured
family covers it (a read-only code search on Explore, a short fact lookup, a browser flow, a fix with the
test runner in the loop), and the call asks for something dearer than the family's decision, the widget
acts by the "Route Agent calls" option: `ask` (the default) puts the question in the terminal with the
evidence (`haiku low (measured 214/216, $0.005/success)`), `auto` routes and toasts, `off` does nothing.
The decision is applied on the subagent itself (the model at the spawn, the effort on each of its
requests), never by rewriting the Agent tool's input, so auto mode's own review of the call stands.
Nothing unmeasured is touched: a research report, a design, a review, a plan keep their model; a prompt
that names a test runner or asks for a code change is never read as a research note, however it is worded.
The same keyword rule classifies the ledger, and a test keeps the two copies identical. A routed
call that fails, or that the main model re-issues within ten minutes, escalates its family for the rest
of the session. `/router effort advise|auto|off` extends the same rule to the main session's own
requests: a prompt that reads as a measured family runs at that family's measured effort, back up after
3 tool errors; advise (the default) only says what auto would have done and the estimate.

**Every verb** (`/router <verb>`; the buttons are the same jobs):

| Verb | Does |
|---|---|
| `setup`, `doctor` | first run on a machine; the installation piece by piece, ok or to do |
| `check` | the pane's text, every section (`fetch`: after `git fetch`, so behind/ahead are current) |
| `routing ask\|auto\|off` | how Agent calls are routed this session (`/config` for good) |
| `effort advise\|auto\|off` | the main session's effort rule |
| `monitor`, `monitor save [id]` | the run monitor pane and its text; a run's report into `docs/runs/` |
| `task start <name>`, `task end` | group the agents of several prompts into one named run |
| `runs`, `runs show <id>`, `runs import [--days N] [--rebuild]` | the saved runs; one of them; runs rebuilt from the transcripts |
| `prefer <class> <model> <effort>`, `prefer clear <class>`, `prefer` | an override for this project, before the family default |
| `mark <note>` | record a change made by hand, so the saving counts from now |
| `dismiss <n or id>`, `undismiss <id>` | hide a suggestion you judge wrong, and bring it back |
| `agents pin\|check\|update\|list` | agent files from outside this repository, pinned to their source commit; a change there shown as a diff before it lands |
| `prune` | move the agent files no transcript ever called out of the prefix (reversible) |
| Re-check routing (u) | `tools/update.py`: `regress.py` on every family that can run here, then commit and push the entry |
| Ledger now (l) | `tools/ledger.py --commit` (into the pane in the marketplace clone) |
| Apply agents (a) | `apply_agents.py`: routing.json's model and effort into the agent files you have |
| Pull (p) | `git pull --ff-only` |

## The method, in the order it runs

1. A family per kind of work, each with a checker in code (a test suite, an answer pattern, a fetched
   page), so success is never an opinion.
2. Every model and effort runs the same tasks; each receipt is priced at list API prices from
   `catalog/models.json`. On a subscription those dollars measure rate-limit headroom.
3. The metric is cost per success, so failures are paid for. The rule (`decide.py`): the cheapest
   candidate whose Wilson lower bound reaches the best one minus 0.02; thin evidence cannot win.
4. No blind downgrade: work no family measures keeps the session's model.
5. The widget routes each Agent call to the decision (ask, auto or off), shows the rate-limit
   windows, the 30-day consumption and the suggestions, each with the kind of evidence behind it:
   measured, extrapolated, unmeasured, learned.
6. After a change, the saving is measured on your own transcripts, per unit of the same work, next to
   the projection and the regression check: projected, realized, regress. A thin window says so.
7. Learned per machine and project: calls that struggle (re-issued, error-heavy, failed) against your
   own baseline, with a threshold you set; an override per project steps up where that project needs it.
8. Kept honest over time: a regression check on every Claude Code update, a monthly ledger, a
   paraphrase check, a contamination control on a private tree, the prefix measured under the
   harness settings.

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
tools/agent_sources.py pinned third-party agent files: diff with flags before an update lands
tools/release.py       tag a version (v<plugin.json version>) after the CHANGELOG and tree checks
tools/claude_home.py   where Claude Code keeps its files (~/.claude, or CLAUDE_CONFIG_DIR)
tools/fixtures/          transcript rows as each Claude Code version writes them, content replaced: the format test
tools/status.py          where the routing stands on this machine, what is worth doing, and the suggestions (text or --json)
tools/consumption.py     the last 30 days of interactive work by model and effort, every Agent call priced and classified
tools/runs.py            the runs the widget saved (list, show, export as markdown), and runs rebuilt from the transcripts
tools/update.py          re-check: regress.py on every family whose fixtures exist here, then commit and push
mod/                     the Claude Code widget: status line, the main pane and the run monitor over the scripts above
```

## The widget, under the hood

`mod/` is a Claude Code mod (hooks module), one `register.tsx` and its tests, that runs on Linux,
macOS and Windows alike since it runs inside Claude Code. The install clones this repository (the
marketplace) and the widget reads from that clone; a checkout of your own, for the benchmark or the
code, is an option in `/config` (default `~/Projects/Github/model-router`; on Windows `~` is
`C:\Users\<you>`). The agents block, the monitor and the runs come from the engine's `agent.spawn`,
`turn.step`, `turn.complete` and tool events, with a one-second tick only while agents run; the
consumption, the suggestions and the savings from `tools/consumption.py` and `tools/status.py` over
the local transcripts, where every ratio is a named constant with the cell it came from. The keyword
lists that classify a prompt are the same for the router and the ledger, so what is counted and what
is acted on agree. `claude plugin validate mod` and `claude plugin test mod` check the mod,
`python3 tools/test_status.py` the data side (classifier, suggestions, per-change savings),
`python3 bench/common/test_harness.py` the runners. CI runs the Python tests and the widget's tests on Ubuntu, macOS and Windows.

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
- `mod/`: the Claude Code widget (see What you see); `.claude-plugin/marketplace.json` at the root makes this repository its marketplace.
- `docs/runs/`: run reports written by `/router monitor save` (none committed here; yours land in your project).
- `tools/`: `usage_scan.py` (the transcript scan behind `GAPS.md` and the ledger), `prune_agents.py`,
  `status.py`, `update.py`, `runs.py`, `ledger.py` (`ledger.sh` wraps it for the timer), `install_ledger_timer.sh` (a monthly systemd user timer, `model-router-ledger.timer`, 1st of the month 09:00; installed 2026-11-01, `--remove` undoes it).
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
