# Missing spots (2026-10-31)

**Status 2026-11-01:** items 1-9 below are done or have a first measurement; see `results/cell8`.
1 pruned (prefix 40k -> 23k tokens, `results/prefix`); 2 done on a private TypeScript repo with the effort sweep
(Opus and Fable fix 24/24 at low, high and xhigh; xhigh costs 1.3-1.5x low; Haiku low with the runner
72/72 at 1/70 of Fable); 3 `tools/ledger.sh` with the first entry (the monthly systemd user timer from
`tools/install_ledger_timer.sh` is installed since 2026-11-01 on the user's request; first run verified under systemd); 4 `bench/web_research` with a
citation checker and live-version questions (Haiku 76/78 at 1/17 of Fable xhigh); the rubric part
is still open; 5 Wilson intervals and pass^k in `report.py`/`decide.py`, `--rule lower` default;
6 `regress.py` is the regression suite, the new families are the capability tier (both still at the
ceiling for every Claude tier, so they admit, they do not rank); 7 one paraphrase on repo_fix (no
effect); 8 repo_fix is on a private tree; 9 `regress.py` records the Claude Code version and the
prefix, and the binary did update from 2.1.314 to 2.1.316 during the day.

**Status 2026-11-02:** the repository is generic and public, with the author's own fixtures kept local
(`local/README.md`); the widget (`mod/`, 0.7.x) installs with one line, reads the install's own clone, routes
each Agent call per family (ask, auto, off), and shows the rate-limit windows, the 30-day consumption, the
suggestions with their evidence, and what each recorded change really saved (per unit of the same work,
in its own window, with the family's regression verdict beside it). Item 11 is closed by that, item 12 is
now measurable instead of asserted. Still open, in the order worth doing: (1) a synthesis rubric family,
the largest unmeasured subagent spend on every machine seen so far; (4) a capability tier with tasks in
the 30 to 70% band, so a new model can be ranked; (5) contamination control on a private tree for
find_feature; (6) paraphrases per family; (7) harness ablation; (8) the price of a wrong answer, measured;
(9) browser work as the agent file describes it; (10) the Codex runner arm, only with the user's say.
Also open: a macOS install check (Linux and Windows are verified), and a license file for the public repo.

What this benchmark does not cover, what the public ones do not cover, and what to do first.
Grounded in two things: a scan of this machine's own Claude Code transcripts
(`tools/usage_scan.py`, September to October 2026) and the public work listed at the end.

## What the usage scan says

- **Subagents are rare here.** 33 subagent calls in two months of interactive sessions:
  29 `general-purpose`, 3 `Explore`, 1 `Product Manager`. About 20 of the 33 are web research
  and synthesis (product research, "deep dive", "research X"), 5 are design critiques, 2 write a
  report, 2 write code, 3 map a codebase.
- **The four routed agents were never called.** None of the 184 custom agent files was used,
  except `Product Manager` once. The routing applied so far saves nothing today.
- **The money is in main sessions.** Catalog-equivalent cost, September to October: Fable 5.1
  main sessions $575, Opus 5.5 main sessions $364, all subagent transcripts together $83, the
  benchmark's own runs $300. Cache reads dominate every row (for Fable in September, 638M
  cache-read tokens against 1.4M output tokens): interactive cost is context size times turns.
- **Every request carries 184 agent descriptions**, about 10k tokens of descriptions and 17k as
  rendered (`results/cell1/PREFIX.md`), for agents that are not used. Claude Code warns above
  15k. Removing them is a saving on every session, without any measurement.
- The `effort` frontmatter field is real (Claude Code docs, and the 2.1.314 binary carries it) and
  no environment variable overrides it here, so what `apply_agents.py` writes does take effect.

## What this benchmark misses

1. **The families people here actually run.** Web research and synthesis, critique, report
   writing. None has a code checker. They need rubric or pairwise graders calibrated against a
   human read, which Anthropic's eval guidance treats as normal, and this repo has avoided.
2. **Main-session work.** Over 90% of spend. No family measures Fable 5.1 or Opus 5.5 at low
   versus xhigh effort on the user's own repos (.NET, TypeScript with
   vitest, Rust with 213 tests, Go). The assumption that the Linux C
   results transfer to other languages is untested.
3. **Statistics.** Rates without confidence intervals; a fixed 0.02 margin instead of an interval;
   no pass^k (all-trials-pass) per task, which is the number that matters for consistency.
4. **Saturation.** Every family sits at 100% for every model, so the benchmark cannot rank
   models; it can only say that the cheapest is enough. Tasks with 30 to 70% pass rates are what
   rank models (Efficient Benchmarking of AI Agents). The saturated families should become a
   regression suite that is not re-run on every new model.
