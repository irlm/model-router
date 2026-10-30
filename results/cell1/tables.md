## Per bench x model x effort x trial

| Bench | Model | Effort | Trial | n | success | outcomes | cost total $ | cost / success $ | cost p90 $ | cost max $ | turns mean | turns max | wall mean s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| find_feature | claude-fable-5-1 | low | 1 | 72 | 72 | correct 72 | 41.61 | 0.5779 | 0.5978 | 0.6009 | 2.5 | 5 | 8.3 |
| find_feature | claude-haiku-5-5 | low | 1 | 72 | 70 | correct 70, wrong 2 | 0.47 | 0.0067 | 0.0070 | 0.0075 | 2.8 | 7 | 6.2 |
| find_feature | claude-haiku-5-5 | low | 2 | 72 | 72 | correct 72 | 0.29 | 0.0040 | 0.0068 | 0.0080 | 3.1 | 7 | 6.4 |
| find_feature | claude-haiku-5-5 | low | 3 | 72 | 72 | correct 72 | 0.23 | 0.0031 | 0.0064 | 0.0071 | 3.1 | 10 | 6.5 |
| find_feature | claude-haiku-5-5 | medium | 1 | 72 | 72 | correct 72 | 0.47 | 0.0065 | 0.0071 | 0.0092 | 3.2 | 7 | 6.8 |
| find_feature | claude-haiku-5-5 | medium | 2 | 72 | 70 | correct 70, wrong 2 | 0.29 | 0.0041 | 0.0068 | 0.0078 | 3.0 | 10 | 6.8 |
| find_feature | claude-haiku-5-5 | medium | 3 | 72 | 71 | correct 71, wrong 1 | 0.45 | 0.0063 | 0.0069 | 0.0079 | 2.9 | 5 | 6.6 |
| find_feature | claude-sonnet-5-5 | low | 1 | 72 | 72 | correct 72 | 8.58 | 0.1192 | 0.1236 | 0.1412 | 2.4 | 5 | 6.0 |
| find_feature | claude-sonnet-5-5 | low | 2 | 72 | 72 | correct 72 | 8.31 | 0.1154 | 0.1189 | 0.1265 | 2.3 | 6 | 6.3 |
| fix_bug | claude-fable-5-1 | low | 1 | 2 | 0 | ungraded 2 | 1.25 | - | 0.6285 | 0.6285 | 3.0 | 3 | 10.0 |
| fix_bug | claude-haiku-5-5 | low | 1 | 2 | 0 | ungraded 2 | 0.02 | - | 0.0080 | 0.0080 | 3.5 | 4 | 8.9 |
| fix_bug | claude-sonnet-5-5 | low | 1 | 2 | 0 | ungraded 2 | 0.26 | - | 0.1300 | 0.1300 | 3.0 | 3 | 8.0 |

## find_feature per family

