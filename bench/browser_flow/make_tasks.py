"""Build tasks.json for the browser-flow family: one task per planted defect
plus the control, each with the truth vector the scripted user (oracle.py)
observes against the real app. Usage: python3 make_tasks.py [--port 8790]
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import app as APP  # noqa: E402
import oracle  # noqa: E402


def start_app(port, defect):
    proc = subprocess.Popen([sys.executable, str(HERE / 'app.py'), '--port', str(port), '--defect', defect],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(50):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/__state', timeout=1).read()
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError(f'app did not start on {port}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8790)
    ap.add_argument('--out', type=Path, default=HERE / 'tasks.json')
    args = ap.parse_args()
    tasks = []
    for n, defect in enumerate(APP.DEFECTS, 1):
        proc = start_app(args.port, defect)
        try:
            truth = oracle.run_checklist(f'http://127.0.0.1:{args.port}')
        finally:
            proc.kill()
            proc.wait()
        fails = [k for k, v in truth.items() if v == 'fail']
        assert (defect == 'none') == (not fails), f'{defect}: fails={fails}'
        tasks.append({'id': f'flow-{n:02d}-{defect}', 'defect': defect, 'truth': truth, 'fails': fails})
        print(f'{defect:24} fails {fails}', flush=True)
    args.out.write_text(json.dumps({'checklist': oracle.CHECKLIST, 'credentials': {'username': 'tester', 'password': 'letmein'},
                                    'tasks': tasks}, indent=1))
    print(json.dumps({'tasks': len(tasks)}))


if __name__ == '__main__':
    main()
