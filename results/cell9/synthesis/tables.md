Cost column: catalog prices (catalog/models.json).

## Per bench x model x effort x trial

| Bench | Model | Effort | Trial | n | success | rate 95% CI | outcomes | cost total $ | cost / success $ | cost p90 $ | cost max $ | turns mean | turns max | wall mean s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| research_synthesis | claude-fable-5-1 | low | 1 | 6 | 6 | 0.61-1.00 | correct 6 | 3.11 | 0.5191 | 0.5687 | 0.6913 | 9.3 | 15 | 44.0 |
| research_synthesis | claude-fable-5-1 | low | 2 | 6 | 6 | 0.61-1.00 | correct 6 | 3.30 | 0.5501 | 0.5550 | 1.0156 | 9.7 | 19 | 49.8 |
| research_synthesis | claude-haiku-5-5 | low | 1 | 6 | 6 | 0.61-1.00 | correct 6 | 0.22 | 0.0371 | 0.0549 | 0.0557 | 8.2 | 12 | 22.9 |
| research_synthesis | claude-haiku-5-5 | low | 2 | 6 | 5 | 0.44-0.97 | correct 5, right-unsourced 1 | 0.26 | 0.0513 | 0.0530 | 0.0665 | 10.0 | 16 | 38.2 |
| research_synthesis | claude-haiku-5-5 | low | 3 | 6 | 5 | 0.44-0.97 | correct 5, right-unsourced 1 | 0.30 | 0.0602 | 0.0508 | 0.0685 | 10.5 | 18 | 29.9 |
| research_synthesis | claude-opus-5-5 | low | 1 | 6 | 6 | 0.61-1.00 | correct 6 | 1.05 | 0.1752 | 0.1906 | 0.2273 | 6.0 | 9 | 27.1 |
| research_synthesis | claude-opus-5-5 | low | 2 | 6 | 6 | 0.61-1.00 | correct 6 | 1.11 | 0.1856 | 0.1909 | 0.2648 | 6.5 | 10 | 33.9 |
| research_synthesis | claude-sonnet-5-5 | low | 1 | 6 | 6 | 0.61-1.00 | correct 6 | 0.56 | 0.0931 | 0.0974 | 0.1350 | 6.8 | 11 | 23.0 |
| research_synthesis | claude-sonnet-5-5 | low | 2 | 6 | 6 | 0.61-1.00 | correct 6 | 0.56 | 0.0938 | 0.0931 | 0.1454 | 7.0 | 13 | 23.4 |

## find_feature per family

| Model | Effort | Trial | Family | n | correct | outcomes | cost / correct $ | turns mean | wall mean s |
|---|---|---|---|---|---|---|---|---|---|

## Every non-success response

| Bench | Model | Effort | Trial | Task | Outcome | Detail |
|---|---|---|---|---|---|---|
| research_synthesis | claude-haiku-5-5 | low | 2 | rs-03 | right-unsourced | 3: right, no cited page states it |
| research_synthesis | claude-haiku-5-5 | low | 3 | rs-05 | right-unsourced | 3: right, no cited page states it |
