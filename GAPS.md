# What is still open (2026-11-09)

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

- Cost-of-Pass: https://arxiv.org/abs/2504.13359
- RouterArena (ICLR 2026): https://proceedings.iclr.cc/paper_files/paper/2026/file/4987bb24bc53c198785922d1bd9e18cf-Paper-Conference.pdf
- Anthropic, Demystifying evals for AI agents: https://anthropic.com/engineering/demystifying-evals-for-ai-agents
- Claude Code subagent docs (frontmatter `model`, `effort`, description budget): https://code.claude.com/docs/en/sub-agents
- Terminal-Bench leaderboard: https://www.tbench.ai/leaderboard
- Artificial Analysis (cost per task, effort variants): https://artificialanalysis.ai/
- An Empirical Study of Harness Design for Coding Agents: https://arxiv.org/abs/2609.20804
- Efficient Benchmarking of AI Agents: https://arxiv.org/abs/2603.23749
