"""The skills nothing on this machine loaded in the window: listed name-only, so their descriptions
leave every request (Claude Code's `skillOverrides` setting; "name-only" keeps /name and the name in the
list, drops the description). Reversible: what this wrote is recorded in
<CLAUDE_CONFIG_DIR or ~/.claude>/model-router/skills-pruned.json and --revert removes exactly that.

A plugin's skills are left alone: they leave the list only with their plugin (claude plugin disable).
A skill already overridden by hand (any value) is left alone. --keep names skills to leave listed.
--agents runs tools/prune_agents.py first in the same mode, so one command prunes both lists.

    python3 tools/prune_skills.py --dry-run        # what would change
    python3 tools/prune_skills.py                  # write it
    python3 tools/prune_skills.py --revert         # undo what this wrote
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_home  # noqa: E402

VALUE = 'name-only'


def unused_skills(days, fixed_json):
    """The listed skills nothing loaded in the window, largest first; None when no transcript has the listing."""
    if fixed_json:
        fx = json.loads(Path(fixed_json).read_text(encoding='utf-8'))
    else:
        import consumption
        fx = consumption.collect(days).get('fixed')
    if not fx:
        return None
    return ((fx.get('parts') or {}).get('skills') or {}).get('unused') or []


def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--settings', type=Path, default=claude_home.config_dir() / 'settings.json', help='the settings file skillOverrides lives in')
    ap.add_argument('--state', type=Path, default=claude_home.config_dir() / 'model-router' / 'skills-pruned.json')
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--fixed-json', type=Path, help='a saved fixed-text summary instead of the transcript scan (tests)')
    ap.add_argument('--keep', nargs='*', default=[], help='skill names to leave listed with their description')
    ap.add_argument('--agents', action='store_true', help='prune the agent files first (tools/prune_agents.py), in the same mode')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    if args.agents:
        argv = [sys.executable, str(HERE / 'prune_agents.py')] + (['--revert'] if args.revert else []) + (['--dry-run'] if args.dry_run else [])
        print('── agents ──')
        r = subprocess.run(argv, text=True)
        if r.returncode != 0:
            return r.returncode
        print('── skills ──')
    settings = read_json(args.settings, {})
    overrides = settings.get('skillOverrides') or {}
    if args.revert:
        wrote = read_json(args.state, [])
        back = [n for n in wrote if overrides.get(n) == VALUE]
        for n in back:
            print('restore', n)
            del overrides[n]
        if not args.dry_run:
            if overrides:
                settings['skillOverrides'] = overrides
            else:
                settings.pop('skillOverrides', None)
            write_json(args.settings, settings)
            if args.state.exists():
                args.state.unlink()
        print(f'{len(back)} skills {"would be " if args.dry_run else ""}listed with their description again in {args.settings}')
        return 0
    unused = unused_skills(args.days, args.fixed_json)
    if unused is None:
        print('no transcript here carries the skill listing yet (Claude Code 2.1.28x on): nothing to prune')
        return 0
    own, tokens = [], 0
    plugin = [u for u in unused if ':' in u['name']]
    for u in unused:
        name = u['name']
        if ':' in name:
            continue
        if name in args.keep:
            print(f'keep  {name}: --keep')
        elif name in overrides:
            print(f'keep  {name}: already {overrides[name]} in {args.settings.name}')
        else:
            print(f'{"would set" if args.dry_run else "set"}  {name}: {VALUE} ({u["tokens"]} tokens)')
            own.append(name); tokens += u['tokens']
    if plugin:
        print(f'{len(plugin)} plugin skills left alone; they leave the list with their plugin: claude plugin disable <plugin>@<marketplace> --scope project')
    if own and not args.dry_run:
        for n in own:
            overrides[n] = VALUE
        settings['skillOverrides'] = overrides
        write_json(args.settings, settings)
        write_json(args.state, sorted(set(read_json(args.state, [])) | set(own)))
    print(f'{len(own)} skills {"would be " if args.dry_run else ""}listed {VALUE} in {args.settings}: about {tokens} tokens off every request'
          + ('' if args.dry_run else '; a new session sees it; /router prune skills revert undoes it'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
