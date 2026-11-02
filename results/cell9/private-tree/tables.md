Cost column: catalog prices (catalog/models.json).

## Per bench x model x effort x trial

| Bench | Model | Effort | Trial | n | success | rate 95% CI | outcomes | cost total $ | cost / success $ | cost p90 $ | cost max $ | turns mean | turns max | wall mean s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| find_feature_private | claude-fable-5-1 | low | 1 | 21 | 21 | 0.85-1.00 | correct 21 | 5.71 | 0.2717 | 0.2857 | 0.3441 | 2.1 | 3 | 6.9 |
| find_feature_private | claude-haiku-5-5 | low | 1 | 21 | 21 | 0.85-1.00 | correct 21 | 0.07 | 0.0032 | 0.0035 | 0.0047 | 2.2 | 3 | 5.0 |
| find_feature_private | claude-haiku-5-5 | low | 2 | 21 | 21 | 0.85-1.00 | correct 21 | 0.02 | 0.0009 | 0.0012 | 0.0028 | 2.2 | 5 | 4.8 |
| find_feature_private | claude-haiku-5-5 | low | 3 | 21 | 21 | 0.85-1.00 | correct 21 | 0.02 | 0.0010 | 0.0017 | 0.0027 | 2.2 | 4 | 4.9 |
| find_feature_private | claude-opus-5-5 | low | 1 | 21 | 21 | 0.85-1.00 | correct 21 | 2.34 | 0.1116 | 0.1220 | 0.1251 | 2.0 | 3 | 5.6 |
| find_feature_private | claude-sonnet-5-5 | low | 1 | 21 | 21 | 0.85-1.00 | correct 21 | 1.20 | 0.0573 | 0.0632 | 0.0644 | 2.3 | 4 | 5.0 |

## find_feature per family

| Model | Effort | Trial | Family | n | correct | outcomes | cost / correct $ | turns mean | wall mean s |
|---|---|---|---|---|---|---|---|---|---|

## Every non-success response

| Bench | Model | Effort | Trial | Task | Outcome | Detail |
|---|---|---|---|---|---|---|
