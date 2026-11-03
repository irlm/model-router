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
import collections
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
sys.path.insert(0, str(HERE / 'catalog'))
import price  # noqa: E402
import changes  # noqa: E402
import consumption  # noqa: E402
import overrides  # noqa: E402
import routed_log  # noqa: E402
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
FIND_FEATURE_COST = 0.0046    # Haiku low per code search, 214/216 found (routing.json evidence)
BROWSER_FLOW_COST = 0.0367    # Haiku low per browser flow, 63/63 on the toy app (routing.json evidence)
SUGGESTION_FLOOR = 0.5        # a known saving below this many dollars per window is not worth a line
# Which measured family stands behind each class of Agent call the consumption scan sees.
CLASS_FAMILY = {'code-explore': 'find_feature', 'fact-lookup': 'web_research', 'browser-flow': 'browser_flow', 'code-change': 'repo_fix',
                'research-synthesis': 'research_synthesis'}
STRUGGLE_MIN_N = 8            # calls of one class in one project before its struggle rate means anything
NEXT_TIER = {'haiku': 'sonnet', 'sonnet': 'opus', 'opus': 'fable', 'fable': 'fable'}
CLASS_LABEL = {'code-explore': 'code searches', 'fact-lookup': 'fact lookups', 'browser-flow': 'browser flows',
               'research-synthesis': 'research notes', 'code-change': 'code changes', 'code-review': 'code reviews', 'other': 'other calls'}
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
    _, out, err = sh([exe, '--version'])
    # The first version-shaped word: a tool manager (mise) may print its own notice first.
    m = re.search(r'\d+\.\d+\.\d+\S*', out) or re.search(r'\d+\.\d+\.\d+\S*', err)
    return m.group(0) if m else None


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
    if bench in ('web_research', 'research_synthesis'):
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
            # missing: the repository ships it (agents/), apply installs it; absent: an agent file this machine does not have
            state = 'missing' if (HERE / 'agents' / file).exists() else 'absent'
            routed.append({'file': file, 'family': spec.get('family'), 'want': want, 'have': None, 'state': state})
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


