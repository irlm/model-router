# model-router

Which model, at which effort, for which kind of agent work, measured on our own tasks.
The output is a routing strategy per task family that agents read, with the numbers behind it,
re-evaluated when a new model appears and repriced when a price changes.

Status: routing v1 decided 2026-10-30 from three families, see `ROUTING.md`. `results/` holds what has actually run.

## Layout

- `ROUTING.md`, `routing.json`: the decision (model and effort per task family, with the evidence)
  in prose and for scripts. `apply_agents.py` writes it into the agent files' frontmatter (`--revert` undoes).
- `catalog/models.json`: models, API prices, verified date and source. Prices are not in the providers'
  model-list APIs, so a new model is "price unknown" until a human fills it in.
- `catalog/discover.py`: the thing to run after a launch. Lists live models per provider, diffs against the
  catalog, flags new ids, delisted ids and stale prices. Needs `ANTHROPIC_API_KEY` (or the anthropic SDK
  with an `ant auth login` profile) and `OPENAI_API_KEY`; without them it says so and checks only staleness.
- `bench/find_feature/`: the "find a feature in a huge codebase" family. Agent with file and search
  tools inside a pinned Linux v6.12 tree, web off. 48 lexical tasks with string-verified truth plus
  24 semantic tasks with hand-classified truth. Copied from the author's earlier evaluation repository, see `PROVENANCE.md`.
- `runs/`: one receipt per call (`runs-<model>-<effort>-t<trial>.jsonl`). Receipts are the evidence
  and are committed.
- `report.py`: grades every receipt mechanically (no judge model) and prints, per model x effort x
  trial and per family: outcomes, API-equivalent cost per correct task, p90 and max cost per task,
  turns and wall time.
- `results/<cell>/`: the tables and a short reading of each cell.

## Run a cell

```bash
cd bench/find_feature
python3 run_agent.py --model claude-haiku-5-5 --effort low     # all 72 tasks, receipts in ../../runs
python3 run_agent.py --model claude-sonnet-5-5 --effort low --ids exists-real-01 callers-01   # smoke
cd ../.. && python3 report.py --out results/cell1
```

## Caveats

- The `claude` CLI here is logged in with a claude.ai subscription. Its `cost_usd` is the
  API-equivalent price of the tokens used, not a bill. The ranking between models is still valid;
  the dollars are what an API key would pay.
- One trial per cell is a calibration, not a decision. Anthropic's bar for a production cutover is
  about 50 cases and 5 trials per configuration.
- The fixed Claude Code prefix (system prompt, tools, the user's agent list) is identical across
  models and is part of every receipt. That is the real workload, so it stays in.
