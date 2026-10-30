"""Derive the write-tests tasks from the 10 K2 seeded bugs: same functions,
and each task keeps its verified mutation as the hidden bug the agent's test
must catch. Oracle fields (mutated_function) are never shown to the agent."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = json.loads((HERE.parent / 'fix_bug/tasks.json').read_text())
tasks = []
for t in src['tasks']:
    tasks.append({'id': 'test-' + t['id'].removeprefix('edit-'), 'family': 'write_tests',
                  'file': t['file'], 'function': t['function'],
                  'existing_suite': t['suite'], 'mutation': t['mutation'],
                  'mutated_function': t['mutated_function']})
(HERE / 'tasks.json').write_text(json.dumps({'tree': src['tree'], 'tasks': tasks}, indent=1))
print(len(tasks), 'tasks')