def suggest(usage, agents, routing=None):
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
        others = {t: v for t, v in fl['types'].items() if t != 'Web Researcher'}
        n = sum(others.values())
        cost = fl['cost']
        out.append({'id': 'lookups', 'kind': 'measured', 'stake': cost, 'saving': [round(max(0.0, cost - n * WEB_RESEARCHER_COST), 2)] * 2,
                    'title': f"{n} fact lookups ran on {', '.join(f'{t} x{v}' for t, v in sorted(others.items(), key=lambda kv: -kv[1]))} (${cost:.2f}, last {fl['last'][:10]})",
                    'basis': f'web_research family: Haiku low 76/78 correct with sources at ${WEB_RESEARCHER_COST} each (results/cell8)',
                    'action': 'ask for the Web Researcher agent for lookups (model haiku, effort low in ~/.claude/agents/web-researcher.md)'})
    # 3. code searches that ran above haiku: the find_feature family covers them, the widget routes them
    ce = bc.get('code-explore')
    dear = {m: v for m, v in (ce or {}).get('models', {}).items() if m != '?' and not m.startswith('claude-haiku')}
    if dear:
        n = sum(v['n'] for v in dear.values()); cost = round(sum(v['cost'] for v in dear.values()), 2)
        out.append({'id': 'explore', 'kind': 'measured', 'stake': cost, 'saving': [round(max(0.0, cost - n * FIND_FEATURE_COST), 2)] * 2,
                    'title': f"{n} code searches above haiku (${cost:.2f} on {', '.join(m.removeprefix('claude-') for m in sorted(dear))}, last {ce['last'][:10]})",
                    'basis': f'find_feature family: Haiku low found 214/216 at ${FIND_FEATURE_COST} per search; the widget routes Explore calls when routing is ask or auto',
                    'action': '/router routing auto, so these calls run on haiku low without asking (or pick the measured option when the router asks)'})
    # 3b. browser flows that ran above haiku: the browser_flow family covers them, the widget routes them
    bf = bc.get('browser-flow')
    dear = {m: v for m, v in (bf or {}).get('models', {}).items() if m != '?' and not m.startswith('claude-haiku')}
    if dear:
        n = sum(v['n'] for v in dear.values()); cost = round(sum(v['cost'] for v in dear.values()), 2)
        out.append({'id': 'browser', 'kind': 'measured', 'stake': cost, 'saving': [round(max(0.0, cost - n * BROWSER_FLOW_COST), 2)] * 2,
                    'title': f"{n} browser flows above haiku (${cost:.2f} on {', '.join(m.removeprefix('claude-') for m in sorted(dear))}, last {bf['last'][:10]})",
                    'basis': f'browser_flow family: Haiku low drove 63/63 checklist flows at ${BROWSER_FLOW_COST} each, and 28/30 on a real store; the widget routes browser flows when routing is ask or auto',
                    'action': '/router routing auto, so browser flows run on haiku low without asking; or set model haiku, effort low in the agent file that drives them'})
    # 4. research notes: measured once the research_synthesis family is decided (routing.json), unmeasured before
    rs = bc.get('research-synthesis')
    fam = ((routing or {}).get('families') or {}).get('research_synthesis') or {}
    d = fam.get('default') or {}
    ev = ((fam.get('decided') or {}).get('evidence') or {})
    model_id = next((mid for mid, alias in decide.ALIAS.items() if alias == d.get('model')), d.get('model'))
    per = (ev.get(f"{model_id} {d.get('effort')}") or {}).get('cost_per_success') if d.get('model') else None
    dear = {m: v for m, v in (rs or {}).get('models', {}).items() if m != '?' and not m.startswith(str(model_id))} if per is not None else {}
    if dear:
        n = sum(v['n'] for v in dear.values()); cost = round(sum(v['cost'] for v in dear.values()), 2)
        out.append({'id': 'synthesis', 'kind': 'measured', 'stake': cost, 'saving': [round(max(0.0, cost - n * per), 2)] * 2,
                    'title': f"{n} research notes above {d['model']} (${cost:.2f} on {', '.join(m.removeprefix('claude-') for m in sorted(dear))}, last {rs['last'][:10]})",
                    'basis': f"research_synthesis family: {d['model']} {d['effort']} {(fam.get('evidence') or {}).get(d['model'] + ' ' + d['effort'], '')} on fact-dense notes "
                             f"with sources at ${per} per note (results/cell9); the prose beyond the facts is not judged",
                    'action': '/router routing auto, so research notes run on the decided model; keep the session model where you see the difference'})
    elif rs and rs['n'] and per is None:
        out.append({'id': 'synthesis', 'kind': 'unmeasured', 'stake': rs['cost'], 'saving': None,
                    'title': f"{rs['n']} research reports on general-purpose agents at the session model (${rs['cost']:.2f})",
                    'basis': 'no family grades report writing yet; the fact-lookup result (Haiku 76/78) does not transfer to synthesis',
                    'action': f"worth measuring next: a synthesis rubric family (GAPS.md open item); until then no blind downgrade"})
    # 5. Fable in main sessions where the measured families saw Opus equal
    fable = [r for r in rows if r['model'].startswith('claude-fable-5-1')]
    if fable:
        spend = sum(r['cost'] for r in fable)
        out.append({'id': 'tier', 'kind': 'unmeasured', 'stake': round(spend, 2),
                    'saving': [round(spend * (1 - OPUS_OVER_FABLE[1]), 2), round(spend * (1 - OPUS_OVER_FABLE[0]), 2)],
                    'title': f"main sessions on Fable 5.1: ${spend:.0f} in {USAGE_DAYS} days",
                    'basis': 'on the measured families Opus 5.5 matched Fable (24/24 and 26/26) at 37-40% of the cost (results/cell8); '
                             'main-session work is not measured, so the saving is what it would be if that held',
                    'action': 'try `claude --model opus` for routine sessions and compare the next ledger; keep Fable where you see the difference'})
    return [g for g in out if g['saving'] is None or g['saving'][1] >= SUGGESTION_FLOOR]


