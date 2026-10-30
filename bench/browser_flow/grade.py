"""Grade browser-flow receipts: the agent's pass/fail vector against the truth
vector the scripted user observed. Outcomes: correct | wrong (detail: items
that differ) | unparseable | operational. Also reports `drove`: whether the
app's action log shows the full flow (2 sign-ins, 3 adds, 1 edit, 1 delete,
1 logout), part of it, or nothing. Cheap, so report.py calls it inline.
"""
import json
import re

EXPECTED = {'login': 2, 'add': 3, 'edit': 1, 'delete': 1, 'logout': 1}


def extract_json(text):
    """The first JSON object in the text that has a `results` key. Agents sometimes
    wrap the object in a code fence or add prose after it; that is a format slip,
    not a wrong verdict, so the grader tolerates it."""
    dec = json.JSONDecoder()
    for m in re.finditer(r'\{', text):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict) and 'results' in obj:
            return obj
    raise ValueError('no json')


def drove(state):
    log = (state or {}).get('log') or []
    counts = {k: sum(1 for e in log if e.get('action') == k) for k in EXPECTED}
    if all(counts[k] >= v for k, v in EXPECTED.items()):
        return 'full'
    return 'partial' if any(counts.values()) else 'none'


def grade_one(task, record):
    if record.get('operational_error'):
        return 'operational', record['operational_error']
    try:
        answer = extract_json(record.get('text') or '')
        results = {str(k): str(v).strip().lower() for k, v in (answer.get('results') or {}).items()}
    except (ValueError, AttributeError) as e:
        return 'unparseable', str(e)[:80]
    truth = task['truth']
    wrong = [k for k in truth if results.get(k) != truth[k]]
    if not wrong:
        return 'correct', f'drove={drove(record.get("state"))}'
    said = ','.join(f'{k}:{results.get(k, "?")}' for k in wrong)
    return 'wrong', f'items {said} (truth fails {task["fails"]}) drove={drove(record.get("state"))}'
