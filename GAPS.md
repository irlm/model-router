# What is still open (2026-11-18)

The benchmark and the widget are described in `README.md`; what each version changed is in
`CHANGELOG.md` (the widget) and the `results/<cell>/` readings (the measurements). This file keeps only
what is not done. The history of the earlier plan, written on 2026-10-31, is below under "Done".

## Open

1. **A calibrated prose judge for the research notes.** `bench/research_synthesis` is graded in code on
   facts and sources (cell 9); the quality of the prose is not graded at all. A rubric or pairwise judge
   calibrated against a dozen hand-read notes would let the family rank models, not only admit them.
2. **A capability tier that can rank a new model.** Every decided family sits at or near its ceiling
   for every Claude tier (`fix_bug` hard set included), so a new model is admitted or not, never
   ranked. Tasks in the 30 to 70% band are what rank models.
3. **The price of a wrong answer.** The step-up rule prices a wrong answer by assertion ("18x a
   session"), not by measurement. The per-machine "learned" data (re-issued, error-heavy and failed
   calls, `tools/status.py`) is the raw material; nothing turns it into a measured price yet.
4. **Browser work as the agent file describes it.** Screenshots, visual judgement, exploratory testing
   are unmeasured; `bench/browser_flow` measures a scripted checklist.
5. **The Codex runner arm** cannot run inside Codex's sandbox (ptrace); only with `--codex-full-access`,
   which lets the model act as the user on the whole machine, so it runs only on the user's say.
6. **The monthly ledger runs itself on Linux only.** `tools/install_ledger_timer.sh` is a systemd user
   timer. On macOS and Windows nothing schedules it: the pane says "no usage ledger since …" after 35
   days (`ADVICE_LEDGER_DAYS` in `tools/status.py`) and `/router ledger` writes one. A launchd agent and
   a Scheduled Task would close this.
7. **Main-session effort is measured by extrapolation.** `/router effort auto` applies the measured
   families' effort to main-session turns that read as one of them; the cell 8 effort ratios come from
   subagent fixes, not from main sessions on the user's own repositories.
8. **The widget's tests run on Linux in CI**, the author's machines are macOS and Windows; the path
   handling (home directory, project key, Python on PATH) is exercised there by use, not by CI.

### From the 2026-11-18 review pass (what the widget would not notice)

Three readers went over the code, the features and the field. The nine defects they found are fixed in widget
0.30.1 (`CHANGELOG.md`). What they left open, in the order it is worth doing:

9. **A model in the transcripts with no receipts in any family has no alarm.** The sessions have run on
   `claude-fable-5-2` since 2026-11-10 and on `claude-opus-5` (effort unknown), but `EFFORT_RATIO` and
   `OPUS_OVER_FABLE` in `tools/status.py` are 5.1-and-5.5 ratios, the tier suggestion filters on `fable-5-1` so the
   5.2 spend drops out of it, and `decide.ALIAS` maps `fable` to 5-1 while the engine resolves it to 5.2. The only
   advice is "prices verified N days ago". The check: a model in the window's rows that no family's evidence
   names, with `decide.py --dry-run`'s list of what to run (`plan_for_unmeasured_models` in routing.json exists
   and is never surfaced).
10. **A routed fix agent that never ran the tests is invisible.** `repo_fix` was measured with the runner in the loop
   (72/72); the widget appends `RUNNER_NOTE` and hopes. It keeps each agent's last eight tool calls and its answer:
   a `repo_fix`-routed agent whose tail has no runner command, or a `find_feature` answer that says "not found",
   is the free part of item 3 (the price of a wrong answer), and should mark the row and count as a failure for
   the escalation.
11. **Five of seven families are never re-checked on a machine without their worktrees** (`can_run` says no for
   find_feature, fix_bug, write_tests, browser_flow, repo_fix here), and the regression advice is satisfied by any
   regress file matching the Claude Code version. The pane should say "N families have no check on this
   machine", and `ok 5/6` should carry its power (at n=6 the binomial catches a drop below about 65% only).
12. **The rate-limit windows are read and drive nothing.** Every monitor in the field (claude-dashboard,
   Claude-Code-Usage-Monitor, ccstatusline) shows a burn rate and a time to the limit; two routers (jev-router,
   frugal) tighten their policy at 80 and 95% of the window. The widget has the windows from the API responses;
   a slope over the session gives the time, and a threshold that turns `ask` into `auto` and `advise` into
   `auto` for the rest of the window is where routing pays on a subscription.