# Which part of a realized window answers each suggestion: a class of Agent call, or the main sessions.
SUGG_SCOPE = {'explore': ('class', 'code-explore'), 'browser': ('class', 'browser-flow'), 'synthesis': ('class', 'research-synthesis'),
              'lookups': ('class', 'fact-lookup'), 'effort': ('main', 'effort'), 'tier': ('main', 'model')}


def span_days(a, b):
    start = datetime.datetime.strptime(a[:16], '%Y-%m-%dT%H:%M').replace(tzinfo=datetime.timezone.utc)
    end = datetime.datetime.strptime(b[:16], '%Y-%m-%dT%H:%M').replace(tzinfo=datetime.timezone.utc) if b else datetime.datetime.now(datetime.timezone.utc)
    return max(0.0, (end - start).total_seconds() / 86400)


def verdicts(suggestions, latest, days):
    """Estimate against real, per suggestion, from the latest realized window: what the suggestion's class (or the
    main sessions) saved since the change, scaled to the window's length. States: not applied (the after side
    still runs what the suggestion wants changed), no calls yet, too early (under a day or too few units),
    holding (real at or above half the estimate), below estimate, wrong so far (dearer). The person decides."""
    for g in suggestions:
        scope = SUGG_SCOPE.get(g['id'])
        if not scope or not latest:
            continue
        est = g['saving'][1] if g['saving'] else None
        sd = span_days(latest['since'], latest.get('until'))
        real = {'since': latest['since'], 'span': latest.get('span'), 'est': est, 'saved': None, 'per_window': None, 'state': ''}
        if scope[0] == 'class':
            c = next((c for c in latest['classes'] if c['class'] == scope[1]), None)
            if not c:
                real['state'] = 'no calls since the change'
            else:
                dear = [m for m in c['after']['models'] if m != '?' and not m.startswith('claude-haiku')]
                applied = scope[1] != 'research-synthesis' and not dear or scope[1] == 'research-synthesis' and not any(m.startswith('claude-fable') or m.startswith('claude-opus') for m in c['after']['models'])
                real['saved'] = c['saved']
                if not applied:
                    real['state'] = 'not applied: the calls after the change still ran above the decided model'
                elif c['after']['n'] < 5 or sd < 1:
                    real['state'] = f"too early: {c['after']['n']} calls in {latest.get('span')}"
                else:
                    real['per_window'] = round(c['saved'] / sd * days, 2) if c['saved'] is not None else None
        else:
            m = latest['main']
            rows = [r for r in m['rows'] if r['after']]
            top = max(rows, key=lambda r: r['after']['msgs'])['after'] if rows else None
            top_row = max(rows, key=lambda r: r['after']['msgs']) if rows else None
            applied = bool(top_row) and (top_row['effort'] == 'low' if scope[1] == 'effort' else top_row['model'].startswith('claude-opus'))
            real['saved'] = m['saved']
            if not top:
                real['state'] = 'no messages since the change'
            elif not applied:
                real['state'] = f"not applied: main sessions still on {top_row['model'].removeprefix('claude-')} {top_row['effort']}"
            elif m['after']['msgs'] < 50 or sd < 1:
                real['state'] = f"too early: {m['after']['msgs']} msgs in {latest.get('span')}"
            else:
                real['per_window'] = round(m['saved'] / sd * days, 2) if m['saved'] is not None else None
        if real['per_window'] is not None and not real['state']:
            pw = real['per_window']
            real['state'] = 'wrong so far' if pw <= 0 else 'holding' if est is None or pw >= 0.5 * est else 'below estimate'
        g['real'] = real
    return suggestions


def slots(usage, routed, days):
    """The window in weekly slots, oldest first: spend, Agent calls, struggled calls, routed calls."""
    now = datetime.datetime.now(datetime.timezone.utc).date()
    starts = [now - datetime.timedelta(days=d) for d in range(days - 1, -1, -7)]
    out = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else now + datetime.timedelta(days=1)
        a, b = start.isoformat(), end.isoformat()
        calls = [c for c in usage['subagents']['calls'] if a <= c['ts'][:10] < b]
        out.append({'since': a, 'until': (end - datetime.timedelta(days=1)).isoformat(),
                    'spend': round(sum(d['cost'] for d in usage.get('daily', []) if a <= d['date'] < b), 2),
                    'calls': len(calls), 'struggled': sum(1 for c in calls if c.get('retry_of') or c.get('errors', 0) >= consumption.ERROR_HEAVY or c.get('failed')),
                    'routed': sum(1 for r in routed if a <= r['at'][:10] < b)})
    return out