| Model | Effort | Trial | Family | n | correct | outcomes | cost / correct $ | turns mean | wall mean s |
|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5-1 | low | 1 | callers | 12 | 12 | correct 12 | 0.5916 | 4.2 | 8.8 |
| claude-fable-5-1 | low | 1 | dispatch | 12 | 12 | correct 12 | 0.5740 | 2.2 | 6.8 |
| claude-fable-5-1 | low | 1 | exists | 24 | 24 | correct 24 | 0.5731 | 2.3 | 8.6 |
| claude-fable-5-1 | low | 1 | fields | 12 | 12 | correct 12 | 0.5785 | 2.2 | 8.2 |
| claude-fable-5-1 | low | 1 | refs | 12 | 12 | correct 12 | 0.5772 | 2.0 | 9.0 |
| claude-haiku-5-5 | low | 1 | callers | 12 | 11 | correct 11, wrong 1 | 0.0072 | 3.9 | 6.3 |
| claude-haiku-5-5 | low | 1 | dispatch | 12 | 12 | correct 12 | 0.0066 | 2.7 | 5.9 |
| claude-haiku-5-5 | low | 1 | exists | 24 | 24 | correct 24 | 0.0065 | 2.5 | 6.4 |
| claude-haiku-5-5 | low | 1 | fields | 12 | 11 | correct 11, wrong 1 | 0.0071 | 2.3 | 5.7 |
| claude-haiku-5-5 | low | 1 | refs | 12 | 12 | correct 12 | 0.0065 | 2.9 | 6.7 |
| claude-haiku-5-5 | low | 2 | callers | 12 | 12 | correct 12 | 0.0034 | 4.7 | 6.5 |
| claude-haiku-5-5 | low | 2 | dispatch | 12 | 12 | correct 12 | 0.0041 | 2.8 | 6.8 |
| claude-haiku-5-5 | low | 2 | exists | 24 | 24 | correct 24 | 0.0040 | 2.9 | 6.9 |
| claude-haiku-5-5 | low | 2 | fields | 12 | 12 | correct 12 | 0.0059 | 2.2 | 5.4 |
| claude-haiku-5-5 | low | 2 | refs | 12 | 12 | correct 12 | 0.0027 | 3.2 | 6.3 |
| claude-haiku-5-5 | low | 3 | callers | 12 | 12 | correct 12 | 0.0026 | 4.6 | 6.5 |
| claude-haiku-5-5 | low | 3 | dispatch | 12 | 12 | correct 12 | 0.0035 | 2.3 | 6.2 |
| claude-haiku-5-5 | low | 3 | exists | 24 | 24 | correct 24 | 0.0027 | 2.7 | 6.9 |
| claude-haiku-5-5 | low | 3 | fields | 12 | 12 | correct 12 | 0.0039 | 2.2 | 5.2 |
| claude-haiku-5-5 | low | 3 | refs | 12 | 12 | correct 12 | 0.0034 | 3.9 | 7.1 |
| claude-haiku-5-5 | medium | 1 | callers | 12 | 12 | correct 12 | 0.0066 | 4.2 | 7.0 |
| claude-haiku-5-5 | medium | 1 | dispatch | 12 | 12 | correct 12 | 0.0064 | 2.7 | 6.0 |
| claude-haiku-5-5 | medium | 1 | exists | 24 | 24 | correct 24 | 0.0066 | 2.9 | 7.4 |
| claude-haiku-5-5 | medium | 1 | fields | 12 | 12 | correct 12 | 0.0065 | 2.3 | 5.6 |
| claude-haiku-5-5 | medium | 1 | refs | 12 | 12 | correct 12 | 0.0066 | 3.8 | 7.3 |
| claude-haiku-5-5 | medium | 2 | callers | 12 | 12 | correct 12 | 0.0023 | 3.1 | 7.0 |
| claude-haiku-5-5 | medium | 2 | dispatch | 12 | 12 | correct 12 | 0.0043 | 2.5 | 5.9 |
| claude-haiku-5-5 | medium | 2 | exists | 24 | 24 | correct 24 | 0.0048 | 2.9 | 7.5 |
| claude-haiku-5-5 | medium | 2 | fields | 12 | 12 | correct 12 | 0.0035 | 2.2 | 5.2 |
| claude-haiku-5-5 | medium | 2 | refs | 12 | 10 | correct 10, wrong 2 | 0.0051 | 4.6 | 7.7 |
| claude-haiku-5-5 | medium | 3 | callers | 12 | 12 | correct 12 | 0.0065 | 3.5 | 7.2 |
| claude-haiku-5-5 | medium | 3 | dispatch | 12 | 12 | correct 12 | 0.0064 | 2.6 | 6.6 |
| claude-haiku-5-5 | medium | 3 | exists | 24 | 24 | correct 24 | 0.0059 | 2.7 | 6.7 |
| claude-haiku-5-5 | medium | 3 | fields | 12 | 11 | correct 11, wrong 1 | 0.0070 | 2.4 | 5.6 |
| claude-haiku-5-5 | medium | 3 | refs | 12 | 12 | correct 12 | 0.0064 | 3.3 | 6.6 |
| claude-sonnet-5-5 | low | 1 | callers | 12 | 12 | correct 12 | 0.1189 | 2.2 | 6.0 |
| claude-sonnet-5-5 | low | 1 | dispatch | 12 | 12 | correct 12 | 0.1216 | 2.8 | 6.3 |
| claude-sonnet-5-5 | low | 1 | exists | 24 | 24 | correct 24 | 0.1177 | 2.4 | 5.7 |
| claude-sonnet-5-5 | low | 1 | fields | 12 | 12 | correct 12 | 0.1187 | 2.2 | 5.9 |
| claude-sonnet-5-5 | low | 1 | refs | 12 | 12 | correct 12 | 0.1204 | 2.4 | 6.3 |
| claude-sonnet-5-5 | low | 2 | callers | 12 | 12 | correct 12 | 0.1163 | 2.8 | 6.3 |
| claude-sonnet-5-5 | low | 2 | dispatch | 12 | 12 | correct 12 | 0.1156 | 2.3 | 6.4 |
| claude-sonnet-5-5 | low | 2 | exists | 24 | 24 | correct 24 | 0.1146 | 2.3 | 6.3 |
| claude-sonnet-5-5 | low | 2 | fields | 12 | 12 | correct 12 | 0.1158 | 2.2 | 6.1 |
| claude-sonnet-5-5 | low | 2 | refs | 12 | 12 | correct 12 | 0.1153 | 2.1 | 6.1 |

## Every non-success response

| Bench | Model | Effort | Trial | Task | Outcome | Detail |
|---|---|---|---|---|---|---|
| find_feature | claude-haiku-5-5 | low | 1 | fields-06 | wrong |  |
| find_feature | claude-haiku-5-5 | low | 1 | callers-10 | wrong | lexical-confusion: lib/string_helpers.c has only definition |
| find_feature | claude-haiku-5-5 | medium | 2 | refs-05 | wrong |  |
| find_feature | claude-haiku-5-5 | medium | 2 | refs-10 | wrong |  |
| find_feature | claude-haiku-5-5 | medium | 3 | fields-06 | wrong |  |
| fix_bug | claude-fable-5-1 | low | 1 | edit-string-01-strncasecmp | ungraded |  |
| fix_bug | claude-fable-5-1 | low | 1 | edit-string-02-strcspn | ungraded |  |
| fix_bug | claude-haiku-5-5 | low | 1 | edit-string-01-strncasecmp | ungraded |  |
| fix_bug | claude-haiku-5-5 | low | 1 | edit-string-02-strcspn | ungraded |  |
| fix_bug | claude-sonnet-5-5 | low | 1 | edit-string-01-strncasecmp | ungraded |  |
| fix_bug | claude-sonnet-5-5 | low | 1 | edit-string-02-strcspn | ungraded |  |
