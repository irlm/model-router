# Regression check 2026-11-02-claude-2.1.316

Claude Code 2.1.316, sample 6 tasks per family, seed 1, alpha 0.05.

Fixed prefix of a trivial Haiku call (input + cache write + cache read; MCP servers skipped): 22693, 22692 tokens.

| Family | Default | Sample | Successes | Decided rate (95% CI) | P(this few) | Verdict | Cost $ |
|---|---|---|---|---|---|---|---|
| find_feature | haiku low | 6 | 6 | 214/216 (0.97-1.00) | 1.00 | ok | 0.019 |
| repo_fix | haiku low +vitest | 6 | 6 | 72/72 (0.95-1.00) | 1.00 | ok | 0.036 |
| web_research | haiku low | 6 | 5 | 76/78 (0.91-0.99) | 0.43 | ok | 0.128 |