def project_short(key):
    """A transcript project key without this machine's home prefix: -home-me-Projects-x -> Projects-x."""
    home = re.sub(r'[^A-Za-z0-9]', '-', str(Path.home()))
    return key[len(home) + 1:] if key.startswith(home + '-') else key


def learned_from(struggle, routing, ovr, threshold):
    """What this machine's own transcripts say, per project and class of Agent call: how many calls struggled
    (re-issued in the session, 3+ tool errors inside, or failed) against the rest of this machine, and how
    often sessions hit the context boundary. A cell is hot with at least STRUGGLE_MIN_N calls and a rate at
    or above the threshold and twice the rest of the machine: the threshold is the person's, the baseline is
    theirs too, so a project that asks differently is judged against their own other work. Suggestions of
    kind 'learned' never cite the benchmark; they say to read what failed first."""
    cells = struggle.get('cells') or {}
    flat = [(p, c, x) for p, cs in cells.items() for c, x in cs.items()]
    tot_n = sum(x['n'] for _, _, x in flat)
    tot_s = sum(x['struggled'] for _, _, x in flat)
    out_cells, sugg = [], []
    for p, c, x in sorted(flat, key=lambda t: -t[2]['n']):
        on, os_ = tot_n - x['n'], tot_s - x['struggled']
        base = os_ / on if on else 0.0
        rate = x['struggled'] / x['n'] if x['n'] else 0.0
        hot = x['n'] >= STRUGGLE_MIN_N and rate >= max(threshold, 2 * base)
        ov = (ovr.get(p) or {}).get(c)
        out_cells.append({'project': project_short(p), 'project_key': p, 'class': c, 'hot': hot, 'rate': round(rate, 3), 'baseline': round(base, 3),
                          'override': ov, **{k: x[k] for k in ('n', 'retries', 'error_heavy', 'failed', 'struggled', 'cost', 'examples')}})
        if hot and not ov:
            fam = CLASS_FAMILY.get(c)
            d = (((routing or {}).get('families') or {}).get(fam) or {}).get('default') or {} if fam else {}
            step = NEXT_TIER.get(d.get('model'), 'the next tier')
            what = [s for s, k in ((f"{x['error_heavy']} hit {consumption.ERROR_HEAVY}+ tool errors", x['error_heavy']),
                                   (f"{x['retries']} were re-issued", x['retries']), (f"{x['failed']} failed", x['failed'])) if k]
            sugg.append({'id': f'learned:{p}:{c}', 'kind': 'learned', 'stake': x['cost'], 'saving': None,
                         'title': f"{project_short(p)}: {x['struggled']} of {x['n']} {CLASS_LABEL.get(c, c)} struggled ({rate:.0%}; the rest of this machine {base:.0%})",
                         'basis': f"{'; '.join(what)}. Learned from this machine's transcripts, not from the benchmark; hot at {threshold:.0%} or twice the rest",
                         'action': f"read what failed first (Details lists them); if it is the task and not the tools, step up in that project: /router prefer {c} {step} low; or give those calls more context in the prompt"})
    out_sess = []
    for p, s in (struggle.get('sessions') or {}).items():
        per = s['compactions'] / s['sessions'] if s['sessions'] else 0.0
        out_sess.append({'project': project_short(p), 'project_key': p, 'per_session': round(per, 1), **s})
        if s['compactions'] >= 3 and per >= 2:
            sugg.append({'id': f'boundary:{p}', 'kind': 'learned', 'stake': 0.0, 'saving': None,
                         'title': f"{project_short(p)}: sessions hit the context boundary {per:.0f} times each ({s['compactions']} in {s['sessions']} session{'s' if s['sessions'] != 1 else ''})",
                         'basis': "each boundary is a compaction: the model goes on from a summary and loses detail. Learned from this machine's transcripts",
                         'action': 'split the work into smaller sessions or hand the bulk to subagents; a model change does not move the boundary'})
    out_sess.sort(key=lambda s: -s['msgs'])
    return {'cells': out_cells, 'sessions': out_sess[:8], 'threshold': threshold}, sugg