5. **Contamination.** Linux v6.12 is in every model's training data. The find-feature truth is
   memorisable; the mutated bugs less so. No control on a private tree.
6. **Prompt robustness.** One prompt per family. Cell 7 showed a wording effect on the callers
   tasks. No paraphrases, so the spread is unknown.
7. **Harness ablation.** The prefix was measured once and never varied (agents removed,
   `omitClaudeMd`, fewer tools). The harness-design study found context management and action
   space move cost materially.
8. **Cost of being wrong.** The step-up rule prices a wrong answer at "18x a session" by
   assertion, not measurement.
9. **Browser work as the agent file describes it.** Screenshots, visual judgement, exploratory
   testing: unmeasured. The agent it is applied to is unused anyway.
10. **The Codex runner arm** cannot run inside Codex's sandbox (ptrace); only with full access.
11. **No ledger, no re-check trigger.** Nothing tracks what the routing saved, and nothing
    re-runs a smoke when Claude Code updates and the prefix changes.
12. **The benchmark cost more than it saved.** $300 equivalent to run, $0 saved so far.

## What the public work misses, and this repo has

- **Leaderboards** (Terminal-Bench, Artificial Analysis, HAL) now publish cost per task, tokens,
  model-plus-harness pairs and confidence intervals, and Artificial Analysis lists effort
  variants. They measure their tasks on their harness. They cannot know this machine's 95k-token
  prefix, which sets the cost floor on short tasks, or whether a test runner is in the loop.
- **Cost-of-Pass** formalises the metric used here (expected cost of a correct answer, with a
  frontier across models) on question-answer datasets. No agent loop, no harness, no runner
  ablation.
- **Routers** (RouteLLM, Not Diamond, Martian; RouterArena as the neutral benchmark) are
  per-query classifiers on single-turn questions, ranked by accuracy against cost per 1k queries.
  RouterArena found no router best on all metrics and the commercial ones over-picking expensive
  models. A router cannot see your checker, and Claude Code offers no per-call router hook: model
  and effort are per agent file or per invocation.
- **Anthropic's own guidance** says "use Haiku for simple subagent tasks" and gives no rule for
  which tasks. This repo has a rule with numbers, and the runner finding (write-tests 4/10 to
  10/10 on Fable once the runner is in the loop) at a size nobody publishes.

## What to do, in order

1. **Remove the unused agent files from `~/.claude/agents`** (keep the few in use). No
   measurement needed; it cuts every request on every session. Reversible.
2. **Build one family on a real repo and run the effort sweep on the main models.**
   the TypeScript repo (vitest) or the Rust one (cargo test): mutate, give the agent the failing
   test, compare Opus 5.5 and Fable 5.1 at low, high and xhigh. This measures the lever that
   drives the bill and tests the transfer assumption at once.
3. **Keep `tools/usage_scan.py` as the ledger.** Run it monthly; the routing table should be
   checked against what actually ran, and the benchmark's own cost should be visible.
4. **Measure the family that is actually used: web research.** A code-graded citation check
   (each claim's URL must resolve and contain the claim) plus a rubric grader calibrated on a
   dozen hand-read reports; Sonnet and Haiku against Fable.
5. **Add Wilson intervals and pass^k to `report.py` and `decide.py`**, and let the interval,
   not a fixed margin, set the bar.
6. **Retire the saturated cells into a regression suite** and add a capability tier with tasks
   in the 30 to 70% band, so a new model can be ranked, not just admitted.
7. **Two paraphrases per family prompt**, reported as a spread.
8. **Contamination control:** find-feature tasks on a private repo.
9. **A smoke on Claude Code updates**, since the prefix and the tool set change with the binary.

## Sources

- Cost-of-Pass: https://arxiv.org/abs/2504.13359
- RouterArena (ICLR 2026): https://proceedings.iclr.cc/paper_files/paper/2026/file/4987bb24bc53c198785922d1bd9e18cf-Paper-Conference.pdf
- Anthropic, Demystifying evals for AI agents: https://anthropic.com/engineering/demystifying-evals-for-ai-agents
- Claude Code subagent docs (frontmatter `model`, `effort`, description budget): https://code.claude.com/docs/en/sub-agents
- Terminal-Bench leaderboard: https://www.tbench.ai/leaderboard
- Artificial Analysis (cost per task, effort variants): https://artificialanalysis.ai/
- An Empirical Study of Harness Design for Coding Agents: https://arxiv.org/abs/2609.20804
- Efficient Benchmarking of AI Agents: https://arxiv.org/abs/2603.23749
