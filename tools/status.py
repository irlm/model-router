#!/usr/bin/env python3
"""Where the routing stands on this machine, in one screen or one JSON.

Reads routing.json, catalog/models.json, the ledger, the agent files in
~/.claude/agents, git, the Claude Code version and (on Linux) the ledger timer,
and says what is worth doing: a regression check after a Claude Code update,
a price check, a pull, an apply. The mod in mod/ draws this; /router check
prints it. Thresholds are stated in ADVICE_* below, not hidden.

Usage: python3 tools/status.py [--json] [--fetch]
"""
import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import decide  # noqa: E402

ADVICE_PRICE_DAYS = 30     # prices verified longer ago than this: check the sources
ADVICE_LEDGER_DAYS = 35    # no usage ledger for this long: write one
ADVICE_REGRESS_DAYS = 60   # no regression check for this long: run one
AGENTS_DIR = Path.home() / '.claude/agents'
UNUSED_DIR = Path.home() / '.claude/agents.unused'


def sh(argv, cwd=None, timeout=30):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, '', str(e)


def claude_version():
    exe = shutil.which('claude')
    if not exe:
        return None
    _, out, _ = sh([exe, '--version'])
    return out.split()[0] if out else None


def git_state(fetch):
    git = shutil.which('git')
    if not git or not (HERE / '.git').exists():
        return {'path': str(HERE), 'is_repo': False}
    fetched = False
    if fetch:
        rc, _, _ = sh([git, 'fetch', '-q'], cwd=HERE, timeout=90)
        fetched = rc == 0
    _, head, _ = sh([git, 'rev-parse', '--short', 'HEAD'], cwd=HERE)
    _, branch, _ = sh([git, 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=HERE)
    _, dirty, _ = sh([git, 'status', '--porcelain'], cwd=HERE)
    rc, lr, _ = sh([git, 'rev-list', '--left-right', '--count', 'HEAD...@{u}'], cwd=HERE)
    ahead = behind = None
    if rc == 0 and lr:
        ahead, behind = [int(x) for x in lr.split()]
    return {'path': str(HERE), 'is_repo': True, 'head': head, 'branch': branch, 'dirty': len(dirty.splitlines()),
            'ahead': ahead, 'behind': behind, 'fetched': fetched}


def variant_of(requires):
    s = ' '.join(requires or [])
    for v in ('kunit', 'vitest'):
        if v in s:
            return v
    return ''


def can_run(bench):
    """Whether this family's regression sample can run on this machine, and why not."""
    if bench == 'find_feature':
        spec = json.loads((HERE / 'bench/find_feature/tasks/lexical.json').read_text())
        tree = Path(os.path.expanduser(spec['tree']))
        return (True, '') if tree.exists() else (False, f'needs the source tree {spec["tree"]}')
    if bench in ('fix_bug_hard', 'write_tests'):
        return False, 'needs a kernel worktree and KUnit build (regress.py --kernel-worktree): by hand'
    if bench == 'repo_fix':
        spec = json.loads((HERE / 'bench/repo_fix/repos/private-ts.json').read_text())
        clone, wts = Path(os.path.expanduser(spec['clone'])), Path(os.path.expanduser(spec['worktrees']))
        if not clone.exists() or not wts.exists():
            return False, f'needs the clone and worktrees under {spec["worktrees"]}'
        if not shutil.which('npx'):
            return False, 'needs node (npx) for vitest'
        return True, ''
    if bench == 'web_research':
        return (True, '') if shutil.which('claude') else (False, 'needs the claude CLI')
    if bench == 'browser_flow':
        return False, 'needs Chrome open (regress.py --browser): by hand'
    return False, 'no runner wired'


def regress_rows(path):
    """The per-family rows of a ledger/regress-*.md table."""
    rows = {}
    for line in path.read_text().splitlines():
        if not line.startswith('| ') or line.startswith('| Family') or line.startswith('|---'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 7:
            rows[cells[0]] = {'default': cells[1], 'sample': cells[2], 'successes': cells[3], 'verdict': cells[6]}
    return rows


def last_regress():
    files = sorted(HERE.glob('ledger/regress-*.md'))
    if not files:
        return None
    f = files[-1]
    m = re.match(r'regress-(\d{4}-\d{2}-\d{2})-claude-(.+)\.md$', f.name)
    return {'file': f.name, 'date': m.group(1) if m else None, 'claude': m.group(2) if m else None, 'rows': regress_rows(f)}


def last_usage():
    files = sorted(HERE.glob('ledger/usage-*.md'))
    return files[-1].name[len('usage-'):-3] if files else None


def frontmatter(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    if not text.startswith('---'):
        return {}
    parts = text.split('\n---', 2)
    out = {}
    for line in parts[0].splitlines()[1:]:
        if ':' in line:
            k, v = line.split(':', 1)
            out[k.strip()] = v.strip()
    return out


def agents_state(routing):
    routed = []
    for file, spec in (routing.get('agents') or {}).items():
        want = f"{spec['model']} {spec['effort']}"
        p = AGENTS_DIR / file
        if not p.exists():
            routed.append({'file': file, 'family': spec.get('family'), 'want': want, 'have': None, 'state': 'missing'})
            continue
        fm = frontmatter(p)
        have = f"{fm.get('model', '-')} {fm.get('effort', '-')}"
        routed.append({'file': file, 'family': spec.get('family'), 'want': want, 'have': have,
                       'state': 'applied' if have == want else 'drifted'})
    files = len(list(AGENTS_DIR.glob('*.md'))) if AGENTS_DIR.exists() else 0
    unused = len(list(UNUSED_DIR.glob('*.md'))) if UNUSED_DIR.exists() else 0
    return {'dir': str(AGENTS_DIR), 'files': files, 'unused': unused, 'routed': routed}


def timer_state():
    if platform.system() != 'Linux':
        return {'kind': 'none', 'note': 'the ledger timer is a Linux systemd user unit; elsewhere run /router ledger by hand'}
    sc = shutil.which('systemctl')
    if not sc:
        return {'kind': 'none', 'note': 'no systemctl'}
    rc, out, _ = sh([sc, '--user', 'list-timers', 'model-router-ledger.timer', '--no-pager', '--no-legend'])
    if rc != 0 or not out:
        return {'kind': 'systemd', 'installed': False, 'note': 'not installed: bash tools/install_ledger_timer.sh'}
    # NEXT is the first three columns (day date time) and a zone
    cols = out.split()
    return {'kind': 'systemd', 'installed': True, 'next': ' '.join(cols[:4])}


def days_since(iso, today):
    try:
        return (today - datetime.date.fromisoformat(iso)).days
    except (TypeError, ValueError):
        return None


def collect(fetch=False):
    today = datetime.date.today()
    routing = json.loads((HERE / 'routing.json').read_text())
    catalog = json.loads((HERE / 'catalog/models.json').read_text())
    version = claude_version()
    families = []
    for fam, rf in routing['families'].items():
        d = rf.get('default') or {}
        bench = (decide.FAMILIES.get(fam) or {}).get('benches', [fam])[0]
        ok, why = can_run(bench)
        model_id = next((mid for mid, alias in decide.ALIAS.items() if alias == d.get('model')), d.get('model'))
        variant = variant_of(rf.get('requires'))
        key = f"{model_id} {d.get('effort')}{'+' + variant if variant else ''}"
        ev = ((rf.get('decided') or {}).get('evidence') or {}).get(key) or {}
        families.append({'name': fam, 'bench': bench, 'status': rf.get('status'), 'model': d.get('model'), 'effort': d.get('effort'),
                         'requires': rf.get('requires') or [], 'variant': variant, 'rate': f"{ev['success']}/{ev['n'] - ev.get('not_model', 0)}" if ev else None,
                         'ci': ev.get('ci'), 'cost_per_success': ev.get('cost_per_success'), 'can_run': ok, 'why': why})
    models = [{'id': mid, 'verified': m.get('verified_date'), 'input': m.get('input_per_mtok'), 'output': m.get('output_per_mtok')}
              for mid, m in catalog['models'].items()]
    oldest = min((m['verified'] for m in models if m['verified']), default=None)
    reg = last_regress()
    usage = last_usage()
    git = git_state(fetch)
    agents = agents_state(routing)
    timer = timer_state()
    for f in families:
        f['last_check'] = (reg or {}).get('rows', {}).get(f['name'])

    advice = []
    if version and reg and reg.get('claude') and reg['claude'] != version:
        advice.append(f"Claude Code is {version}; the last regression check ran on {reg['claude']}: /router update")
    if reg and days_since(reg.get('date'), today) is not None and days_since(reg['date'], today) > ADVICE_REGRESS_DAYS:
        advice.append(f"last regression check was {days_since(reg['date'], today)} days ago: /router update")
    if not reg:
        advice.append('no regression check yet: /router update')
    for f in families:
        lc = f.get('last_check')
        if lc and lc['verdict'] not in ('ok',) and not lc['verdict'].startswith('skipped'):
            advice.append(f"{f['name']}: last check said '{lc['verdict']}' ({lc['successes']}/{lc['sample']}): read ledger/{reg['file']}")
    age = days_since(oldest, today) if oldest else None
    if age is not None and age > ADVICE_PRICE_DAYS:
        advice.append(f"prices verified {age} days ago ({oldest}): check the sources in catalog/models.json, then decide.py")
    if git.get('behind'):
        advice.append(f"repo is {git['behind']} commit(s) behind origin: /router pull")
    if git.get('dirty'):
        advice.append(f"{git['dirty']} uncommitted change(s) in the repo")
    for a in agents['routed']:
        if a['state'] != 'applied':
            advice.append(f"agent {a['file']} is {a['state']} (want {a['want']}, have {a['have']}): /router apply")
    if usage is None or (days_since(usage, today) or 0) > ADVICE_LEDGER_DAYS:
        advice.append(f"no usage ledger since {usage}: /router ledger")
    if timer.get('kind') == 'systemd' and not timer.get('installed'):
        advice.append('ledger timer not installed: bash tools/install_ledger_timer.sh')
    if not version:
        advice.append('claude CLI not found on PATH: nothing can run here')

    return {'at': datetime.datetime.now().isoformat(timespec='minutes'), 'platform': platform.system(), 'host': platform.node(),
            'python': sys.version.split()[0], 'claude': version, 'repo': git,
            'routing': {'version': routing.get('version'), 'decided': routing.get('decided')},
            'families': families, 'agents': agents,
            'catalog': {'verified_oldest': oldest, 'age_days': age, 'models': models, 'fees_verified': (catalog.get('fees') or {}).get('verified')},
            'ledger': {'usage_last': usage, 'regress_last': reg}, 'timer': timer, 'advice': advice,
            'thresholds': {'price_days': ADVICE_PRICE_DAYS, 'ledger_days': ADVICE_LEDGER_DAYS, 'regress_days': ADVICE_REGRESS_DAYS}}


def text(s):
    g = s['repo']
    sync = ('not a git checkout' if not g.get('is_repo') else
            ', '.join(x for x in [f"{g['dirty']} dirty" if g.get('dirty') else 'clean',
                                  (f"{g['behind']} behind" if g.get('behind') else 'up to date' if g.get('behind') == 0 else 'origin unknown'),
                                  f"{g['ahead']} ahead" if g.get('ahead') else ''] if x))
    out = [f"model-router  {s['at']}  {s['platform']}  Claude Code {s['claude'] or 'not found'}  repo {g.get('head', '-')} ({sync})",
           f"routing v{s['routing']['version']} decided {s['routing']['decided']}", '',
           f"{'family':<14}{'default':<22}{'evidence':<10}{'$/success':<11}{'here':<6}last check"]
    for f in s['families']:
        d = (f"{f['model']} {f['effort']}" + (' +' + f['variant'] if f['variant'] else '')) if f['model'] else 'none'
        lc = f.get('last_check')
        last = f"{lc['verdict']} {lc['successes']}/{lc['sample']}" if lc and lc['sample'] else (lc['verdict'] if lc else '-')
        cost = f"{f['cost_per_success']:.4f}" if f.get('cost_per_success') is not None else '-'
        out.append(f"{f['name']:<14}{d:<22}{f['rate'] or '-':<10}{cost:<11}{'yes' if f['can_run'] else 'no':<6}{last}")
    a = s['agents']
    applied = sum(1 for r in a['routed'] if r['state'] == 'applied')
    out += ['', f"agents: {a['files']} files in {a['dir']}, {a['unused']} unused; routed {applied}/{len(a['routed'])} applied",
            f"prices: verified {s['catalog']['verified_oldest']} ({s['catalog']['age_days']} days)   "
            f"ledger: usage {s['ledger']['usage_last']}, regress {(s['ledger']['regress_last'] or {}).get('date')} "
            f"on {(s['ledger']['regress_last'] or {}).get('claude')}   timer: {s['timer'].get('next') or s['timer'].get('note')}", '']
    out += ['advice: nothing to do'] if not s['advice'] else ['advice:'] + [f"  - {x}" for x in s['advice']]
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--fetch', action='store_true', help='git fetch first, so behind/ahead are current')
    args = ap.parse_args()
    s = collect(fetch=args.fetch)
    print(json.dumps(s) if args.json else text(s))


if __name__ == '__main__':
    main()