TOKEN_KINDS = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')


def tok_total(t):
    return sum((t or {}).get(k, 0) or 0 for k in TOKEN_KINDS)


def price_tokens(tok, model):
    """What these tokens cost at MODEL's catalog rates; None when the model has no price."""
    entry = price.model_entry(model) if model else None
    if not entry or not tok:
        return None
    r = price.rates(entry)
    return (tok.get('input_tokens', 0) * r['in'] + tok.get('output_tokens', 0) * r['out']
            + tok.get('cache_read_input_tokens', 0) * r['cache_read'] + tok.get('cache_creation_input_tokens', 0) * r['write_5m'])


def dominant(models):
    """The model that did most of a side's calls (ties: the dearer), or None."""
    named = {m: n for m, n in (models or {}).items() if m and m != '?'}
    return max(named, key=lambda m: (named[m], m)) if named else None


def same_work(after_calls, ref_model):
    """The saving from the model change alone: the after side's own tokens priced at the reference model's rates,
    minus what they really cost. Task size cancels out; what a different model does with the same ask does not."""
    if not ref_model:
        return None
    cf = actual = 0.0
    n = 0
    for c in after_calls:
        p = price_tokens(c.get('tok'), ref_model)
        if p is None or c.get('cost') is None:
            continue
        cf += p; actual += c['cost']; n += 1
    return round(cf - actual, 2) if n else None


