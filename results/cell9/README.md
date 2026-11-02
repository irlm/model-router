# Cell 9: research notes, a private tree, a paraphrase, the prefix under five settings (2026-11-02)

Four measurements in one afternoon, about $20 catalog-equivalent in all. Receipts: `runs/research_synthesis/`
(committed), `runs/find_feature_private/` (local: it names files of a private repository),
`runs/regress/2026-11-02-claude-2.1.316-pb/` (committed), `results/prefix/ablation-2026-11-02.md`.
Tables: `synthesis/tables.md`, `private-tree/tables.md` (from `report.py`).

## 1. Research notes: a new family (`bench/research_synthesis`)

The largest unmeasured class of subagent work on both machines seen so far (research reports: $72 here
and $55 on a second machine in 30 days). Six briefs, each made of three of `bench/web_research`'s
fixed-truth questions (PostgreSQL limits and defaults, TLS and DNS, Lambda, Kubernetes, Docker, vitest,
the kernel's Rust version): "write a 250-700 word note for a colleague who is <doing X>, answer these three
questions from the web, put the page you read after each claim, then a JSON of answers and sources".
Graded in code with the web_research checker: every answer must match its pattern and a cited page must
fetch and state it; the note must be prose of 200 to 1000 words. What is not judged: the quality of the
prose beyond that. Prompt variant `b` exists for the paraphrase check.

| model, effort | trials | judged | correct | rate (95% CI) | $ per success | wall |
|---|---|---|---|---|---|---|
| haiku low | 3 | 18 | 16 | 0.889 (0.67-0.97) | 0.049 | 30 s |
| **sonnet low** | 2 | 12 | 12 | 1.000 (0.76-1.00) | **0.094** | 23 s |
| opus low | 2 | 12 | 12 | 1.000 (0.76-1.00) | 0.180 | 31 s |
| fable low | 2 | 12 | 12 | 1.000 (0.76-1.00) | 0.535 | 47 s |

Decision (`decide.py --rule lower`): **sonnet low**. The bar is the best lower bound minus 0.02
(0.7575 - 0.02 = 0.7375); Haiku's lower bound is 0.67. Haiku's two misses were not wrong facts: the third
claim was right, but the page cited for it did not state it (`right-unsourced`), the failure mode
web_research watches too. Sonnet writes a sourced note at 1/5.7 of Fable's cost and 1/1.9 of Opus's.

The widget routes research prompts (general-purpose calls whose prompt reads as research, compare,
report, deep dive) to sonnet low in ask or auto mode, and the research-notes suggestion is now
measured. The prose judge stays open (GAPS 1): a rubric calibrated against a human read.

## 2. find_feature on a private tree: the contamination control

The Linux tree is in every model's training data. `bench/find_feature/private_tree.py make` built
21 tasks on the author's private TypeScript repository (85 source files): 8 `exists` on real exported
functions, 5 on names that exist nowhere, 8 `refs` (which of six candidate files call the function),
truth made by a word search, nothing hand-classified. Same prompt shape as the kernel tasks, read-only
tools, no web.

| model, effort | trials | judged | correct | $ per task | kernel find_feature for comparison |
|---|---|---|---|---|---|
| haiku low | 3 | 63 | 63 | 0.001-0.003 | 214/216 at 0.0046 |
| sonnet low | 1 | 21 | 21 | 0.057 | |
| opus low | 1 | 21 | 21 | 0.112 | |
| fable low | 1 | 21 | 21 | 0.272 | |

No contamination effect: on code no model has seen, every tier finds every function, and Haiku does it
at the same cost as on the kernel. The lexical families are solved by search, not memory, and the cost
ranking that decided find_feature stands. Tasks, receipts and grades stay local (`.gitignore`); only
these counts are committed.

## 3. Paraphrase: the prompt-robustness check (web_research)

`regress.py --prompt-variant b` runs a family's regression sample on a reworded prompt. Same six
questions (seed 1) as the morning's check, Haiku low:

| prompt | correct | cost | verdict against the decided 76/78 |
|---|---|---|---|
| a (the measured one) | 5/6 | $0.128 | ok (P 0.43) |
| b (reworded) | 6/6 | $0.107 | ok (P 1.00) |

One question of spread, inside the decided interval. research_synthesis and repo_fix carry a prompt
`b` as well; cell 8 found no wording effect on repo_fix.

## 4. The prefix under five harness settings (`tools/prefix_ablation.py`)

Input tokens of a one-turn Haiku call, two calls per setting, nothing else running:

| setting | tokens | against the baseline |
|---|---|---|
| baseline (Read only, MCP off, empty cwd) | 22,688 | |
| every tool allowed | 22,688 | +0 |
| MCP on, as configured on this machine (the Docs connector) | 24,614 | +1,926 |
| a 500-word CLAUDE.md in the cwd | 23,488 | +800 |
| the six agent files moved aside | 22,151 | -538 |

Restricting tools changes nothing in the prompt (the allow-list filters use). The MCP connector is the
largest variable left, 1.9k tokens on every request; a CLAUDE.md costs about 1.6 tokens per word on
every request; the six remaining agent files cost 538 (the 184 before pruning cost about 17k,
`results/prefix`). Every short task pays this floor; that is why cost per success on 20-second tasks
is dominated by the prefix, not by the answer.

## Cost of this cell

Research notes $10.5, private tree $9.4, paraphrase $0.1, ablation about $0.02: about $20
catalog-equivalent, on a subscription.
