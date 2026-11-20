# Regression check 2026-11-20-claude-2.1.329

Claude Code 2.1.329, sample 6 tasks per family, seed 1, alpha 0.05.

Fixed prefix of a trivial Haiku call (input + cache write + cache read; MCP servers skipped): 24238, 24198 tokens.

| Family | Default | Sample | Successes | Decided rate (95% CI) | P(this few) | Verdict | Cost $ |
|---|---|---|---|---|---|---|---|
| find_feature | haiku low | 6 | 6 | 214/216 (0.97-1.00) | 1.00 | ok | 0.021 |
| repo_fix | haiku low +vitest | 6 | 6 | 72/72 (0.95-1.00) | 1.00 | ok | 0.039 |
| web_research | haiku low | 6 | 5 | 76/78 (0.91-0.99) | 0.43 | ok | 0.140 |
| research_synthesis | sonnet low | 6 | 5 | 12/12 (0.76-1.00) | 0.81 | ok | 0.748 |
