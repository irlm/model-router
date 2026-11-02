# Regression check 2026-11-02-claude-mise

Claude Code mise, sample 6 tasks per family, seed 1, alpha 0.05.

Fixed prefix of a trivial Haiku call (input + cache write + cache read; MCP servers skipped): None, None tokens.

| Family | Default | Sample | Successes | Decided rate (95% CI) | P(this few) | Verdict | Cost $ |
|---|---|---|---|---|---|---|---|
| find_feature | haiku low | 0 | 0 | - | - | nothing judged | 0.000 |
| repo_fix | haiku low +vitest | 0 | 0 | - | - | nothing judged | 0.000 |
| web_research | haiku low | 0 | 0 | - | - | nothing judged | 0.000 |
