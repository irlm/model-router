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
sys.path.insert(0, str(HERE / 'tools'))
sys.path.insert(0, str(HERE / 'bench/common'))
import decide  # noqa: E402
import consumption  # noqa: E402
import local  # noqa: E402

ADVICE_PRICE_DAYS = 30     # prices verified longer ago than this: check the sources
ADVICE_LEDGER_DAYS = 35    # no usage ledger for this long: write one
ADVICE_REGRESS_DAYS = 60   # no regression check for this long: run one
USAGE_DAYS = 30            # the consumption window the suggestions are computed on
# Cost of a task at this effort divided by its cost at low, measured on results/cell8 repo_fix
# (24 tasks, every effort solved every task): the only effort sweep with more than one tier.
EFFORT_RATIO = {'xhigh': {'claude-opus-5-5': 1.30, 'claude-fable-5-1': 1.52}, 'high': {'claude-opus-5-5': 1.06, 'claude-fable-5-1': 1.16}}
# Opus 5.5 cost per success divided by Fable 5.1's on the families where both were run at the same effort:
# repo_fix 0.178/0.481 = 0.37, web_research 0.12/0.30 = 0.40 (results/cell8), same results on both.
OPUS_OVER_FABLE = (0.37, 0.40)
WEB_RESEARCHER_COST = 0.022   # Haiku low per fact lookup, 76/78 correct (results/cell8)
AGENTS_DIR = Path.home() / '.claude/agents'
UNUSED_DIR = Path.home() / '.claude/agents.unused'