def realized_savings(usage, events, families):
    """What the transcripts show for each recorded change (tools/changes.py), in its own window: from the
    change to the next one (or now), against the stretch before it (back to the previous change, or the
    window's start). The cost per unit of the same work on each side, times the units after: one Agent
    call of a class, one main-session message. Positive is saved, negative is dearer. Beside each class,
    the family's last regression verdict: the check that the cheaper model still does the work here."""
    segs = usage.get('segments')
    if not events or not segs:
        return None
    checks = {f['name']: f.get('last_check') for f in families}
    calls = usage['subagents']['calls']
    now = datetime.datetime.now(datetime.timezone.utc)

    def side(cs):
        priced = [c for c in cs if c['cost'] is not None]
        toks = sum(tok_total(c.get('tok')) for c in cs)
        return {'n': len(cs), 'cost': round(sum(c['cost'] or 0 for c in cs), 2),
                'per_call': round(sum(c['cost'] for c in priced) / len(priced), 4) if priced else None,
                'tok_per_call': round(toks / len(cs)) if cs else None,
                'per_mtok': round(sum(c['cost'] for c in priced) / toks * 1e6, 3) if priced and toks else None,
                'models': dict(collections.Counter(c['model'] or '?' for c in cs))}

    def per_msg(p):
        return round(p['main_total'] / p['main_msgs'], 4) if p['main_msgs'] else None

    def main_tok(p):
        t = collections.Counter()
        for r in p['main_rows']:
            t.update(r.get('tok') or {})
        return dict(t)

    def main_same_work(after_seg, ref):
        """The after segment's main-session tokens priced at the reference (model, effort)'s model rates, minus actual."""
        if not ref:
            return None
        cf = price_tokens(main_tok(after_seg), ref[0])
        return round(cf - after_seg['main_total'], 2) if cf is not None else None

    def top_pair(p):
        rows = p['main_rows']
        return (max(rows, key=lambda r: r['msgs'])['model'], max(rows, key=lambda r: r['msgs'])['effort']) if rows else None

    def span(a, b):
        start = datetime.datetime.strptime(a[:16], '%Y-%m-%dT%H:%M').replace(tzinfo=datetime.timezone.utc)
        end = datetime.datetime.strptime(b[:16], '%Y-%m-%dT%H:%M').replace(tzinfo=datetime.timezone.utc) if b else now
        m = max(0, int((end - start).total_seconds() // 60))
        return f'{m} min' if m < 120 else f'{m / 60:.1f} h' if m < 48 * 60 else f'{m / 1440:.1f} days'

    # The baseline: everything before the first change. Each window is also measured against it, so the latest
    # window's baseline figures are what all the changes did together, while 'before' is the stretch just before.
    first = events[0]['at'][:16]
    base_calls = {cls: side([c for c in calls if c['class'] == cls and c['ts'] < first]) for cls in {c['class'] for c in calls}}
    base_main = per_msg(segs[0])
    base_top = top_pair(segs[0])
    windows = []
    for i, ev in enumerate(events):
        at, prev = ev['at'][:16], events[i - 1]['at'][:16] if i else ''
        nxt = events[i + 1]['at'] if i + 1 < len(events) else None
        classes = []
        for cls in sorted({c['class'] for c in calls}):
            before_calls = [c for c in calls if c['class'] == cls and prev <= c['ts'] < at]
            after_calls = [c for c in calls if c['class'] == cls and c['ts'] >= at and (nxt is None or c['ts'] < nxt[:16])]
            before, after = side(before_calls), side(after_calls)
            if not after['n']:
                continue
            per_call_saved = round((before['per_call'] - after['per_call']) * after['n'], 2) if before['per_call'] is not None and after['per_call'] is not None else None
            # The same work: the after calls' own tokens at the before side's dominant model, minus what they cost.
            sw = same_work(after_calls, dominant(before['models']))
            saved = sw if sw is not None else per_call_saved
            bpc = base_calls.get(cls, {}).get('per_call')
            vs_base = same_work(after_calls, dominant(base_calls.get(cls, {}).get('models')))
            if vs_base is None:
                vs_base = round((bpc - after['per_call']) * after['n'], 2) if bpc is not None and after['per_call'] is not None else None
            fam = CLASS_FAMILY.get(cls)
            classes.append({'class': cls, 'family': fam, 'before': before, 'after': after, 'saved': saved, 'saved_per_call': per_call_saved,
                            'same_work': sw is not None, 'ref_model': dominant(before['models']), 'vs_baseline': vs_base,
                            'baseline_per_call': bpc, 'check': checks.get(fam) if fam else None})
        b, a = segs[i], segs[i + 1]
        pb, pa = per_msg(b), per_msg(a)
        rb = {(r['model'], r['effort']): r for r in b['main_rows']}
        ra = {(r['model'], r['effort']): r for r in a['main_rows']}
        rows = [{'model': k[0], 'effort': k[1],
                 'before': {'msgs': rb[k]['msgs'], 'per_msg': round(rb[k]['cost'] / rb[k]['msgs'], 4)} if k in rb else None,
                 'after': {'msgs': ra[k]['msgs'], 'per_msg': round(ra[k]['cost'] / ra[k]['msgs'], 4)} if k in ra else None}
                for k in sorted(set(rb) | set(ra), key=lambda k: -((ra.get(k) or rb.get(k))['cost']))]
        per_msg_saved = round((pb - pa) * a['main_msgs'], 2) if pb is not None and pa is not None else None
        sw_main = main_same_work(a, top_pair(b))
        vs_base_main = main_same_work(a, base_top)
        if vs_base_main is None:
            vs_base_main = round((base_main - pa) * a['main_msgs'], 2) if base_main is not None and pa is not None else None
        bt, atk = tok_total(main_tok(b)), tok_total(main_tok(a))
        main = {'before': {'msgs': b['main_msgs'], 'cost': b['main_total'], 'per_msg': pb, 'tok_per_msg': round(bt / b['main_msgs']) if b['main_msgs'] else None},
                'after': {'msgs': a['main_msgs'], 'cost': a['main_total'], 'per_msg': pa, 'tok_per_msg': round(atk / a['main_msgs']) if a['main_msgs'] else None},
                'saved': sw_main if sw_main is not None else per_msg_saved, 'saved_per_msg': per_msg_saved, 'same_work': sw_main is not None,
                'ref': top_pair(b), 'rows': rows, 'baseline_per_msg': base_main, 'vs_baseline': vs_base_main}
        saved = round(sum(c['saved'] or 0 for c in classes) + (main['saved'] or 0), 2)
        vs_baseline = round(sum(c['vs_baseline'] or 0 for c in classes) + (main['vs_baseline'] or 0), 2)
        windows.append({'since': ev['at'], 'until': nxt, 'span': span(ev['at'], nxt), 'kind': ev['kind'], 'what': ev['detail'],
                        'projected': ev.get('projected'), 'days': days_since(ev['at'][:10], datetime.date.today()),
                        'classes': classes, 'main': main, 'saved': saved, 'vs_baseline': vs_baseline, 'baseline_since': usage.get('since')})
    windows.reverse()
    return {'latest': windows[0], 'history': windows}

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
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=USAGE_DAYS)).strftime('%Y-%m-%dT%H:%M')
    events = [e for e in changes.read() if e.get('at', '') >= cutoff]   # a change older than the window has no before side here
    usage = consumption.collect(USAGE_DAYS, splits=[e['at'] for e in events] or None)
    suggestions = suggest(usage, agents, routing)
    ovr = overrides.read()
    try:
        threshold = max(0.05, min(0.95, float(os.environ.get('MODEL_ROUTER_STRUGGLE', '25')) / 100))
    except ValueError:
        threshold = 0.25
    learned, learned_sugg = learned_from(usage.get('struggle') or {}, routing, ovr, threshold)
    suggestions += learned_sugg
    realized = realized_savings(usage, events, families)
    verdicts(suggestions, realized['latest'] if realized else None, USAGE_DAYS)
    gone = overrides.dismissed()
    for g in suggestions:
        g['dismissed'] = g['id'] in gone
    routed = routed_log.read(USAGE_DAYS)
    week_slots = slots(usage, routed, USAGE_DAYS)

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
    if git.get('dirty') and not os.environ.get('MODEL_ROUTER_CLONE'):   # the install's clone keeps local results uncommitted on purpose
        advice.append(f"{git['dirty']} uncommitted change(s) in the repo")
    for a in agents['routed']:
        if a['state'] == 'missing':
            advice.append(f"agent {a['file']} not installed yet (the repository ships it): /router apply")
        elif a['state'] == 'drifted':
            advice.append(f"agent {a['file']} is drifted (want {a['want']}, have {a['have']}): /router apply")
    usage_last = last_usage()
    clone = bool(os.environ.get('MODEL_ROUTER_CLONE'))   # the install's clone: the ledger prints to the pane, nothing is committed
    if not clone and (usage_last is None or (days_since(usage_last, today) or 0) > ADVICE_LEDGER_DAYS):
        advice.append(f"no usage ledger since {usage_last}: /router ledger")
    if not clone and timer.get('kind') == 'systemd' and not timer.get('installed'):
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
                      'by_class': {k: {'n': v['n'], 'cost': v['cost'], 'types': v['types'], 'models': v.get('models', {}), 'last': v.get('last', '')} for k, v in usage['subagents']['by_class'].items()},
                      'daily': usage.get('daily', []),
                      'previous': {'since': usage['previous']['since'], 'main_total': usage['previous']['main_total'], 'subagents_total': usage['previous']['subagents_total']}},
            'suggestions': suggestions, 'learned': learned, 'overrides': ovr, 'slots': week_slots,
            'routed_window': {'n': len(routed), 'kept': sum(1 for r in routed if r.get('decision') == 'kept')},
            'changes': {'events': events[-5:], 'realized': realized['latest'] if realized else None, 'history': realized['history'] if realized else []},
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
    r = (s.get('changes') or {}).get('realized')
    if r:
        out.append(f"since {r['since']} ({r['kind']}: {r['what']}), {r.get('span', '')}: {'saved' if r['saved'] >= 0 else 'cost up'} ${abs(r['saved']):.2f}"
                   + (f" (projected ${r['projected']})" if r.get('projected') is not None else ''))
        out.append('')
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
