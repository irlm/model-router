# Regression check 2026-11-08-claude-2.1.319

Claude Code 2.1.319, sample 6 tasks per family, seed 1, alpha 0.05.

Fixed prefix of a trivial Haiku call (input + cache write + cache read; MCP servers skipped): 26227, 26227 tokens.

| Family | Default | Sample | Successes | Decided rate (95% CI) | P(this few) | Verdict | Cost $ |
|---|---|---|---|---|---|---|---|
| web_research | haiku low | 6 | 6 | 76/78 (0.91-0.99) | 1.00 | ok | 0.118 |


