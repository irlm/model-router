# Regression check 2026-11-06-claude-2.1.319

Claude Code 2.1.319, sample 6 tasks per family, seed 1, alpha 0.05.

Fixed prefix of a trivial Haiku call (input + cache write + cache read; MCP servers skipped): 39377, 39373 tokens.

| Family | Default | Sample | Successes | Decided rate (95% CI) | P(this few) | Verdict | Cost $ |
|---|---|---|---|---|---|---|---|
| web_research | haiku low | 6 | 0 | 76/78 (0.91-0.99) | 0.00 | REGRESSED | 0.144 |
| research_synthesis | sonnet low | 6 | 5 | 12/12 (0.76-1.00) | 0.81 | ok | 0.955 |
