# Cell 4: browser flows through the Chrome extension (2026-10-30)

One trial, 11 flows, three models at low effort. The agent gets a URL and a numbered 9-item
checklist and must drive a real Chrome tab through it with the Claude-in-Chrome tools only: no
source, no network or console inspection. It returns one pass/fail per item. Truth comes from a
scripted user (`bench/browser_flow/oracle.py`) that drives the same app over HTTP and records what
it sees. A run is `correct` only when all 9 items match the scripted user. The app's own action log
says whether the agent really did the flow (`drove`: full, partial, none). No judge model.
Receipts: `runs/browser_flow/`; grades: `grades.json`; tables: `tables.md`.

## The tasks (`bench/browser_flow/tasks.json`, made by `make_tasks.py`)

- **App:** `bench/browser_flow/app.py`, Python stdlib, server-rendered HTML. Sign in, a list of
  items with quantity, price, line total and grand total, add, edit, delete, sign out.
- **Defects:** one per run, chosen from 10, plus one clean run: wrong password accepted, wrong user
  shown after sign-in, line total adds instead of multiplies, grand total skips the last row, grand
  total rounds to whole units, empty name accepted, edit not saved, edit loses the name, delete
  removes the wrong row, sign-out keeps the session.
- **Checklist (9 items):** wrong password rejected; sign-in shows "Signed in as tester"; add Pen
  3 x 2.50 = 7.50; add Notebook 1 x 3.25 = 3.25; grand total 10.75; edit Pen quantity to 4 gives
  10.00 and 13.25; delete Notebook leaves Pen and 10.00; empty name is refused with "Name is
  required" and the list is unchanged; sign out returns to the sign-in page and /items no longer
  shows the list.
- **Truth per defect:** the scripted user's fail set, for example line-total-adds fails items 3 to 7
  (the wrong line totals cascade into the grand total, the edit and the delete checks), edit-loses-name
  fails 6 and 7, logout-keeps-session fails only 9, the clean app fails nothing.
- **Each run:** a fresh app on its own port, a fresh headless `claude -p --chrome` session, tools
  limited to tab, navigate, read_page, get_page_text, find, form_input, computer, browser_batch and
  resize_window. Runs are sequential because there is one browser.

## Result

| Model | Correct / 11 | Drove the full flow / 11 | Cost per flow (min to max) | Turns (min to max) | Wall (min to max) | Cache-read tokens per flow | Output tokens per flow |
|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | 11 | 11 | $0.035 ($0.027 to $0.042) | 47 (16 to 57) | 91 s (64 to 162) | 1.53M | 6.5k |
| claude-sonnet-5-5 | 11 | 11 | $0.427 ($0.410 to $0.455) | 41 (20 to 47) | 76 s (55 to 94) | 0.84M | 4.6k |
| claude-fable-5-1 | 10 | 11 | $2.26 ($1.98 to $2.44) | 52 (47 to 67) | 140 s (78 to 216) | 1.52M | 6.3k |

Every model caught every planted defect: on all 33 runs each item the scripted user saw fail was
reported as a fail. The clean app was reported clean by all three. 32 of 33 vectors matched exactly.

## The one miss

Fable, `flow-09-edit-loses-name`. After the edit the Pen row kept its numbers but lost its name.
Fable reported item 6 as fail (correct) and item 7 ("delete Notebook: the Notebook row is gone,
the Pen row remains, grand total 10.00") as pass, with the note that "the same nameless row
persisted through steps 7 and 8". Haiku, Sonnet and the scripted user read "the Pen row remains"
strictly: a row with no name is not the Pen row, so 7 fails too. Fable saw the same screen and
chose the lenient reading. This is a rubric judgement on a cascading item, not a browsing failure;
it is graded `wrong` because the scripted user is the oracle. Item 7 should say "the row named
Pen remains" in v2 of the checklist. The wording was left alone so the three runs stay comparable.

Haiku had two permission denials (a `navigate` to `chrome://newtab/` when closing up, blocked by
the extension). Both runs still finished correct.

## Reading

1. **Haiku equals Sonnet on this family at one twelfth of the cost.** Fable costs 65x Haiku, takes
   50% longer, and was the only tier with a miss. There is nothing here that a bigger model buys.
2. **The cost shape is different from the code families.** A flow is 40 to 50 tool calls, and every
   call re-reads the whole context. Cache reads dominate: for Haiku about 1.5M cache-read tokens
   per flow, roughly $0.015 of the $0.035; the fixed prefix write is about $0.0055. For Fable the
   cache reads alone are about $1.50 of the $2.26. So on browser work, unlike short code tasks,
   tokens per session matter as much as the number of sessions. Both point the same way: Haiku.
3. **The checker is the scripted user, not a model.** That is what makes a cheap tier safe to route
   here: the family has a mechanical oracle, so a regression would show up in a re-run.
4. **Routing decision:** checklist-driven browser flows go to `haiku`, `low`. No step-up and no
   escalation rule: the only miss was on the most expensive tier.

## Limits

- One trial per tier. A second and third Haiku trial cost about $0.40 each and should be run
  before this is treated as a production decision (Anthropic's bar is about 50 cases and 5 trials).
- One small server-rendered app. JavaScript-heavy pages, slow pages, pages that need scrolling or
  drag, and visual judgements from screenshots were not measured. The agents read the DOM through
  `read_page` and `get_page_text`; they did not have to look at pixels.
- The checklist was explicit and numbered. Exploratory testing ("test this page like a user" with
  no list) is a different family and was not measured.
- Scores are ceiling-level for all tiers, so this cell does not rank the models; it only shows that
  the cheapest tier is enough for this shape of task.
