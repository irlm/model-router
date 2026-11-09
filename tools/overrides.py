"""Per-project routing overrides on this machine: what the person chose for a class of Agent call in one
project, after the widget's learned suggestion (or on their own). The router applies an override before
the family default. Stored in <CLAUDE_CONFIG_DIR or ~/.claude>/model-router/overrides.json, never in the
repository: {project_key: {class: {model, effort, since, why}}}. The project key is the transcript
directory name Claude Code uses (the working directory with every non-alphanumeric character as '-').

  python3 tools/overrides.py set <project_key> <class> <model> <effort> [--why TEXT]
  python3 tools/overrides.py clear <project_key> <class>
  python3 tools/overrides.py list
"""
import argparse
import datetime
import json
import os
from pathlib import Path

FILE = Path(os.environ.get('CLAUDE_CONFIG_DIR') or (Path.home() / '.claude')) / 'model-router' / 'overrides.json'
MODELS = ('haiku', 'sonnet', 'opus', 'fable')
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')


def read():
    try:
        return json.loads(FILE.read_text(encoding='utf-8')) if FILE.exists() else {}
    except ValueError:
        return {}


def write(data):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')


def set_override(project, cls, model, effort, why=''):
    if model not in MODELS or effort not in EFFORTS:
        raise SystemExit(f'model must be one of {MODELS} and effort one of {EFFORTS}')
    data = read()
    data.setdefault(project, {})[cls] = {'model': model, 'effort': effort, 'why': why,
                                         'since': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}
    write(data)
    return data[project][cls]


def dismissed():
    """Suggestion ids the person judged wrong: hidden from the glance, listed under Details."""
    return read().get('_dismissed') or {}


def dismiss(sid, undo=False):
    data = read()
    d = data.setdefault('_dismissed', {})
    if undo:
        gone = d.pop(sid, None)
    else:
        d[sid] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        gone = d[sid]
    if not d:
        data.pop('_dismissed', None)
    write(data)
    return gone


def clear(project, cls):
    data = read()
    gone = (data.get(project) or {}).pop(cls, None)
    if project in data and not data[project]:
        del data[project]
    write(data)
    return gone


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('verb', choices=['set', 'clear', 'list', 'dismiss', 'undismiss'])
    ap.add_argument('words', nargs='*')
    ap.add_argument('--why', default='')
    a = ap.parse_args(argv)
    if a.verb in ('dismiss', 'undismiss'):
        if len(a.words) != 1:
            raise SystemExit('dismiss needs the suggestion id')
        print(dismiss(a.words[0], undo=a.verb == 'undismiss') or 'nothing to undo')
        return
    if a.verb == 'list':
        for proj, classes in read().items():
            if proj == '_dismissed':
                print('dismissed:', ', '.join(f'{k} ({v})' for k, v in classes.items()))
                continue
            for cls, o in classes.items():
                print(f"{proj}  {cls:20} {o['model']} {o['effort']}  since {o['since']}  {o.get('why', '')}")
    elif a.verb == 'set':
        if len(a.words) != 4:
            raise SystemExit('set needs: <project_key> <class> <model> <effort>')
        print(json.dumps(set_override(*a.words, why=a.why)))
    else:
        if len(a.words) != 2:
            raise SystemExit('clear needs: <project_key> <class>')
        print('cleared' if clear(*a.words) else 'nothing to clear')


if __name__ == '__main__':
    main()
