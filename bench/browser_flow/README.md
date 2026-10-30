# Family: drive a web page through a checklist in a real browser

The agent gets a URL and a numbered checklist and must act like a careful end user in a real
Chrome tab, through the Claude-in-Chrome extension tools, then report pass or fail per item.
The app has one planted defect per run; a scripted user computes the truth; the grade is an exact
match of the two vectors. Results and reading: `results/cell4/README.md`.

## Pieces

- `app.py`: stdlib `ThreadingHTTPServer` app. Sign in (`tester` / `letmein`), item list with
  quantity, price, line and grand totals, add, edit, delete, sign out. `--defect NAME` plants one
  of 10 defects (`DEFECTS` at the top of the file). `GET /__state` exposes the defect, the items,
  the sessions and an action log for the grader; `POST /__reset` clears state.
- `oracle.py`: the scripted user. Drives the 9-item `CHECKLIST` over HTTP with a cookie jar and
  numeric comparison, returns `{'1': 'pass'|'fail', ...}`.
- `make_tasks.py` writes `tasks.json`: the checklist, the credentials, and one task per defect
  (plus `none`) with the oracle's truth vector and fail list.
- `run_agent.py`: for each task, starts the app on its own port (8800 + n), runs one headless
  `claude -p --chrome --output-format json` session with the prompt (URL plus checklist, JSON
  answer demanded), and writes a receipt with the answer text, the app's final state and log,
  usage, cost, turns, wall time and permission denials. Tools are the extension's tab, navigate,
  read, find, form and click tools; the JavaScript, network and console tools are excluded so
  the agent cannot read the truth out of the app. Sequential: one shared browser. Resumable.

  ```
  python3 bench/browser_flow/run_agent.py --model claude-haiku-5-5 --effort low [--trial 1]
  ```

- `grade.py`: `correct` when all items match the truth, `wrong` (with the mismatched items),
  `unparseable`, `operational`. Also `drove` from the app log: `full` needs 2 sign-ins, 3 adds,
  1 edit, 1 delete, 1 sign-out. Cheap, so `report.py` grades inline.

## Requirements

- Chrome with the Claude in Chrome extension connected, and the `claude` CLI logged in.
  `--chrome` works in headless `-p` sessions; a site permission for 127.0.0.1 was not needed.
- Do not use the browser for anything else while a run is going: the runs share it.

## Known limits

- Server-rendered HTML, no JavaScript, no scrolling, no screenshots needed: the agents read the
  DOM as text. Visual judgement and dynamic pages are not measured.
- The checklist is explicit. Exploratory testing without a list is a different family.
- Checklist item 7 ("the Pen row remains") is ambiguous once a defect blanks the name; the
  scripted user reads it strictly. Say "the row named Pen" in a v2 checklist.