def sh(argv, cwd=None, timeout=30):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, cwd=cwd)
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
        spec = json.loads((HERE / 'bench/find_feature/tasks/lexical.json').read_text(encoding='utf-8'))
        tree = Path(local.resolve(spec['tree']))
        return (True, '') if tree.exists() else (False, f'needs the kernel tree {spec["tree"]} (local/config.json: kernel_tree)')
    if bench in ('fix_bug_hard', 'write_tests'):
        return False, 'needs a kernel worktree and KUnit build (regress.py --kernel-worktree): by hand'
    if bench == 'repo_fix':
        repos = sorted(p for p in (HERE / 'bench/repo_fix/repos').glob('*.json') if p.stem != 'example')
        if not repos or not (HERE / 'bench/repo_fix/tasks.json').exists():
            return False, 'needs a repository of your own: bench/repo_fix/repos/<name>.json and its tasks (local/README.md)'
        spec = json.loads(repos[0].read_text(encoding='utf-8'))
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
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('| ') or line.startswith('| Family') or line.startswith('|---'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 7:
            rows[cells[0]] = {'default': cells[1], 'sample': cells[2], 'successes': cells[3], 'verdict': cells[6]}
    return rows


REGRESS_NAME = re.compile(r'regress-(\d{4}-\d{2}-\d{2})-claude-(.+?)(?:-r(\d+))?\.md$')


def last_regress():
    """The newest ledger/regress-<date>-claude-<version>[-rN].md by date, then run number."""
    found = []
    for f in HERE.glob('ledger/regress-*.md'):
        m = REGRESS_NAME.match(f.name)
        if m:
            found.append(((m.group(1), int(m.group(3) or 1)), f, m))
    if not found:
        return None
    _, f, m = max(found, key=lambda x: x[0])
    return {'file': f.name, 'date': m.group(1), 'claude': m.group(2), 'run': int(m.group(3) or 1), 'rows': regress_rows(f)}


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
        routed.append({'file': file, 'name': fm.get('name') or p.stem, 'family': spec.get('family'), 'want': want, 'have': have,
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


def suggest(usage, agents):
    """Where the last USAGE_DAYS days could have consumed less for the same work, each with its evidence.

    kind: measured (a decided family covers it), extrapolated (measured on the benchmark's tasks,
    applied to sessions it did not measure) or unmeasured (the stake is known, no cheaper model is)."""
    out = []
    rows = usage['main']['rows']
    # 1. effort above low in main sessions
    hi = [r for r in rows if r['effort'] in EFFORT_RATIO]
    if hi:
        spend = sum(r['cost'] for r in hi)
        lo = hi_ = 0.0
        for r in hi:
            ratios = EFFORT_RATIO[r['effort']]
            rr = ratios.get(r['model'].split(' ')[0])
            rs = [rr] if rr else list(ratios.values())
            lo += r['cost'] * (1 - 1 / max(rs)) if rr else r['cost'] * (1 - 1 / min(rs))
            hi_ += r['cost'] * (1 - 1 / min(rs)) if rr else r['cost'] * (1 - 1 / max(rs))
        lo, hi_ = min(lo, hi_), max(lo, hi_)
        out.append({'id': 'effort', 'kind': 'extrapolated', 'stake': round(spend, 2), 'saving': [round(lo, 2), round(hi_, 2)],
                    'title': f"main sessions at high/xhigh effort: ${spend:.0f} in {USAGE_DAYS} days",
                    'basis': 'results/cell8: xhigh cost 1.30x (Opus) to 1.52x (Fable) of low, high 1.06x to 1.16x, same 24/24 fixes at every effort; '
                             'your sessions were not measured, so this is the sweep\'s ratio applied to them',
                    'action': 'start routine sessions with `claude --effort low` (or set effortLevel in settings.json); the next ledger shows the change'})
    # 2. fact lookups that did not go through the routed Web Researcher
    bc = usage['subagents']['by_class']
    fl = bc.get('fact-lookup')
    if fl and any(t != 'Web Researcher' for t in fl['types']):
        n = sum(v for t, v in fl['types'].items() if t != 'Web Researcher')
        cost = fl['cost']
        out.append({'id': 'lookups', 'kind': 'measured', 'stake': cost, 'saving': [round(max(0.0, cost - n * WEB_RESEARCHER_COST), 2)] * 2,
                    'title': f"{n} fact lookups ran on general-purpose agents (${cost:.2f})",
                    'basis': f'web_research family: Haiku low 76/78 correct with sources at ${WEB_RESEARCHER_COST} each (results/cell8)',
                    'action': 'ask for the Web Researcher agent for lookups (model haiku, effort low in ~/.claude/agents/web-researcher.md)'})
    # 3. research synthesis: the stake is known, no cheaper model is
    rs = bc.get('research-synthesis')
    if rs and rs['n']:
        out.append({'id': 'synthesis', 'kind': 'unmeasured', 'stake': rs['cost'], 'saving': None,
                    'title': f"{rs['n']} research reports on general-purpose agents at the session model (${rs['cost']:.2f})",
                    'basis': 'no family grades report writing yet; the fact-lookup result (Haiku 76/78) does not transfer to synthesis',
                    'action': f"worth measuring next: a synthesis rubric family (GAPS.md open item); until then no blind downgrade"})
    # 4. Fable in main sessions where the measured families saw Opus equal
    fable = [r for r in rows if r['model'].startswith('claude-fable-5-1')]
    if fable:
        spend = sum(r['cost'] for r in fable)
        out.append({'id': 'tier', 'kind': 'unmeasured', 'stake': round(spend, 2),
                    'saving': [round(spend * (1 - OPUS_OVER_FABLE[1]), 2), round(spend * (1 - OPUS_OVER_FABLE[0]), 2)],
                    'title': f"main sessions on Fable 5.1: ${spend:.0f} in {USAGE_DAYS} days",
                    'basis': 'on the measured families Opus 5.5 matched Fable (24/24 and 26/26) at 37-40% of the cost (results/cell8); '
                             'main-session work is not measured, so the saving is what it would be if that held',
                    'action': 'try `claude --model opus` for routine sessions and compare the next ledger; keep Fable where you see the difference'})
    return out


def collect(fetch=False):
    today = datetime.date.today()
    routing = json.loads((HERE / 'routing.json').read_text(encoding='utf-8'))
    catalog = json.loads((HERE / 'catalog/models.json').read_text(encoding='utf-8'))
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
    git = git_state(fetch)
    agents = agents_state(routing)
    timer = timer_state()
    for f in families:
        f['last_check'] = (reg or {}).get('rows', {}).get(f['name'])
    usage = consumption.collect(USAGE_DAYS)
    suggestions = suggest(usage, agents)

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
    usage_last = last_usage()
    if usage_last is None or (days_since(usage_last, today) or 0) > ADVICE_LEDGER_DAYS:
        advice.append(f"no usage ledger since {usage_last}: /router ledger")
    if timer.get('kind') == 'systemd' and not timer.get('installed'):
        advice.append('ledger timer not installed: bash tools/install_ledger_timer.sh')
    if not version:
        advice.append('claude CLI not found on PATH: nothing can run here')
    unpriced = [r for r in usage['main']['rows'] if r['model'].endswith('(no price)')]
    if unpriced:
        advice.append(f"{sum(r['msgs'] for r in unpriced)} messages in {USAGE_DAYS} days on model ids without a catalog price "
                      f"({', '.join(sorted(set(r['model'].split(' ')[0] for r in unpriced)))}): totals understate; add them to catalog/models.json")

    return {'at': datetime.datetime.now().isoformat(timespec='minutes'), 'platform': platform.system(), 'host': platform.node(),
            'python': sys.version.split()[0], 'claude': version, 'repo': git,
            'routing': {'version': routing.get('version'), 'decided': routing.get('decided')},
            'families': families, 'agents': agents,
            'catalog': {'verified_oldest': oldest, 'age_days': age, 'models': models, 'fees_verified': (catalog.get('fees') or {}).get('verified')},
            'ledger': {'usage_last': last_usage(), 'regress_last': reg}, 'timer': timer, 'advice': advice,
            'usage': {'days': usage['days'], 'since': usage['since'], 'main_total': usage['main']['total'], 'main_out_cost': usage['main']['out_cost'],
                      'main_rows': [{k: r[k] for k in ('model', 'effort', 'msgs', 'cost', 'out_cost')} for r in usage['main']['rows'] if r['cost'] >= 0.5 or r['model'].endswith('(no price)')],
                      'subagents_total': usage['subagents']['total'], 'subagent_calls': len(usage['subagents']['calls']),
                      'by_class': {k: {'n': v['n'], 'cost': v['cost'], 'types': v['types']} for k, v in usage['subagents']['by_class'].items()},
                      'previous': {'since': usage['previous']['since'], 'main_total': usage['previous']['main_total'], 'subagents_total': usage['previous']['subagents_total']}},
            'suggestions': suggestions,
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
    u = s['usage']
    out += ['', f"consumption, last {u['days']} days since {u['since']} (catalog $ = headroom on a subscription): "
                f"main ${u['main_total']:.0f} (output ${u['main_out_cost']:.0f}), subagents ${u['subagents_total']:.0f} in {u['subagent_calls']} calls; "
                f"previous {u['days']} days: main ${u['previous']['main_total']:.0f}, subagents ${u['previous']['subagents_total']:.0f}"]
    for r in u['main_rows'][:8]:
        out.append(f"  {r['model']:<32}{r['effort']:<8}{r['msgs']:>6} msgs  ${r['cost']:>7.2f}")
    for cls, b in sorted(u['by_class'].items(), key=lambda kv: -kv[1]['cost']):
        out.append(f"  subagents {cls:<22}{b['n']:>4} calls ${b['cost']:>7.2f}  " + ', '.join(f'{t} x{n}' for t, n in b['types'].items()))
    out.append('')
    if not s['suggestions']:
        out.append('suggestions: none from the last window')
    for g in s['suggestions']:
        sv = (f"saves ${g['saving'][0]:.0f}-{g['saving'][1]:.0f}" if g['saving'] and g['saving'][0] != g['saving'][1]
              else f"saves ${g['saving'][0]:.0f}" if g['saving'] else 'saving unknown')
        out += [f"[{g['kind']}] {g['title']}: {sv} per {u['days']} days", f"    basis: {g['basis']}", f"    do: {g['action']}"]
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