13. **The prompt classifier has no guard against a false positive.** Any general-purpose prompt under 900
   characters with "what is the" is a fact lookup routed to Haiku low ("what is the cause of this crash in
   parser.c?" included). A risk floor (AutoMode's idea: auth, migrations, payments, destructive operations
   never go below a tier) and a fail-closed fallback for the words the rule misses are the two halves.
14. **The biggest subagent bucket is `other`** (half of subagent spend on this machine, general-purpose calls),
   and the pane says nothing about it. A delegation break-even (the 23k prefix as a share of each agent's cost:
   "this Explore paid 78% of its cost on the prefix") is what frugal and the Systima "subagent tax" write-up
   report and this repo measured but never shows.
15. **The suggestions ignore the widget's own levers.** The effort suggestion's action is `claude --effort low`
   while `/router effort auto` exists and is off by default (advise); the tier suggestion says "try opus" while
   the window already holds Opus messages that are never compared with the Fable ones. Comparing the user's
   own Opus and Fable messages (cost per message, tool-error and re-issue rates) would turn "unmeasured" into
   measured on this machine.
16. **Shadow mode and replay.** A candidate routing.json cannot be priced on the last 30 days before `apply`;
   `tools/consumption.py` has every call with its tokens and class, so a replay under another policy is a
   function away (jev-router's `--shadow` and `replay`).
17. **The command names overlap**: `/router update` is the regression check, `/router upgrade` updates the
   install, and `pull`, `fetch`, `check` exist beside them. A reader of "update" expects the plugin update.

Lower on the list, from the code review and not yet fixed: `decide.py` records `pass_k: 0.0` for a cell with a
task of zero judged runs and crashes when a family's default model is not in the catalog; the weekly slots are
UTC days while the "days since" are local; `tools/runs.py import` compares calls by dict equality (quadratic);
`bench/common/worktree.py reset()` runs `git reset --hard` on any path it is given; `call_claude` in the harness
does not catch a timeout the way `call_codex` does.

## Done, from the 2026-10-31 plan

The plan listed twelve gaps; what closed each one:

- Unused agent files pruned (prefix 40k → 23k tokens, `results/prefix`; `tools/prune_agents.py`,
  `/router prune`); what every request carries measured under five harness settings (`tools/fixed_text.py`).
- A family on a real, private repository (`bench/repo_fix`) with the effort sweep: Opus and Fable fix
  24/24 at low, high and xhigh; xhigh costs 1.3-1.5x low; Haiku low with the runner 72/72 at 1/70 of Fable.
- The ledger: `tools/ledger.py` (monthly, `ledger/usage-<date>.md`), `/router ledger`, the per-change
  saving measured on the user's own transcripts (projected, realized, regress).
- Web research measured with a citation checker (`bench/web_research`, Haiku 76/78 at 1/17 of Fable
  xhigh) and the research-notes family graded on facts and sources (cell 9, Sonnet low).
- Wilson intervals and pass^k in `report.py` and `decide.py`, `--rule lower` the default.
- The saturated cells are the regression suite (`regress.py`, run on every Claude Code update, with the
  version and the prefix recorded; `/router update`).
- One paraphrase per family (no effect); the find-feature families on a private tree (no contamination
  effect).
- Routing applied automatically: the widget routes each Agent call (ask, auto, off), applies the decision
  on the subagent's spawn and requests, escalates a family on a failed or re-issued call, learns struggles
  per machine, takes per-project overrides, and shows the rate-limit windows, the 30-day consumption, the
  suggestions with their evidence, the agents as they run and the run monitor.

## What the public work misses, and this repo has

The field in 2026-11 (a search on 2026-11-18): GitHub lists twenty-odd "route Claude Code subtasks to the cheapest
model" projects created in 2026, two named `model-router`; a dozen subagent monitors and cost dashboards; the
gateways (OpenRouter's auto router picks model and effort, LiteLLM routes by cost with cooldowns and a classifier).
Nothing found verifies its methodology beyond its own README; the closest in rigour are AutoMode (an end-to-end
session benchmark graded by hidden tests, a 90% interval on the cost ratio) and cc-model-router (48 runs, no
intervals). What they have and this repo lacks is listed above (items 12 to 16); what this repo has and none of
them does: a routing decided by Wilson lower bounds and cost per success with a runner-in-the-loop ablation, a
regression suite on every Claude Code update with the version and the prefix recorded, the saving of each change
measured on the user's own transcripts against its projection, the escalation on the main model's re-issue, the
context-weighted run graph. Claude Code itself shipped no automatic model or effort selection (`/effort auto`
clears the saved level); its `/usage` attributes recent usage to subagents, skills and plugins with a one-key fix,
which overlaps the Suggestions frame.


- **Leaderboards** (Terminal-Bench, Artificial Analysis, HAL) now publish cost per task, tokens,
  model-plus-harness pairs and confidence intervals, and Artificial Analysis lists effort
  variants. They measure their tasks on their harness. They cannot know this machine's 23k-token
  prefix, which sets the cost floor on short tasks, or whether a test runner is in the loop.
- **Cost-of-Pass** formalises the metric used here (expected cost of a correct answer, with a
  frontier across models) on question-answer datasets. No agent loop, no harness, no runner
  ablation.
- **Routers** (RouteLLM, Not Diamond, Martian; RouterArena as the neutral benchmark) are
  per-query classifiers on single-turn questions, ranked by accuracy against cost per 1k queries.
  RouterArena found no router best on all metrics and the commercial ones over-picking expensive
  models. A router cannot see your checker; Claude Code offers no per-call router in its settings, so
  the widget does it from the plugin hooks (the spawn's model, the subagent's effort).
- **Anthropic's own guidance** says "use Haiku for simple subagent tasks" and gives no rule for
  which tasks. This repo has a rule with numbers, and the runner finding (write-tests 4/10 to
  10/10 on Fable once the runner is in the loop) at a size nobody publishes.

## Sources

The field, 2026-11-18 (routers for Claude Code subtasks): AutoMode https://github.com/mralexivy/AutoMode (risk floor,
cache-rewrite break-even, hidden-test session benchmark); frugal https://github.com/ThomasLangbroek/frugal
(verification gate, budget thermostat, delegation floor); cc-model-router https://github.com/misterkante/cc-model-router
(`--verify` gate with escalation on the failure output); jev-router https://github.com/FrancoisChastel/jev-router
(execution-signal escalation, tier cap at 80/95% of the window, shadow mode and replay); claude-auto-model
https://github.com/danniely/claude-auto-model; NadirClaw https://github.com/NadirRouter/NadirClaw (answer verifier,
fallback chain, budgets). Monitors: subagent-monitor https://github.com/blogchik/subagent-monitor (live transcript),
claude-flightdeck https://github.com/scasella/claude-flightdeck, claude-dashboard https://github.com/uppinote20/claude-dashboard
(burn rate, depletion time, budget alerts), claude-code-observatory https://github.com/vladsawyer/claude-code-observatory
(session replay, anomaly flags), Claude-Code-Agent-Monitor https://github.com/hoangsonww/Claude-Code-Agent-Monitor.
Usage trackers: ccusage https://github.com/ryoppippi/ccusage, Claude-Code-Usage-Monitor
https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor (burn rate, P90 limit inference), ccstatusline
https://github.com/sirmalloc/ccstatusline (block forecast, cache TTL countdown). Gateways: OpenRouter auto router
https://openrouter.ai/docs/features/model-routing, LiteLLM routing https://docs.litellm.ai/docs/routing. Benchmarks:
LLMRouterBench https://arxiv.org/html/2601.07206 (newer than RouterArena). The subagent tax (Systima, 2026-07-22):
https://systima.ai/blog/subagent-tax.


- Cost-of-Pass: https://arxiv.org/abs/2504.13359
- RouterArena (ICLR 2026): https://proceedings.iclr.cc/paper_files/paper/2026/file/4987bb24bc53c198785922d1bd9e18cf-Paper-Conference.pdf
- Anthropic, Demystifying evals for AI agents: https://anthropic.com/engineering/demystifying-evals-for-ai-agents
- Claude Code subagent docs (frontmatter `model`, `effort`, description budget): https://code.claude.com/docs/en/sub-agents
- Terminal-Bench leaderboard: https://www.tbench.ai/leaderboard
- Artificial Analysis (cost per task, effort variants): https://artificialanalysis.ai/
- An Empirical Study of Harness Design for Coding Agents: https://arxiv.org/abs/2609.20804
- Efficient Benchmarking of AI Agents: https://arxiv.org/abs/2603.23749
