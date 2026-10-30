## Overall, per model x effort x trial

| Model | Effort | Trial | n | correct | wrong | abst | hall | unp | op | cost total $ | cost / correct $ | cost p90 $ | cost max $ | turns mean | turns max | wall mean s | wall total s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5-1 | low | 1 | 72 | 72 | 0 | 0 | 0 | 0 | 0 | 41.61 | 0.5779 | 0.5978 | 0.6009 | 2.5 | 5 | 8.3 | 601 |
| claude-haiku-5-5 | low | 1 | 72 | 70 | 2 | 0 | 0 | 0 | 0 | 0.47 | 0.0067 | 0.0070 | 0.0075 | 2.8 | 7 | 6.2 | 449 |
| claude-sonnet-5-5 | low | 1 | 72 | 72 | 0 | 0 | 0 | 0 | 0 | 8.58 | 0.1192 | 0.1236 | 0.1412 | 2.4 | 5 | 6.0 | 432 |

## Per family

| Model | Effort | Trial | Family | n | correct | wrong | abst | hall | unp | op | cost / correct $ | cost p90 $ | turns mean | wall mean s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5-1 | low | 1 | callers | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.5916 | 0.5990 | 4.2 | 8.8 |
| claude-fable-5-1 | low | 1 | dispatch | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.5740 | 0.5937 | 2.2 | 6.8 |
| claude-fable-5-1 | low | 1 | exists | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 0.5731 | 0.5888 | 2.3 | 8.6 |
| claude-fable-5-1 | low | 1 | fields | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.5785 | 0.6005 | 2.2 | 8.2 |
| claude-fable-5-1 | low | 1 | refs | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.5772 | 0.5849 | 2.0 | 9.0 |
| claude-haiku-5-5 | low | 1 | callers | 12 | 11 | 1 | 0 | 0 | 0 | 0 | 0.0072 | 0.0071 | 3.9 | 6.3 |
| claude-haiku-5-5 | low | 1 | dispatch | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.0066 | 0.0070 | 2.7 | 5.9 |
| claude-haiku-5-5 | low | 1 | exists | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 0.0065 | 0.0069 | 2.5 | 6.4 |
| claude-haiku-5-5 | low | 1 | fields | 12 | 11 | 1 | 0 | 0 | 0 | 0 | 0.0071 | 0.0070 | 2.3 | 5.7 |
| claude-haiku-5-5 | low | 1 | refs | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.0065 | 0.0069 | 2.9 | 6.7 |
| claude-sonnet-5-5 | low | 1 | callers | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.1189 | 0.1232 | 2.2 | 6.0 |
| claude-sonnet-5-5 | low | 1 | dispatch | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.1216 | 0.1292 | 2.8 | 6.3 |
| claude-sonnet-5-5 | low | 1 | exists | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 0.1177 | 0.1216 | 2.4 | 5.7 |
| claude-sonnet-5-5 | low | 1 | fields | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.1187 | 0.1246 | 2.2 | 5.9 |
| claude-sonnet-5-5 | low | 1 | refs | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0.1204 | 0.1238 | 2.4 | 6.3 |

## Every non-correct response

| Model | Effort | Trial | Task | Outcome | Detail |
|---|---|---|---|---|---|
| claude-haiku-5-5 | low | 1 | fields-06 | wrong |  |
| claude-haiku-5-5 | low | 1 | callers-10 | wrong | lexical-confusion: lib/string_helpers.c has only definition |
