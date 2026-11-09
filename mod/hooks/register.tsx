import { atom, read, update } from 'claude-code'
import type { Hook, Register } from 'claude-code'

import type { Job, Live, MainLive, RateLimit, Realized, RealizedMainSide, RealizedSide, Routed, RunningAgent, Status, StatusJson, Switch, Turn, Recent, RunEvent, RunMeta, SavedRun } from '../types'

type Dollar = Parameters<Hook<'session.start'>>[0]
type RoutingMode = 'ask' | 'auto' | 'off'

const PANE = 'model-router'
const MONITOR = 'model-router-monitor'
// status-3: `where` joined the value (which checkout served: the configured one, or the install's clone)
const status = atom({ plugin: 'model-router', key: 'status' } as const, null, { shape: 'status-3' })
const job = atom({ plugin: 'model-router', key: 'job' } as const, null, { shape: 'job-1' })
// routed-1: the Agent calls the router saw this session, newest last
const routed = atom({ plugin: 'model-router', key: 'routed' } as const, [] as Routed[], { shape: 'routed-1' })
// details-1: whether the pane shows the long sections (agents, dates, consumption, each suggestion's basis)
const details = atom({ plugin: 'model-router', key: 'details' } as const, false, { shape: 'details-1' })
// switches-1: prompts that read as a different task in a session re-reading a lot per turn, and what was done
const switches = atom({ plugin: 'model-router', key: 'switches' } as const, [] as Switch[], { shape: 'switches-1' })
const LIVE0: Live = { turns: [], escalated: {}, agents: {}, finished: [], doneN: 0, doneCost: 0, failedN: 0, stoppedN: 0, events: [], nextN: 1, runs: [], task: null, main: { busy: false, since: 0, lastAt: 0, recent: [] } }
// live-8: `main`, the main session's own state and tool tail, so the monitor has something to draw before any agent runs
const live = atom({ plugin: 'model-router', key: 'live' } as const, LIVE0, { shape: 'live-8' })
/** A second counter while agents run: the elapsed clocks and the spinner move between events. */
const tick = atom({ plugin: 'model-router', key: 'tick' } as const, 0, { shape: 'tick-1' })
/** The run monitor's view: the drawn graph, or the same run as text lines. */
const monitorView = atom({ plugin: 'model-router', key: 'monitorView' } as const, 'graph' as 'graph' | 'list', { shape: 'monitorView-1' })
/** The run the monitor shows: null is the current one (the latest with an agent at work, else the latest). */
const monitorRun = atom({ plugin: 'model-router', key: 'monitorRun' } as const, null as string | null, { shape: 'monitorRun-1' })
const monitorHistory = atom({ plugin: 'model-router', key: 'monitorHistory' } as const, false, { shape: 'monitorHistory-1' })
/** The runs saved on this machine, as last listed (tools/runs.py list --json). */
const savedRuns = atom({ plugin: 'model-router', key: 'savedRuns' } as const, [] as SavedRun[], { shape: 'savedRuns-1' })

// What the buttons and /router <verb> run, from the checkout's root. In the clone the plugin install
// made (`clone`), nothing is committed: the ledger prints its entry, the re-check keeps its results local.
const JOBS: Record<string, { title: string; argv: (python: string, clone: boolean) => string[] }> = {
  update: { title: 'regression check', argv: (py, clone) => [py, 'tools/update.py', '--sample', '6', ...(clone ? ['--no-commit'] : [])] },
  ledger: { title: 'usage ledger', argv: (py, clone) => [py, 'tools/ledger.py', clone ? '--stdout' : '--commit'] },
  apply: { title: 'apply agents', argv: py => [py, 'apply_agents.py'] },
  pull: { title: 'git pull', argv: () => ['git', 'pull', '--ff-only'] },
  // The agent files nothing called: a dry run lists them; `move` parks them in agents.unused (folders kept); `revert` brings them back.
  prune: { title: 'prune agents (dry run)', argv: py => [py, 'tools/prune_agents.py', '--dry-run'] },
  'prune-move': { title: 'prune agents', argv: py => [py, 'tools/prune_agents.py'] },
  'prune-revert': { title: 'restore the pruned agents', argv: py => [py, 'tools/prune_agents.py', '--revert'] },
  // Agent files from outside this repository: pinned to their source commit; a change there is shown with flags and taken only by name.
  'agents-pin': { title: 'pin the agent sources', argv: py => [py, 'tools/agent_sources.py', 'pin', '--repo'] },
  'agents-check': { title: 'check the agent sources', argv: py => [py, 'tools/agent_sources.py', 'check'] },
  'agents-update': { title: 'update the pinned agents', argv: py => [py, 'tools/agent_sources.py', 'update'] },
  'agents-list': { title: 'pinned agent sources', argv: py => [py, 'tools/agent_sources.py', 'list'] },
  doctor: { title: 'installation check', argv: py => [py, 'tools/status.py', '--doctor'] },
}
/** What /router prune <arg> runs: nothing or dry-run lists, move moves, revert restores; anything else is not a job. */
const pruneJob = (arg: string) => (arg === '' || arg === 'dry-run' ? 'prune' : arg === 'move' ? 'prune-move' : arg === 'revert' ? 'prune-revert' : null)
/** What /router agents <args> runs: pin <url>, check, update [file...] [--accept-flags], list; null when it is none of them. */
const agentsJob = (arg: string): { name: string; extra: string[] } | null => {
  const [sub, ...rest] = arg.split(/\s+/).filter(Boolean)
  if (sub === 'pin' && rest.length === 1 && /^(https?:\/\/|git@|\/|~|[A-Za-z]:\\)/.test(rest[0])) return { name: 'agents-pin', extra: rest }
  if (sub === 'check' && rest.length === 0) return { name: 'agents-check', extra: [] }
  if (sub === 'update' && rest.every(r => r === '--accept-flags' || /^[\w.-]+\.md$/.test(r))) return { name: 'agents-update', extra: rest }
  if ((sub === 'list' || sub === undefined) && rest.length === 0) return { name: 'agents-list', extra: [] }
  return null
}

// Python reads and writes UTF-8 everywhere (transcripts, ledger, git output), also on Windows,
// where its default is the console code page.
const PY_ENV = { PYTHONUTF8: '1' }
/** The scripts' environment; in the install's clone, MODEL_ROUTER_CLONE tells status.py its local results are uncommitted on purpose. */
const pyEnv = () => ({ ...PY_ENV, MODEL_ROUTER_STRUGGLE: String(struggleOption), ...(where ? { MODEL_ROUTER_CLONE: '1' } : {}) })

const clock = (ms: number) => {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const windowName = (kind: string) => (kind === 'five_hour' ? '5h' : kind === 'seven_day' ? '7d' : kind)

const limitsText = (limits: RateLimit[]) => limits.map(l => `${windowName(l.kind)} ${Math.round(l.percentUsed)}%`).join(' · ')

/** The status line under the prompt: the rate-limit windows, then what is worth doing. */
type StatusMode = 'full' | 'minimal' | 'off'
const savingsUpTo = (s: StatusJson, kind?: string) => (s.suggestions ?? []).filter(g => !kind || g.kind === kind).reduce((n, g) => n + (g.saving?.[1] ?? 0), 0)
/** The suggestions' upper savings by evidence kind, for the window that was: what it would have consumed less, not what will. */
const savingsMix = (s: StatusJson) => ['measured', 'extrapolated', 'unmeasured'].map(k => [k, savingsUpTo(s, k)] as const).filter(([, v]) => v >= 1).map(([k, v]) => `${money(v)} ${k}`).join(', ')
/** What the window consumed, main sessions and subagents. */
const spent = (s: StatusJson) => (s.usage ? s.usage.main_total + s.usage.subagents_total : 0)
/** `n` as a share of `of`, as "12%; " for a status line, or '' when there is nothing to divide by. */
const share = (n: number, of: number) => (of > 0 && n > 0 ? `${Math.round((100 * n) / of)}%; ` : '')

/** The status line under the prompt (the host prefixes the plugin's name): the rate-limit windows, what the
 * router did this session, what a change saved, what the suggestions add up to, what to check. Only what
 * changes a decision; `minimal` keeps the windows, the routed count and the to-check count. */
const statusLine = (s: StatusJson, limits: RateLimit[], routedN = 0, mode: StatusMode = 'full', ctx: number | null = null, model = '') => {
  const parts = [limitsText(limits)]
  // The context size always (when the host reports it); what re-reading it costs per turn, from the warning size on.
  if (ctx !== null) parts.push(ctx >= contextWarn ? `ctx ${kilo(ctx)} (${money((ctx / 1e6) * cacheRate(model))}/turn re-read)` : `ctx ${kilo(ctx)}`)
  if (routedN > 0) parts.push(`routed ${routedN}`)
  const r = s.changes?.realized
  if (mode === 'full' && r && r.saved !== 0 && !caveats(r)) parts.push(`${r.saved > 0 ? 'saved' : 'cost up'} ${money(Math.abs(r.saved))} since ${r.since.slice(5, 10)}`)
  const upTo = savingsUpTo(s)
  // The share of the window's spend says the same on a subscription, where the dollars are headroom, not a bill.
  if (mode === 'full' && upTo >= 1) parts.push(`up to ${money(upTo)} less last ${s.usage?.days ?? 30}d (${share(upTo, spent(s))}${money(savingsUpTo(s, 'measured'))} measured)`)
  if (s.advice.length > 0) parts.push(`${s.advice.length} to check`)
  if (parts.filter(Boolean).length === 0) parts.push('ok')
  return `${parts.filter(Boolean).join(' · ')} · /router`
}

/** One line of the pane or of /router check's text, with how the pane paints it. */
type Line = { text: string; color?: string; bold?: boolean; dim?: boolean; wrap?: boolean }
const line = (text: string, style: Omit<Line, 'text'> = {}): Line => ({ text, ...style })
const BLANK = line('')
/** The version of this module as loaded (tools/release.py holds it to plugin.json); the checkout's version comes with the status. */
const WIDGET_VERSION = '0.21.0'
/** Which widget runs: the loaded version, and a warning when the checkout already has another (a reload loads it). */
const versionLines = (s: StatusJson | null, full: boolean): Line[] => {
  const have = s?.widget?.version ?? null
  if (have && have !== WIDGET_VERSION) return [line(`widget ${WIDGET_VERSION} loaded; the checkout has ${have}: /reload-plugins loads it`, { color: 'yellow' })]
  return full ? [line(`widget ${WIDGET_VERSION} loaded`, { dim: true })] : []
}

const BLOCKS = '▁▂▃▄▅▆▇█'
/** A sparkline: one block per value, scaled to the largest. */
const spark = (values: number[]) => {
  const max = Math.max(0, ...values)
  return values.map(v => BLOCKS[max > 0 ? Math.min(7, Math.round((v / max) * 7)) : 0]).join('')
}
/** A horizontal bar of `width` cells, `frac` of them full. */
const bar = (frac: number, width = 10) => {
  const n = Math.max(0, Math.min(width, Math.round((Number.isFinite(frac) ? frac : 0) * width)))
  if (n === 0 && frac > 0) return '▏' + '░'.repeat(width - 1)
  return '█'.repeat(n) + '░'.repeat(width - n)
}
const money = (n: number) => `$${n >= 10 ? n.toFixed(0) : n.toFixed(2)}`
const fine = (n: number) => (n < 1 ? `$${n.toFixed(4)}` : money(n))
const when = (iso: string) => {
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${clock(d.getTime())}`
}
const saidSaved = (n: number | null) => (n === null ? 'no basis' : `${n >= 0 ? 'saved' : 'cost up'} ${money(Math.abs(n))}`)
/** What keeps a change's number from meaning anything yet: too few units, or a main-session change not in effect. */
const caveats = (r: Realized) => {
  const calls = r.classes.reduce((n, c) => n + c.after.n, 0)
  const out: string[] = []
  if (r.main.after.msgs < 50 && calls < 5) out.push(`too little yet: ${r.main.after.msgs} msgs, ${calls} agent calls`)
  const top = (side: 'before' | 'after') => r.main.rows.filter(x => x[side]).sort((a, b) => (b[side]!.msgs - a[side]!.msgs))[0]
  const tb = top('before'), ta = top('after')
  if (r.kind === 'mark' && tb && ta && tb === ta) out.push('main sessions run on the same model and effort as before, so the change is not in effect')
  return out.length ? ` (${out.join('; ')})` : ''
}
const savedColor = (n: number | null) => (n === null ? undefined : n > 0 ? 'green' : n < 0 ? 'yellow' : undefined)
/** What the measured suggestions project per window: recorded with a routing change, to compare with what came. */
const measuredProjected = (s: StatusJson | null | undefined) => (s?.suggestions ?? []).filter(g => g.kind === 'measured').reduce((n, g) => n + (g.saving?.[1] ?? 0), 0)
const rateFrac = (rate: string | null) => {
  const m = rate?.match(/^(\d+)\/(\d+)$/)
  return m && Number(m[2]) > 0 ? Number(m[1]) / Number(m[2]) : null
}
const rateColor = (f: number | null) => (f === null ? undefined : f >= 0.9 ? 'green' : f >= 0.7 ? 'yellow' : 'red')
const KIND_COLOR: Record<string, string | undefined> = { measured: 'green', extrapolated: 'cyan', learned: 'magenta' }

/** The rate-limit windows as bars, one line each. */
const limitLines = (limits: RateLimit[]): Line[] =>
  limits.map(l =>
    line(`${windowName(l.kind).padEnd(4)}${bar(l.percentUsed / 100, 20)} ${String(Math.round(l.percentUsed)).padStart(3)}% used${l.resetsAt ? ', resets ' + clock(Date.parse(l.resetsAt)) : ''}`,
      { color: l.percentUsed >= 80 ? 'red' : l.percentUsed >= 50 ? 'yellow' : 'green', bold: true }))

/** The suggestions in the order the pane shows them: largest saving first, a learned one by what its calls cost,
 * unknown last; dismissed ones out unless asked. */
const rank = (g: { saving: [number, number] | null; kind: string; stake: number }) => g.saving?.[1] ?? (g.kind === 'learned' ? g.stake : -1)
const orderedSuggestions = (s: StatusJson, withDismissed = false) =>
  [...(s.suggestions ?? [])].filter(g => withDismissed || !g.dismissed).sort((a, b) => rank(b) - rank(a))

/** Two bars side by side: before and after, on the same scale. */
const pair = (before: number | null, after: number | null, width = 8) => {
  const top = Math.max(before ?? 0, after ?? 0)
  return `${bar(top > 0 && before !== null ? before / top : 0, width)} -> ${bar(top > 0 && after !== null ? after / top : 0, width)}`
}
const kilo = (n: number | null | undefined) => (n == null ? '-' : n >= 1000 ? `${Math.round(n / 1000)}k` : String(n))
const mtok = (x: { per_msg: number | null; tok_per_msg?: number | null }) => (x.per_msg != null && x.tok_per_msg ? (x.per_msg / x.tok_per_msg) * 1e6 : null)
const realText = (g: { real?: { per_window: number | null; state: string } }, days: number) => {
  const r = g.real
  if (!r) return ''
  if (r.per_window !== null) return `real ${r.per_window >= 0 ? '+' : '-'}${money(Math.abs(r.per_window))}/${days}d ${r.state}`
  return r.state.replace(/:.*$/, '')
}

/** The pane's body and /router check's text. `full` (the text, or the pane with Details on) adds the long
 * sections; the pane's default is a glance: numbers that compare, one line each. */
const summaryLines = (s: StatusJson, at: number, seen: Routed[] = [], where = '', full = true, sw: Switch[] = [], ctxNow: number | null = null, modelNow = ''): Line[] => {
  const g = s.repo
  const sync = !g.is_repo
    ? 'not a git checkout'
    : [g.dirty ? `${g.dirty} dirty` : 'clean',
       g.behind ? `${g.behind} behind` : g.behind === 0 ? (g.fetched ? 'up to date' : 'up to date at last fetch') : 'origin unknown',
       g.ahead ? `${g.ahead} ahead` : '']
        .filter(Boolean).join(', ')
  const reg = s.ledger.regress_last
  const u = s.usage
  const days = u?.days ?? 30
  const total = u ? u.main_total + u.subagents_total : 0
  const lines: Line[] = full
    ? [line(`read ${clock(at)} · ${s.platform} · Claude Code ${s.claude ?? 'not found'} · routing v${s.routing.version}, decided ${s.routing.decided}`, { dim: true }),
       line(`repo ${g.head ?? '-'} · ${sync}${where ? ' · ' + where : ''}`, { dim: true })]
    : [line(`read ${clock(at)} · Claude Code ${s.claude ?? 'not found'} · routing v${s.routing.version} · repo ${g.head ?? '-'} ${sync}${where ? ' · ' + where : ''}`, { dim: true })]
  const cells = s.learned?.cells ?? []
  const struggled = cells.reduce((n, c) => n + c.struggled, 0)
  const callsN = cells.reduce((n, c) => n + c.n, 0)
  if (u) {
    const prev = u.previous.main_total + u.previous.subagents_total
    const daily = u.daily ?? []
    lines.push(line(`spend ${days}d ${daily.length ? spark(daily.map(d => d.cost)) + ' ' : ''}${money(total)} (main ${money(u.main_total)}, agents ${money(u.subagents_total)}) · prev ${money(prev)} · struggled ${struggled}/${callsN} calls · routed ${s.routed_window?.n ?? 0}`, { bold: true }))
  }
  // The triple check after a change: projected (the benchmark), realized (your transcripts since), regress (the family here).
  // Each change against the stretch before it (what it did) and against the baseline before the first change (what all did).
  const r = s.changes?.realized
  if (r) {
    const checks = r.classes.filter(c => c.family && c.check).map(c => `${c.family} ${c.check!.verdict}`)
    const span = r.span ? `, ${r.span}${r.until ? ' until the next change' : ' so far'}` : ''
    const base = r.vs_baseline !== undefined ? ` · vs baseline (before ${r.baseline_since ?? 'the first change'}): ${saidSaved(r.vs_baseline)}` : ''
    lines.push(BLANK, line(`since ${when(r.since)} (${r.kind}: ${r.what})${span}: vs previous ${saidSaved(r.saved)}${base}${caveats(r)}${r.projected != null ? ` · projected ${money(r.projected)} per ${days}d` : ''}${checks.length ? ` · regress ${checks.join(', ')}` : ''}`,
      { color: caveats(r) ? undefined : savedColor(r.saved), bold: true, wrap: true }))
    const shown = full ? r.classes : r.classes.slice(0, 3)
    // Price per million tokens before and after: task size cancels out of this column. The saving is the same-work
    // figure (the after tokens priced at the model used before, minus what they cost); the size change is shown as tokens per unit.
    for (const c of shown) {
      const pb = c.before.per_mtok ?? null, pa = c.after.per_mtok ?? null
      lines.push(line(`  ${c.class.padEnd(19)}$/Mtok ${(pb ?? 0).toFixed(2).padStart(7)} -> ${(pa ?? 0).toFixed(2).padEnd(7)} ${pair(pb, pa)}  ${saidSaved(c.saved).padEnd(14)} ${c.same_work ? 'same work' : 'per call'} · ${c.after.n} after · ${kilo(c.before.tok_per_call)} -> ${kilo(c.after.tok_per_call)} tok/call${c.vs_baseline != null ? ` · vs baseline ${saidSaved(c.vs_baseline)}` : ''}`, { color: savedColor(c.saved) }))
    }
    const m = r.main
    const mb = mtok(m.before), ma = mtok(m.after)
    lines.push(line(`  ${'main sessions'.padEnd(19)}$/Mtok ${(mb ?? 0).toFixed(2).padStart(7)} -> ${(ma ?? 0).toFixed(2).padEnd(7)} ${pair(mb, ma)}  ${saidSaved(m.saved).padEnd(14)} ${m.same_work ? 'same work' : 'per msg'} · ${m.after.msgs} msgs after · ${kilo(m.before.tok_per_msg)} -> ${kilo(m.after.tok_per_msg)} tok/msg${m.vs_baseline != null ? ` · vs baseline ${saidSaved(m.vs_baseline)}` : ''}`, { color: savedColor(m.saved) }))
  } else if (full) {
    lines.push(BLANK, line('no change recorded yet: Apply agents (when it changes a file), /router routing auto, /router prefer and /router mark <note> start the before/after count', { dim: true }))
  }
  // Suggestions: estimate against real, one line each, numbered so /router dismiss <n> can hide one you judge wrong.
  const sug = orderedSuggestions(s)
  const gone = (s.suggestions ?? []).filter(x => x.dismissed).length
  const upTo = savingsUpTo(s)
  lines.push(BLANK, line(sug.length === 0 ? `suggestions: none${gone ? ` (${gone} dismissed)` : ''}`
    : full ? `suggestions (the last ${days} days could have consumed up to ${money(upTo)} less of ${money(total)}${total > 0 && upTo > 0 ? ` (${Math.round((100 * upTo) / total)}%)` : ''}: ${savingsMix(s) || 'nothing measured'}${gone ? `; ${gone} dismissed` : ''}):`
    : `suggestions · up to ${money(upTo)} less last ${days}d${total > 0 && upTo > 0 ? ` (${Math.round((100 * upTo) / total)}%)` : ''} · ${sug.length} (Details has basis and action):`, { bold: true }))
  const GLANCE = 4
  const shownSug = full ? sug : sug.slice(0, GLANCE)
  shownSug.forEach((g, i) => {
    const est = g.saving === null ? 'est -' : `est ${money(g.saving[1])}/${days}d`
    const head = `${String(i + 1).padStart(2)}. [${g.kind}]`.padEnd(19)
    lines.push(line(`${head}${g.title.slice(0, 58).padEnd(59)} ${est.padEnd(16)} ${realText(g, days)}`, { color: KIND_COLOR[g.kind] }))
    if (full) lines.push(line(`    basis: ${g.basis}`, { dim: true }), line(`    do: ${g.action}`, { dim: true }))
  })
  if (shownSug.length < sug.length) lines.push(line(`  … ${sug.length - shownSug.length} more (Details)`, { dim: true }))
  // Families: one line in the glance, the table under Details.
  const decided = s.families.filter(f => f.model)
  const here = decided.filter(f => f.can_run)
  const notOk = here.filter(f => f.last_check && f.last_check.verdict !== 'ok' && !f.last_check.verdict.startsWith('skipped'))
  if (full || notOk.length) lines.push(BLANK, line(`families: ${decided.length} decided · ${here.length} checkable here${notOk.length ? ` · last check not ok: ${notOk.map(f => f.name).join(', ')}` : here.length ? ' · last checks ok' : ''}${full ? '' : ' (table in Details)'}`, { bold: true, color: notOk.length ? 'yellow' : undefined }))
  if (full) {
    lines.push(line(`${'family'.padEnd(13)}${'default'.padEnd(19)}${'ok'.padEnd(11)}${'evidence'.padEnd(9)}${'$/ok'.padEnd(8)}${'here'.padEnd(5)}last check`, { bold: true }))
    for (const f of s.families) {
      const d = f.model ? `${f.model} ${f.effort}${f.variant ? ' +' + f.variant : ''}` : 'none'
      const lc = f.last_check
      const last = lc ? (lc.sample ? `${lc.verdict} ${lc.successes}/${lc.sample}` : lc.verdict) : '-'
      const cost = f.cost_per_success === null ? '-' : f.cost_per_success.toFixed(4)
      const fr = rateFrac(f.rate)
      lines.push(line(`${f.name.padEnd(13)}${d.padEnd(19)}${fr === null ? '-'.padEnd(10) : bar(fr)} ${(f.rate ?? '-').padEnd(9)}${cost.padEnd(8)}${(f.can_run ? 'yes' : 'no').padEnd(5)}${last}`,
        { color: rateColor(fr), dim: fr === null }))
    }
    const present = s.agents.routed.filter(x => x.state !== 'absent')
    const applied = present.filter(x => x.state === 'applied').length
    const absent = s.agents.routed.length - present.length
    lines.push(
      line(`agents: ${s.agents.files} files, ${s.agents.unused} unused; routed ${applied}/${present.length} applied${absent ? `, ${absent} not on this machine` : ''}`, { dim: true }),
      line(`prices verified ${s.catalog.verified_oldest ?? '?'} (${s.catalog.age_days ?? '?'} days) · ledger: usage ${s.ledger.usage_last ?? 'none'}, regress ${reg?.date ?? 'none'} on ${reg?.claude ?? '-'}`, { dim: true }),
      line(`timer: ${s.timer.next ? 'next ' + s.timer.next : s.timer.note ?? 'none'}`, { dim: true }),
    )
  }
  lines.push(BLANK)
  const more = (n: number) => line(`  … ${n} more (Details)`, { dim: true })
  if (s.advice.length === 0) lines.push(line('nothing to check', { color: 'green', bold: true }))
  else {
    const shown = full ? s.advice : s.advice.slice(0, 3)
    lines.push(line('to check:', { bold: true }), ...shown.map(a => line(`  - ${a}`, { color: 'yellow', wrap: true })))
    if (shown.length < s.advice.length) lines.push(more(s.advice.length - shown.length))
  }
  if (full && s.slots?.length) {
    const top = Math.max(0, ...s.slots.map(x => x.spend))
    lines.push(BLANK, line(`by week (oldest first): ${'spend'.padStart(8)}  calls  struggled  routed`, { bold: true }))
    for (const x of s.slots) lines.push(line(`  ${x.since.slice(5)} to ${x.until.slice(5)}  ${bar(top > 0 ? x.spend / top : 0, 12)} ${money(x.spend).padStart(6)}  ${String(x.calls).padStart(5)}  ${String(x.struggled).padStart(9)}  ${String(x.routed).padStart(6)}`))
  }
  if (u && full) {
    lines.push(BLANK, line(`consumption, last ${days} days since ${u.since} (catalog $ = headroom on a subscription; a floor: the side requests Claude Code makes are not in the transcripts): main ${money(u.main_total)} (output ${money(u.main_out_cost)}) · subagents ${money(u.subagents_total)} in ${u.subagent_calls} calls`, { bold: true }))
    const top = Math.max(0, ...u.main_rows.map(x => x.cost), ...Object.values(u.by_class).map(b => b.cost))
    for (const x of u.main_rows.slice(0, 6)) {
      lines.push(line(`  ${x.model.padEnd(30)}${x.effort.padEnd(8)}${bar(top > 0 ? x.cost / top : 0, 20)} ${money(x.cost).padStart(5)}  ${String(x.msgs).padStart(5)} msgs`))
    }
    if (u.main_rows.some(x => x.effort === '?')) lines.push(line('  effort ? = not recorded in the transcript: the default effort of the session at the time', { dim: true }))
    for (const [cls, b] of Object.entries(u.by_class).sort((a, b) => b[1].cost - a[1].cost)) {
      const types = Object.entries(b.types).sort((a, b) => b[1] - a[1])
      const shown = types.slice(0, 3).map(([t, n]) => `${t} x${n}`).join(', ') + (types.length > 3 ? ` +${types.length - 3} more` : '')
      lines.push(line(`  ${('agents ' + cls).padEnd(30)}${''.padEnd(8)}${bar(top > 0 ? b.cost / top : 0, 20)} ${money(b.cost).padStart(5)}  ${String(b.n).padStart(5)} calls${b.last ? `  last ${b.last.slice(0, 10)}` : ''}`))
      lines.push(line(`${''.padEnd(40)}${shown}`, { dim: true }))
    }
  }
  if (r && full) {
    const earlier = (s.changes?.history ?? []).slice(1, 6)
    if (earlier.length) {
      lines.push(BLANK, line('  earlier changes, each in its own window (vs the stretch before it; vs the baseline):', { dim: true }))
      for (const h of earlier) {
        lines.push(line(`    ${when(h.since)} (${h.kind}: ${h.what})${h.span ? ` · ${h.span}` : ''}: ${saidSaved(h.saved)}${h.vs_baseline != null ? `; vs baseline ${saidSaved(h.vs_baseline)}` : ''}${caveats(h)}${h.projected != null ? ` · projected ${money(h.projected)}` : ''}`, { color: caveats(h) ? undefined : savedColor(h.saved), wrap: true }))
      }
    }
    const dismissed = (s.suggestions ?? []).filter(x => x.dismissed)
    if (dismissed.length) lines.push(line(`  dismissed by you: ${dismissed.map(x => x.id).join(', ')} (/router undismiss <id>)`, { dim: true }))
  }
  const learned = s.learned
  if (full && learned) {
    const hot = learned.cells.filter(c => c.hot || c.override)
    const mine = Object.entries(s.overrides?.[projectKey] ?? {})
    lines.push(BLANK, line(`learned on this machine (hot at ${Math.round(learned.threshold * 100)}% struggled or twice the rest; struggled = re-issued, 3+ tool errors inside, or failed):`, { bold: true }))
    if (hot.length === 0) lines.push(line('  no project and class of call struggles more than the rest of this machine', { dim: true }))
    for (const c of hot) {
      lines.push(line(`  ${c.project} · ${c.class}: ${c.struggled} of ${c.n} struggled (${Math.round(c.rate * 100)}%; rest ${Math.round(c.baseline * 100)}%)${c.override ? ` · override ${c.override.model} ${c.override.effort}` : ''}`, { color: c.override ? undefined : 'magenta' }))
      for (const ex of c.examples.slice(0, 3)) lines.push(line(`      ${ex}`, { dim: true }))
    }
    for (const sx of learned.sessions.filter(x => x.compactions > 0).slice(0, 4)) {
      lines.push(line(`  ${sx.project}: ${sx.sessions} session${sx.sessions === 1 ? '' : 's'}, ${sx.msgs} msgs, ${sx.errors} tool errors, ${sx.compactions} context boundaries (${sx.per_session} per session)${sx.ctx_per_msg ? ` · ${kilo(sx.ctx_per_msg)} tokens re-read per msg, ${money(sx.read_cost ?? 0)} in cache reads` : ''}${sx.idle_returns ? ` · ${sx.idle_returns} idle returns re-cached ${money(sx.idle_cost ?? 0)}` : ''}`, { dim: true }))
    }
    lines.push(line(mine.length ? `  this project's overrides: ${mine.map(([c, o]) => `${c} -> ${o.model} ${o.effort}`).join(', ')} (/router prefer clear <class>)` : '  this project: no override (/router prefer <class> <model> <effort> sets one)', { dim: true }))
  }
  if (sw.length > 0 || ctxNow !== null) {
    const compacted = sw.filter(x => x.action === 'compacted').length
    lines.push(BLANK, line(`context: ${ctxNow !== null ? `${kilo(ctxNow)} tokens re-read every turn (${money((ctxNow / 1e6) * cacheRate(modelNow))} per turn)` : 'size unknown'}${sw.length ? ` · ${sw.length} task switch${sw.length === 1 ? '' : 'es'} seen, ${compacted} compacted` : ''}${ctxNow !== null && ctxNow >= contextWarn ? ' · a new window starts at 23k' : ''}`,
      { bold: true, color: ctxNow !== null && ctxNow >= contextWarn ? 'yellow' : undefined }))
    if (full) for (const x of sw.slice(-5)) lines.push(line(`  ${clock(x.at)}  ${kilo(x.ctx)} tokens: ${x.why} -> ${x.action}`, { dim: true }))
  }
  if (seen.length > 0) {
    const kept = seen.filter(x => x.decision === 'kept').length
    lines.push(BLANK, line(`routed this session: ${seen.length - kept} routed, ${kept} kept (mode ${routingMode}; /router routing ask|auto|off${full ? '' : '; Details lists them'})`, { bold: true }))
    if (full) for (const x of seen.slice(-8)) lines.push(line(`  ${clock(x.at)}  ${x.agent}: ${x.from} -> ${x.to}  [${x.family}] ${x.decision}  ${x.description}`, { dim: x.decision === 'kept' }))
  }
  return lines
}

// Set by register() from the mod's options; module variables start over on a reload, as register runs again.
let repoOption = '~/Projects/Github/model-router'
let pythonOption = ''
let refreshMinutes = 30
let repo = repoOption
// '' when the configured checkout serves; 'marketplace clone' when the clone the plugin install made does.
let where = ''
let python = ''
/** The model's family word: haiku, sonnet, opus, fable; else the id without its prefix. */
const shortModel = (m: string) => Object.keys(PRICES).find(k => m.toLowerCase().includes(k)) ?? m.replace(/^claude-/, '')
const SPIN = '▖▘▝▗'
const secs = (ms: number) => (ms < 60000 ? `${Math.max(0, Math.round(ms / 1000))}s` : `${Math.floor(ms / 60000)}m${String(Math.round((ms % 60000) / 1000)).padStart(2, '0')}`)
/** The agents of this session, the way a connection monitor lists connections: one row each, children under their parent,
 * the spinner in the header alone, a row with no request for a minute in yellow, the glance capped at a few rows. */
const QUIET_MS = 60000
const GLANCE_ROWS = 6
const agentsLines = (lv: Live, now: number, full: boolean): Line[] => {
  const running = Object.values(lv.agents)
  // Nothing has run yet: the full pane (and /router check) still names the block so a dev knows where agents will appear; the glance stays short.
  if (running.length === 0 && lv.doneN === 0) return full ? [line('agents  none running yet this session; subagents appear here as rows: type, model effort, family, task, requests, elapsed', { dim: true })] : []
  const spin = running.length ? SPIN[Math.floor(now / 1000) % SPIN.length] + ' ' : ''
  const head = `${spin}agents running ${running.length}` + (lv.doneN ? ` · done ${lv.doneN} (${money(lv.doneCost)}${lv.failedN ? `, ${lv.failedN} failed` : ''}${lv.stoppedN ? `, ${lv.stoppedN} stopped` : ''})` : '')
  const lines = [line(head + (full ? ' · graph: /router monitor' : ''), { bold: true, color: running.length ? 'cyan' : undefined })]
  const row = (a: RunningAgent, depth: number) => {
    const quiet = a.done === null && now - a.lastStepAt > QUIET_MS
    const mark = a.done === null ? '|' : bad(a) ? '✗' : '✓'
    const lead = depth ? '  '.repeat(depth) + '└ ' : '  '
    const who = `${lead}${mark} ${a.type}`.padEnd(26)
    const what = `${shortModel(a.model)} ${a.effort || ''}`.trim().padEnd(12) + (a.family ?? 'unmeasured').padEnd(15) + a.description.slice(0, 34).padEnd(35)
    const tail = `${String(a.steps).padStart(3)} step${a.steps === 1 ? ' ' : 's'} ${secs((a.done ?? now) - a.startedAt).padStart(6)}` + (a.cost !== null ? `  ${money(a.cost)}` : quiet ? '  quiet' : '')
    return line(`${who}${what}${tail}`, { dim: a.done !== null && !bad(a), color: bad(a) ? 'red' : quiet ? 'yellow' : undefined })
  }
  const rows: Line[] = []
  const tree = (parent: string | null, depth: number) => {
    for (const a of running.filter(x => x.parent === parent).sort((x, y) => x.startedAt - y.startedAt)) {
      rows.push(row(a, depth))
      tree(a.id, depth + 1)
    }
  }
  tree(null, 0)
  for (const a of running.filter(x => x.parent && !lv.agents[x.parent])) rows.push(row(a, 0))   // a parent already gone: at the top
  if (!full && rows.length > GLANCE_ROWS) {
    const slowest = Math.max(...running.map(a => now - a.startedAt))
    lines.push(...rows.slice(0, GLANCE_ROWS - 1), line(`  +${rows.length - GLANCE_ROWS + 1} more running, slowest ${secs(slowest)} (Details)`, { dim: true }))
  } else lines.push(...rows)
  for (const a of lv.finished.slice(full ? -6 : -2)) lines.push(row(a, 0))
  return lines
}

let routingMode: RoutingMode = 'ask'
type MainEffortMode = 'off' | 'advise' | 'auto'
let mainEffortMode: MainEffortMode = 'advise'
/** The main loop's turn in progress: what its prompt read as and what happened inside it; dropped when the turn ends. */
type Plan = { family: string | null; effort: string | null; sessionEffort: string; applied: string | null; wouldApply: string | null; errors: number; agentCalls: number; routed: number; gear: Turn['gear'] }
const plans = new Map<string, Plan>()
let currentTurn = ''
/** Two Agent descriptions with mostly the same words: the second is a re-issue of the first. */
const similar = (a: string, b: string) => {
  const w = (t: string) => new Set(t.toLowerCase().split(/[^a-z0-9]+/).filter(x => x.length > 3))
  const A = w(a), B = w(b)
  if (A.size === 0 || B.size === 0) return a.trim().toLowerCase() === b.trim().toLowerCase()
  let both = 0
  for (const x of A) if (B.has(x)) both++
  return both / Math.max(A.size, B.size) >= 0.5
}
let statusMode: StatusMode = 'full'
let struggleOption = 25
let contextWarn = 100000   // tokens re-read per turn from which a task switch is worth a word

// ---- Context drift: a prompt that reads as a different task, in a session that already re-reads a lot every turn.
// The cost is the API's, the same in the terminal, the desktop app and VS Code: every turn re-reads the whole session
// from the server cache. A new window or terminal is a new session with a small context; that is the fix.
const STOP = new Set(['that', 'this', 'with', 'from', 'have', 'what', 'when', 'then', 'than', 'they', 'them', 'there', 'here', 'will', 'would', 'should',
  'could', 'about', 'into', 'just', 'like', 'also', 'been', 'were', 'your', 'make', 'need', 'want', 'some', 'more', 'most', 'very', 'only', 'same', 'each',
  'other', 'which', 'while', 'where', 'does', 'done', 'doing', 'after', 'before', 'again', 'still', 'please', 'lets', 'check', 'look', 'think', 'maybe'])
const WORDS = /[a-z]{4,}/g
const TICKETS = /\b[A-Z][A-Z0-9]+-\d+\b|#\d{2,}|\bissues?\s+\d+/g
const CACHE_READ: Record<string, number> = { fable: 0.25, opus: 0.2, sonnet: 0.1, haiku: 0.01 }   // $ per million tokens, catalog cache-read prices
const PREFIX_TOKENS = 23000   // what a fresh session re-reads per turn here (results/prefix)
const vocab = new Set<string>()
const ticketsSeen = new Set<string>()
let vocabSeeded = false
let lastSwitchTurn = -100
let driftOff = false
// A compaction the person chose at a task switch: the host runs it after the turn, not under the prompt hook that asked.
let pendingCompact: string | null = null
const wordsOf = (t: string) => new Set((t.toLowerCase().match(WORDS) ?? []).filter(w => !STOP.has(w)))
const ticketsOf = (t: string) => new Set((t.match(TICKETS) ?? []).map(x => x.toUpperCase().replace(/\s+/g, ' ')))
const cacheRate = (model: string): number => CACHE_READ[Object.keys(CACHE_READ).find(k => model.toLowerCase().includes(k)) ?? 'opus'] ?? 0.2
/** $ per million tokens by model family, catalog/models.json: input, output, cache read, cache write at the 1h multiplier (2x input), what a session on a subscription's cache pays. */
const PRICES: Record<string, { in: number; out: number; read: number; write: number }> = {
  fable: { in: 10, out: 50, read: 0.25, write: 20 }, opus: { in: 4, out: 20, read: 0.2, write: 8 },
  sonnet: { in: 2, out: 10, read: 0.1, write: 4 }, haiku: { in: 0.1, out: 0.5, read: 0.01, write: 0.2 },
}
const priceOf = (model: string) => PRICES[Object.keys(PRICES).find(k => model.toLowerCase().includes(k)) ?? 'opus'] ?? PRICES.opus!
type Tokens = { input_tokens: number; output_tokens: number; cache_read_input_tokens: number; cache_creation_input_tokens: number }
const turnCost = (u: Tokens & { model: string }) => {
  const pr = priceOf(u.model)
  return (u.input_tokens * pr.in + u.output_tokens * pr.out + u.cache_read_input_tokens * pr.read + u.cache_creation_input_tokens * pr.write) / 1e6
}
/** results/cell8: a turn's cost at this effort against the same work at low (high 1.06-1.16x, xhigh 1.30-1.52x; midpoints). The saving an effort step down is worth, on the output. */
const EFFORT_RATIO: Record<string, number> = { low: 1, medium: 1.05, high: 1.11, xhigh: 1.41, max: 1.41 }
const effortSaving = (t: Turn) => {
  const from = EFFORT_RATIO[t.sessionEffort] ?? 1, to = EFFORT_RATIO[t.effort] ?? 1
  return from > to ? ((t.out * priceOf(t.model).out) / 1e6) * (from / to - 1) : 0
}
const ESCALATE_ERRORS = 3      // tool errors within a turn that send its effort back up: the struggle signal the transcripts learn from
const REISSUE_MS = 10 * 60000  // an Agent call of the same family and agent within this of a routed one, with the same words, is a re-issue

/** The session as it runs, at the top of the pane: a few lines a person doing the work can read in a glance. */
/** A local date and time, YYYY-MM-DD HH:MM: the same clock the run folders are named by. */
const stamp = (ms: number) => {
  const d = new Date(ms)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${clock(ms)}`
}
const clockS = (ms: number) => {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
/** One tool call in a few words, for the monitor's tail. */
const toolText = (e: Record<string, unknown>): string => {
  const str = (k: string) => (typeof e[k] === 'string' ? (e[k] as string) : '')
  switch (e.tool) {
    case 'Bash': return `$ ${str('command').replace(/\s+/g, ' ').slice(0, 70)}`
    case 'Read': case 'Edit': case 'Write': case 'NotebookEdit': return `${e.tool} ${str('file_path') || str('notebook_path')}`
    case 'Grep': return `Grep "${str('pattern')}"${str('path') ? ' ' + str('path') : ''}`
    case 'Glob': return `Glob ${str('pattern')}`
    case 'WebSearch': return `WebSearch "${str('query')}"`
    case 'WebFetch': return `WebFetch ${str('url')}`
    case 'Agent': return `Agent ${str('description')}`
    default: return String(e.tool)
  }
}
/** The run as a graph: the main session, then each agent as a box under the one that spawned it, the arrow weighted by the
 * context it was sent; below, the live tail of the agents at work and the run's event log. All of it text, one line one row. */
const BOX_W = 48
const weightOf = (ctx: number) => (ctx >= 16000 ? '━' : ctx >= 4000 ? '─' : '┄')
const monitorLines = (lvAll: Live, now: number, runId: string | null = null): Line[] => {
  const lv = scopeOf(lvAll, runId)
  const running = Object.values(lv.agents)
  const { all, kids } = treeOf(lv)
  const spin = running.length ? SPIN[Math.floor(now / 1000) % SPIN.length] + ' ' : ''
  const head = `${spin}agent run · ${running.length} running · ${lv.doneN} done (${money(lv.doneCost)}${lv.failedN ? `, ${lv.failedN} failed` : ''}${lv.stoppedN ? `, ${lv.stoppedN} stopped` : ''})`
  const out: Line[] = [line(head, { bold: true, color: running.length ? 'cyan' : undefined }), line(runLine(lvAll, runId), { dim: true })]
  // Before any agent: the main session is drawn alone, with its state and its own tool tail; agents hang under it as they spawn.
  if (all.length === 0) out.push(line('no agent spawned yet; Agent calls hang under the session box as they spawn', { dim: true }))
  // Every line of a box is BOX_W + 2 columns: ┌ title ─┐ / │ text │ / └──┘.
  const inner = (t: string) => `│ ${t.slice(0, BOX_W - 2).padEnd(BOX_W - 2)} │`
  const top = (title: string) => { const t = title.slice(0, BOX_W - 3); return `┌ ${t} ${'─'.repeat(BOX_W - 2 - t.length)}┐` }
  const bottom = (hasChildren: boolean) => (hasChildren ? `└${'─'.repeat(9)}┬${'─'.repeat(BOX_W - 10)}┘` : `└${'─'.repeat(BOX_W)}┘`)   // the ┬ sits over the children's trunk, 10 columns in
  out.push(line('[ Run graph ]', { bold: true }))
  // Draw with a trunk: lines of a child's box after the first carry the trunk mark when siblings follow.
  const drawn: Line[] = []
  const draw = (a: RunningAgent | null, prefix: string, arrow: string, trunk: boolean) => {
    const children = kids(a)
    const cont = prefix + (trunk ? '┃' : ' ') + ' '.repeat(Math.max(0, arrow.length - 1))
    if (a === null) {
      const t = lv.turns
      drawn.push(line(top('00 main session'), { color: 'cyan' }))
      drawn.push(line(inner(`${mainState(lv.main)}  ${t.length} turn${t.length === 1 ? '' : 's'} · ${money(t.reduce((n, x) => n + x.cost, 0))} · ${all.length} agent${all.length === 1 ? '' : 's'} spawned`), { color: 'cyan' }))
      drawn.push(line(bottom(children.length > 0), { color: 'cyan' }))
    } else {
      // The whole box carries the state's colour: green at work, yellow quiet, red failed or stopped; a finished box in the default colour.
      const { state, color } = stateOf(a, now)
      const figures = `${shortModel(a.model)} ${a.effort}`.trim() + `  ${secs((a.done ?? now) - a.startedAt)}  ${a.steps} step${a.steps === 1 ? '' : 's'}` + (a.cost !== null ? `  ${money(a.cost)}` : '')
      const title = `${String(a.n).padStart(2, '0')} ${a.type}${a.run > 1 ? ` · run ${a.run}` : ''}`
      drawn.push(line(`${prefix}${arrow}${top(title)}`, { color }))
      drawn.push(line(`${cont}${inner(`${state.padEnd(9)}  ${figures}`)}`, { color }))
      drawn.push(line(`${cont}${inner(a.description)}`, { color }))
      drawn.push(line(`${cont}${bottom(children.length > 0)}`, { color }))
    }
    const base = a === null ? '' : cont
    children.forEach((c, i) => {
      const last = i === children.length - 1
      const w = weightOf(c.ctx)
      draw(c, base + '          ', `${last ? '┗' : '┣'}${w}${w} ~${kilo(c.ctx)} ${w}${w}▶ `, !last)
    })
  }
  draw(null, '', '', false)
  out.push(...drawn)
  out.push(line('arrow = context sent, estimated from the prompt (4 chars/token): ━━ ≥16k  ── 4k–16k  ┄┄ <4k', { dim: true }))
  // Live: the agents at work, the most recent call first; a failed one keeps its tail while it is among the last finished.
  // Live: the agents at work, the most recent call first; when fewer than two run, the last finished (a failed one first) keep their tail.
  const live = [...running].sort((x, y) => y.lastStepAt - x.lastStepAt).slice(0, 2)
  const rest = [...lv.finished].sort((x, y) => Number(bad(y)) - Number(bad(x)) || (y.done ?? 0) - (x.done ?? 0)).slice(0, 2 - live.length)
  const tail = (title: string, state: string, recent: Recent[], color: string | undefined) => {
    out.push(BLANK)
    out.push(line(`${title}${' '.repeat(Math.max(1, 62 - title.length))}[${state}]`, { bold: true, color }))
    if (recent.length === 0) out.push(line('  no tool call yet', { dim: true }))
    for (const r of recent.slice(-5)) out.push(line(`  ${clockS(r.at)}  ${r.err ? 'ERROR ' : ''}${r.text}`, { color: r.err ? 'red' : undefined, dim: !r.err }))
  }
  for (const a of [...live, ...rest]) {
    const state = a.done === null ? `RUNNING ${secs(now - a.startedAt)}` : `${endWord(a)} ${bad(a) ? 'after' : 'in'} ${secs((a.done ?? now) - a.startedAt)}`
    tail(`● ${String(a.n).padStart(2, '0')} ${a.type}${a.run > 1 ? ` · run ${a.run}` : ''} / ${a.done === null ? 'live' : 'stopped'}`, state, a.recent, a.done === null ? 'green' : bad(a) ? 'red' : undefined)
  }
  // The main session's own tail when there is room for it: always before any agent, beside a lone agent after.
  if (live.length + rest.length < 2) tail('● 00 main session / live', mainWord(lv.main, now), lv.main.recent, 'cyan')
  out.push(BLANK)
  out.push(line('[ Events ]', { bold: true }))
  if (lv.events.length === 0) out.push(line('  none yet', { dim: true }))
  for (const ev of lv.events.slice(-8)) out.push(line(`  ${clockS(ev.at)}  ${ev.text}`, { color: ev.color }))
  return out
}

/** The run as a drawing: every agent a box on a grid (a column per depth, rows by a centred tree layout), the arrow from its
 * spawner weighted by the context sent. Pure: the pane draws the scene with positioned elements, nothing is measured on screen. */
type Seg = { x: number; text: string; color?: string }
type NodeBox = { a: RunningAgent | null; x: number; y: number; w: number; color?: string; title: string; state: string; figures: string; desc: string }
type Scene = { boxes: NodeBox[]; rows: Map<number, Seg[]>; width: number; height: number }
const BOX_H = 5     // border, three lines, border
const PITCH = 6     // rows a leaf takes: its box and a row to the next
const GAP = 14      // columns between depths: the arrow and its label
type Weight = { h: string; v: string; j: Record<string, string> }
const HEAVY: Weight = { h: '━', v: '┃', j: { ud: '┃', ur: '┗', dr: '┏', udr: '┣', lr: '━', lrd: '┳', lru: '┻', lrud: '╋', lud: '┫', ld: '┓', lu: '┛', r: '━', l: '━', u: '┃', d: '┃' } }
const LIGHT: Weight = { h: '─', v: '│', j: { ud: '│', ur: '└', dr: '┌', udr: '├', lr: '─', lrd: '┬', lru: '┴', lrud: '┼', lud: '┤', ld: '┐', lu: '┘', r: '─', l: '─', u: '│', d: '│' } }
const DASHED: Weight = { ...LIGHT, h: '┄', v: '┆' }
const weightFor = (ctx: number): Weight => (ctx >= 16000 ? HEAVY : ctx >= 4000 ? LIGHT : DASHED)
/** How a finished run ended: STOPPED (aborted), FAILED (an error or a refusal) or DONE. */
const endWord = (a: RunningAgent) => (a.stopped ? 'STOPPED' : a.failed ? 'FAILED' : 'DONE')
const bad = (a: RunningAgent) => a.failed || a.stopped
/** The main session's state word for its box (at work while a turn runs) and the bracket of its panel (how long, or idle since when). */
const mainState = (m: MainLive) => (m.busy ? '● WORKING' : '● IDLE')
const mainWord = (m: MainLive, now: number) => (m.busy ? `WORKING ${secs(now - m.since)}` : m.lastAt ? `IDLE since ${clockS(m.lastAt)}` : 'IDLE')
const stateOf = (a: RunningAgent, now: number) => {
  const quiet = a.done === null && now - a.lastStepAt > QUIET_MS
  return { state: a.done === null ? (quiet ? '● QUIET' : '● RUNNING') : `● ${endWord(a)}`, color: a.done === null ? (quiet ? 'yellow' : 'green') : bad(a) ? 'red' : undefined }
}
/** The tree of a run: every record (running and finished), and a child's parent as the run of that id active at the child's spawn. */
const treeOf = (lv: Live) => {
  const all = [...Object.values(lv.agents), ...lv.finished].sort((x, y) => x.n - y.n || x.run - y.run)
  const parentOf = (c: RunningAgent): RunningAgent | null => {
    if (c.parent === null) return null
    const runs = all.filter(p => p.id === c.parent).sort((x, y) => x.startedAt - y.startedAt)
    if (runs.length === 0) return null
    return [...runs].reverse().find(p => p.startedAt <= c.startedAt) ?? runs[0]
  }
  const kids = (p: RunningAgent | null) => all.filter(a => parentOf(a) === p)
  return { all, kids }
}
const slug = (t: string) => t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'run'
/** The run the monitor shows when none is picked: the latest with an agent at work, else the latest. */
const latestRunId = (lv: Live): string | null => {
  const at = Object.values(lv.agents)
  for (let i = lv.runs.length - 1; i >= 0; i--) if (at.some(a => a.runId === lv.runs[i].id)) return lv.runs[i].id
  return lv.runs[lv.runs.length - 1]?.id ?? null
}
const runOf = (lv: Live, id: string | null) => (id ? lv.runs.find(r => r.id === id) ?? null : null)
/** The live state narrowed to one run: its agents, its events, its counts; the whole session when it has no runs. */
const scopeOf = (lv: Live, runId: string | null): Live => {
  const id = runId ?? latestRunId(lv)
  if (!id) return lv
  const fin = lv.finished.filter(a => a.runId === id)
  return { ...lv, agents: Object.fromEntries(Object.entries(lv.agents).filter(([, a]) => a.runId === id)), finished: fin, events: lv.events.filter(e => e.runId === id),
    doneN: fin.length, doneCost: fin.reduce((n, a) => n + (a.cost ?? 0), 0), failedN: fin.filter(a => a.failed).length, stoppedN: fin.filter(a => a.stopped).length }
}
/** One line naming the run shown: its place among the session's, its words, its agents and cost, whether it ended and was saved. */
const runLine = (lv: Live, id: string | null): string => {
  const m = runOf(lv, id ?? latestRunId(lv))
  if (!m) return 'no run yet this session'
  const i = lv.runs.findIndex(r => r.id === m.id) + 1
  return `run ${i}/${lv.runs.length} this session · ${m.name ? `task "${m.name}"` : `"${m.prompt.slice(0, 50)}${m.prompt.length > 50 ? '…' : ''}"`} · ${m.agentN} agent${m.agentN === 1 ? '' : 's'} · ${money(m.cost)} · ${m.endedAt ? `ended ${clock(m.endedAt)}` : 'running'}${m.saved ? ' · saved' : ''}`
}
/** The run as a markdown report: what was asked, the agents with what they ran on and what they cost, their answers, the events. */
const runReport = (lvAll: Live, id: string, now: number): string => {
  const m = runOf(lvAll, id)
  const lv = scopeOf(lvAll, id)
  const agents = [...Object.values(lv.agents), ...lv.finished].sort((x, y) => x.n - y.n || x.run - y.run)
  const d = stamp
  const out: string[] = []
  out.push(`# Agent run: ${m?.name ?? m?.prompt ?? id}`, '')
  if (m) out.push(`started ${d(m.startedAt)}${m.endedAt ? `, ended ${d(m.endedAt)}` : ', still running'} · ${m.agentN} agent${m.agentN === 1 ? '' : 's'} · ${money(m.cost)}${m.failedN ? ` · ${m.failedN} failed` : ''}${m.stoppedN ? ` · ${m.stoppedN} stopped` : ''}`, '')
  if (m?.prompt && !m.name) out.push('## Asked', '', m.prompt, '')
  out.push('## Graph', '', '```text', ...monitorLines(lvAll, now, id).map(l => l.text), '```', '')
  out.push('## Agents', '', '| # | agent | model effort | family | steps | elapsed | cost | outcome | task |', '|---|---|---|---|---|---|---|---|---|')
  for (const a of agents) out.push(`| ${String(a.n).padStart(2, '0')}${a.run > 1 ? ` · run ${a.run}` : ''} | ${a.type} | ${`${shortModel(a.model)} ${a.effort}`.trim()} | ${a.family ?? 'unmeasured'} | ${a.steps} | ${secs((a.done ?? now) - a.startedAt)} | ${a.cost !== null ? money(a.cost) : '-'} | ${a.done === null ? 'running' : endWord(a).toLowerCase()} | ${a.description.replace(/\|/g, '/')} |`)
  out.push('', '## Answers', '')
  for (const a of agents) if (a.answer) out.push(`### ${String(a.n).padStart(2, '0')} ${a.type}: ${a.description}`, '', a.answer, '')
  out.push('## Events', '')
  for (const ev of lv.events) out.push(`- ${clockS(ev.at)}  ${ev.text}`)
  out.push('', `_Written by model-router ${WIDGET_VERSION}; figures from the engine's per-turn usage, priced from the catalog; context sent estimated from the prompt._`, '')
  return out.join('\n')
}
const sceneOf = (lv: Live, now: number, width: number): Scene => {
  const { all, kids } = treeOf(lv)
  const depthOf = (p: RunningAgent | null, d: number): number => Math.max(d, ...kids(p).map(c => depthOf(c, d + 1)))
  const D = depthOf(null, 0)
  const inner = Math.max(22, Math.min(40, Math.floor((width - GAP * D) / (D + 1)) - 2))
  const w = inner + 2
  const boxes: NodeBox[] = []
  const cells = new Map<number, Map<number, { ch: string; color?: string }>>()
  const put = (y: number, x: number, ch: string, color?: string) => {
    if (!cells.has(y)) cells.set(y, new Map())
    cells.get(y)!.set(x, { ch, color })
  }
  const fit = (t: string) => (t.length > inner ? t.slice(0, inner - 1) + '…' : t)
  // Layout: a leaf at the cursor; a parent centred on its children, which follow one another.
  const place = (a: RunningAgent | null, depth: number, cursor: number): { row: number; height: number } => {
    const children = kids(a)
    const x = depth * (w + GAP)
    let row = cursor
    let height = PITCH
    const childRows: { c: RunningAgent; row: number }[] = []
    if (children.length) {
      let cur = cursor
      for (const c of children) {
        const r = place(c, depth + 1, cur)
        childRows.push({ c, row: r.row })
        cur += r.height
      }
      height = cur - cursor
      row = Math.round((childRows[0].row + childRows[childRows.length - 1].row) / 2)
    }
    if (a === null) {
      const t = lv.turns
      boxes.push({ a, x, y: row, w, color: 'cyan', title: '00 main session', state: mainState(lv.main), figures: `${t.length} turn${t.length === 1 ? '' : 's'} · ${money(t.reduce((n, z) => n + z.cost, 0))}`, desc: fit(`${all.length} agent${all.length === 1 ? '' : 's'} spawned`) })
    } else {
      const { state, color } = stateOf(a, now)
      const parts = [`${shortModel(a.model)} ${a.effort}`.trim(), secs((a.done ?? now) - a.startedAt), `${a.steps} step${a.steps === 1 ? '' : 's'}`, ...(a.cost !== null ? [money(a.cost)] : [])]
      let figures = parts.join('  ')
      // Too long for the box: drop the step count, then the cost, then the elapsed time; the model stays.
      while (`${state}  ${figures}`.length > inner && parts.length > 1) { if (parts.length > 2) parts.splice(2, 1); else parts.pop(); figures = parts.join('  ') }
      boxes.push({ a, x, y: row, w, color, title: fit(`${String(a.n).padStart(2, '0')} ${a.type}${a.run > 1 ? ` · run ${a.run}` : ''}`), state, figures, desc: fit(a.description) })
    }
    // Arrows: a stub out of the box's middle, a trunk two columns on, a branch into each child's middle with the label.
    if (childRows.length) {
      const y0 = row + 2
      const x0 = x + w
      const x1 = x0 + 2
      const trunk = childRows.map(k => weightFor(k.c.ctx)).reduce((m, k) => (k === HEAVY || m === HEAVY ? HEAVY : k === LIGHT || m === LIGHT ? LIGHT : DASHED))
      const ys = childRows.map(k => k.row + 2)
      const ymin = Math.min(y0, ...ys)
      const ymax = Math.max(y0, ...ys)
      put(y0, x0, trunk.h); put(y0, x0 + 1, trunk.h)
      for (let r = ymin; r <= ymax; r++) {
        const key = (r === y0 ? 'l' : '') + (ys.includes(r) ? 'r' : '') + (r > ymin ? 'u' : '') + (r < ymax ? 'd' : '')
        const order = ['l', 'r', 'u', 'd'].filter(k => key.includes(k)).join('')
        const sorted = ['lrud', 'lrd', 'lru', 'lud', 'udr', 'lr', 'ud', 'ur', 'dr', 'ld', 'lu', 'r', 'l', 'u', 'd'].find(k => k.split('').sort().join('') === order.split('').sort().join(''))
        put(r, x1, (sorted && trunk.j[sorted]) || trunk.v)
      }
      for (const k of childRows) {
        const wgt = weightFor(k.c.ctx)
        const y1 = k.row + 2
        const label = ` ~${kilo(k.c.ctx)} `
        const from = x1 + 1
        const to = (depth + 1) * (w + GAP) - 1   // the column before the child's box
        for (let c = from; c <= to; c++) put(y1, c, wgt.h)
        for (let i = 0; i < label.length && from + 1 + i < to; i++) put(y1, from + 1 + i, label[i])
        put(y1, to, '▶')
      }
    }
    return { row, height }
  }
  const total = place(null, 0, 0)
  const rows = new Map<number, Seg[]>()
  for (const [y, line] of cells) {
    const xs = [...line.keys()].sort((p, q) => p - q)
    const segs: Seg[] = []
    for (const x of xs) {
      const c = line.get(x)!
      const last = segs[segs.length - 1]
      if (last && last.x + last.text.length === x && last.color === c.color) last.text += c.ch
      else segs.push({ x, text: c.ch, color: c.color })
    }
    rows.set(y, segs)
  }
  return { boxes, rows, width: (D + 1) * (w + GAP) - GAP, height: Math.max(BOX_H, total.height - 1) }
}

const liveLines = (lv: Live, ctxNow: number | null, modelNow: string, s: StatusJson | null, mode: MainEffortMode): Line[] => {
  const ts = lv.turns
  const head = `this session · ${ts.length === 0 ? 'no turn yet' : `${ts.length} turn${ts.length === 1 ? '' : 's'} · ${money(ts.reduce((n, t) => n + t.cost, 0))}`}`
  const read = ts.reduce((n, t) => n + t.cacheRead, 0), fresh = ts.reduce((n, t) => n + t.in + t.cacheWrite, 0)
  const hit = read + fresh > 0 ? ` · cache hit ${Math.round((100 * read) / (read + fresh))}%` : ''
  const eff = ts.at(-1)?.sessionEffort
  const lines = [line(`${head}${hit}${ctxNow !== null ? ` · ctx ${kilo(ctxNow)}` : ''}${modelNow ? ` · ${modelNow.replace(/^claude-/, '')}${eff ? ' ' + eff : ''}` : ''}`, { bold: true })]
  const esc = Object.entries(lv.escalated)
  const agentsLine = (calls: number, routedN: number) => line(`  agents   ${calls} call${calls === 1 ? '' : 's'} · ${routedN} routed${esc.length ? ` · escalated: ${esc.map(([f, w]) => `${f} (${w})`).join('; ')}` : ''}`, { dim: true })
  if (ts.length === 0) {
    if (esc.length) lines.push(agentsLine(0, 0))
    return lines
  }
  const last = ts.slice(-24)
  const top = Math.max(...last.map(t => t.cost))
  const heavy = ts.filter(t => t.errors >= ESCALATE_ERRORS).length
  lines.push(line(`  $/turn   ${spark(last.map(t => t.cost))}  max ${money(top)}${heavy ? ` · ${heavy} turn${heavy === 1 ? '' : 's'} with ${ESCALATE_ERRORS}+ tool errors` : ''}`, { dim: true }))
  const strip = last.map(t => (t.gear === 'down' ? '↓' : t.gear === 'up' ? '↑' : t.advised ? '?' : '·')).join('')
  const down = ts.filter(t => t.gear === 'down'), up = ts.filter(t => t.gear === 'up'), would = ts.filter(t => t.advised && t.gear === 'same')
  const saved = down.reduce((n, t) => n + effortSaving(t), 0)
  const wouldSave = would.reduce((n, t) => n + ((t.out * priceOf(t.model).out) / 1e6) * ((EFFORT_RATIO[t.sessionEffort] ?? 1) / (EFFORT_RATIO[t.advised ?? 'low'] ?? 1) - 1), 0)
  const tail = mode === 'off' ? 'effort control off (/router effort advise|auto)'
    : mode === 'advise' ? (would.length ? `advise: ${would.length} turn${would.length === 1 ? '' : 's'} read as a measured task and would run at low (est ${money(wouldSave)} less): /router effort auto` : 'advise: no turn read as a measured task yet')
    : `auto: ${down.length} at the measured effort (est ${money(saved)} less)${up.length ? `, ${up.length} back up after errors` : ''}`
  lines.push(line(`  effort   ${strip.padEnd(24)}  ${tail}`, { dim: true }))
  const calls = ts.reduce((n, t) => n + t.agentCalls, 0), routedN = ts.reduce((n, t) => n + t.routed, 0)
  if (calls || esc.length) lines.push(agentsLine(calls, routedN))
  const r = s?.changes?.realized
  if (r && r.projected != null && r.projected > 0 && r.saved !== null) {
    const frac = Math.max(0, Math.min(1, r.saved / r.projected))
    lines.push(line(`  plan     saved ${money(Math.max(0, r.saved))} of ${money(r.projected)} projected ${bar(frac, 10)} ${Math.round(frac * 100)}% · since ${r.since.slice(5, 10)}`, { dim: true, color: r.saved < 0 ? 'yellow' : undefined }))
  }
  return lines
}
async function seedVocab($: Dollar) {
  if (vocabSeeded) return
  vocabSeeded = true
  try {
    for (const m of await $.session.messages()) {
      if (m.role !== 'user') continue
      for (const w of wordsOf(m.text)) vocab.add(w)
      for (const t of ticketsOf(m.text)) ticketsSeen.add(t)
    }
  } catch {
    // no transcript to seed from: the vocabulary grows from here
  }
}
/** The live context size in tokens, or null when the host does not say. */
async function contextTokens($: Dollar) {
  try {
    const u = await $.session.usage()
    return { tokens: u.context.tokens ?? null, window: u.context.window }
  } catch {
    return null
  }
}
// The transcript project key of this session's working directory (what Claude Code names the transcript directory).
let projectKey = ''
const keyOf = (cwd: string) => cwd.replace(/[^A-Za-z0-9]/g, '-')

/** The checkout the scripts run from: the configured path when the repository is there, else the full
 * clone the plugin install made (the marketplace; known_marketplaces.json says where it is), so the
 * install alone is enough. Read on every refresh, so a clone made later is picked up. */
async function resolveRepo($: Dollar) {
  const home = (await $.env.get('HOME')) || (await $.env.get('USERPROFILE')) || ''
  repo = repoOption.replace(/^~(?=$|[\\/])/, home)
  where = ''
  if (await $.fs.exists(`${repo}/routing.json`)) return
  const configDir = (await $.env.get('CLAUDE_CONFIG_DIR')) || `${home}/.claude`
  try {
    const known = JSON.parse(await $.fs.read(`${configDir}/plugins/known_marketplaces.json`)) as Record<string, { installLocation?: string }>
    const clone = known['model-router']?.installLocation
    if (clone && (await $.fs.exists(`${clone}/routing.json`))) {
      repo = clone
      where = 'marketplace clone'
    }
  } catch {
    // no marketplace file, or not readable: the configured path stands, and refresh says it is missing
  }
}

async function findPython($: Dollar) {
  if (python) return python
  for (const candidate of pythonOption ? [pythonOption] : ['python3', 'python', 'py']) {
    try {
      const r = await $.process.run([candidate, '--version'], { timeoutMs: 10000 })
      if (r.exitCode === 0 && /Python 3/.test(r.stdout + r.stderr)) {
        python = candidate
        return candidate
      }
    } catch {
      // not on PATH; try the next name
    }
  }
  const platform = (await $.env.get('OS')) === 'Windows_NT' ? 'winget install Python.Python.3.13 (or python.org), then open a new terminal'
    : (await $.env.get('HOME'))?.startsWith('/Users/') ? 'xcode-select --install or brew install python3'
    : 'apt install python3 (or your distribution\'s package)'
  throw new Error(`no Python 3 on PATH: the widget reads your transcripts with it. Install: ${platform}; or set "Python command" in /config (model-router)`)
}

/** The rate-limit windows the last API response reported; none when the host does not say. */
async function readLimits($: Dollar): Promise<RateLimit[]> {
  try {
    const u = await $.session.usage()
    return u.rateLimits.map(l => ({ kind: l.kind, percentUsed: l.percentUsed, resetsAt: l.resetsAt }))
  } catch {
    return []
  }
}

async function refresh($: Dollar, fetch = false) {
  const at = await $.clock.now()
  try {
    await resolveRepo($)
    if (!(await $.fs.exists(`${repo}/routing.json`))) {
      throw new Error(`no model-router checkout at ${repo} and no clone from the plugin install: clone it there, or set the path in /config`)
    }
    const py = await findPython($)
    const argv = [py, 'tools/status.py', '--json', ...(fetch ? ['--fetch'] : [])]
    const r = await $.process.run(argv, { cwd: repo, env: pyEnv(), timeoutMs: 180000 })
    if (r.exitCode !== 0) throw new Error(`status.py exit ${r.exitCode}: ${r.stderr.trim().split('\n').pop() ?? ''}`)
    const json = JSON.parse(r.stdout) as StatusJson
    const rateLimits = await readLimits($)
    await update($, status, () => ({ at, json, error: null, rateLimits, where }))
    const ctx = await contextTokens($)
    $.ui.status(statusMode === 'off' ? undefined : statusLine(json, rateLimits, (await read($, routed)).length, statusMode, ctx?.tokens ?? null, await $.session.model().catch(() => '')))
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    const rateLimits = await readLimits($)
    await update($, status, () => ({ at, json: null, error, rateLimits, where }))
    $.ui.status(statusMode === 'off' ? undefined : error)
  }
}

/** Record a routing change on this machine (tools/changes.py): the pane counts the saving from now. */
async function recordChange($: Dollar, kind: string, detail: string, projected?: number) {
  try {
    const py = await findPython($)
    const argv = [py, 'tools/changes.py', 'add', kind, detail, ...(projected ? ['--projected', projected.toFixed(2)] : [])]
    const r = await $.process.run(argv, { cwd: repo, env: pyEnv(), timeoutMs: 20000 })
    if (r.exitCode !== 0) throw new Error(r.stderr.trim().split('\n').pop() ?? `exit ${r.exitCode}`)
  } catch (err) {
    $.ui.toast(`router: could not record the change: ${err instanceof Error ? err.message : String(err)}`)
  }
  await refresh($)
}

/** One line in this machine's routed log (tools/routed_log.py), so the weekly slots can count what the router did.
 * The project key begins with a dash (a path's slashes), so it travels as --project=KEY: as a separate word argparse reads it as an option. */
let routedLogWarned = false
/** A hook failure as one line of text, whatever shape the engine gives it. */
const failureText = (err: unknown) => typeof err === 'string' ? err : (err as { message?: string } | null)?.message ?? JSON.stringify(err)
async function logRouted($: Dollar, family: string, agent: string, from: string, to: string, decision: string) {
  try {
    const py = await findPython($)
    const r = await $.process.run([py, 'tools/routed_log.py', 'add', family, agent, from, to, decision, `--project=${projectKey}`], { cwd: repo, env: pyEnv(), timeoutMs: 20000 })
    if (r.exitCode !== 0) throw new Error(r.stderr.trim().split('\n').pop() || `exit ${r.exitCode}`)
  } catch (err) {
    // the log is a convenience: routing stands without it; the first failure of the session is said, with its reason
    if (routedLogWarned) return
    routedLogWarned = true
    $.ui.toast(`router: the routed log was not written (${failureText(err)}); routing itself is unaffected`)
  }
}

/** The run written to <config>/model-router/runs/<day>/<time>-<words>.json: its meta, every agent of it, its events. A re-save overwrites. */
async function saveRun($: Dollar, id: string) {
  const lv = await read($, live)
  const meta = runOf(lv, id)
  if (!meta || !runsDir) return null
  const d = new Date(meta.startedAt)
  const day = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const file = meta.saved ?? `${runsDir}/${day}/${clockS(meta.startedAt).replace(/:/g, '')}-${slug(meta.name ?? meta.prompt)}.json`
  const agents = [...Object.values(lv.agents), ...lv.finished].filter(a => a.runId === id).sort((x, y) => x.n - y.n || x.run - y.run)
  const body = { source: 'live', widget: WIDGET_VERSION, meta: { ...meta, saved: file }, agents, events: lv.events.filter(e => e.runId === id) }
  try {
    await $.fs.write(file, JSON.stringify(body, null, 1))
    await update($, live, v => ({ ...v, runs: v.runs.map(r => (r.id === id ? { ...r, saved: file } : r)) }))
    return file
  } catch (err) {
    $.ui.toast(`router: could not save the run: ${err instanceof Error ? err.message : String(err)}`)
    return null
  }
}
/** A run with no agent left at work has ended (a named task ends only by /router task end): mark it and save it. */
async function closeIdleRuns($: Dollar) {
  const lv = await read($, live)
  const at = Object.values(lv.agents)
  const idle = lv.runs.filter(r => r.endedAt === null && !r.id.startsWith('task:') && !at.some(a => a.runId === r.id))
  if (idle.length === 0) return
  const now = await $.clock.now()
  await update($, live, v => ({ ...v, runs: v.runs.map(r => (idle.some(i => i.id === r.id) ? { ...r, endedAt: now } : r)) }))
  for (const r of idle) await saveRun($, r.id)
}
/** The report of a run written into the project: docs/runs/<day>-<words>.md (a saved run not in this session goes through tools/runs.py). */
async function saveReport($: Dollar, id: string | null): Promise<string> {
  const lv = await read($, live)
  const pick = id ?? latestRunId(lv)
  if (!pick) return 'no run to report yet'
  const now = await $.clock.now()
  const m = runOf(lv, pick)
  if (m) {
    const d = new Date(m.startedAt)
    const path = `docs/runs/${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}-${slug(m.name ?? m.prompt)}.md`
    try { await $.fs.write(path, runReport(lv, pick, now)) } catch (err) { return `could not write the report: ${err instanceof Error ? err.message : String(err)}` }
    return `report written: ${path} (the graph, every agent with model, effort, cost and outcome, their answers, the events)`
  }
  try {
    const py = await findPython($)
    const r = await $.process.run([py, 'tools/runs.py', 'export', pick, '--out-dir', `${sessionCwd}/docs/runs`], { cwd: repo, env: pyEnv(), timeoutMs: 60000 })
    return r.exitCode === 0 ? r.stdout.trim() : `could not export ${pick}: ${r.stderr.trim().split('\n').pop() ?? ''}`
  } catch (err) {
    return `could not export ${pick}: ${err instanceof Error ? err.message : String(err)}`
  }
}
/** The runs saved on this machine, listed by tools/runs.py and kept for the history view. */
async function listSavedRuns($: Dollar): Promise<SavedRun[]> {
  try {
    const py = await findPython($)
    const r = await $.process.run([py, 'tools/runs.py', 'list', '--json'], { cwd: repo, env: pyEnv(), timeoutMs: 60000 })
    const rows = r.exitCode === 0 ? (JSON.parse(r.stdout || '[]') as SavedRun[]) : []
    await update($, savedRuns, () => rows)
    return rows
  } catch {
    return []
  }
}

async function runJob($: Dollar, name: string, extra: string[] = []) {
  const spec = JOBS[name]
  if (!spec) return false
  const current = await read($, job)
  if (current?.isRunning) {
    $.ui.toast(`model-router: ${current.name} is still running`)
    return false
  }
  let argv: string[]
  try {
    argv = [...spec.argv(await findPython($), where !== ''), ...extra]
  } catch (err) {
    $.ui.toast(err instanceof Error ? err.message : String(err))
    return false
  }
  const startedAt = await $.clock.now()
  await update($, job, () => ({ name: spec.title, lines: [`$ ${argv.join(' ')}`], isRunning: true, exitCode: null, startedAt }))
  if (statusMode !== 'off') $.ui.status(`running ${spec.title}… · /router`)
  // The child outlives this dispatch: its loop runs on and ends with the child.
  void (async () => {
    let code: number | null = null
    let rest = ''
    const append = (text: string) =>
      update($, job, j => (j ? { ...j, lines: [...j.lines, ...text.split('\n')].slice(-400) } : j))
    try {
      const child = $.process.spawn({ argv, cwd: repo, env: pyEnv() })
      for await (const piece of child) {
        rest += piece.text
        const cut = rest.lastIndexOf('\n')
        if (cut >= 0) {
          await append(rest.slice(0, cut))
          rest = rest.slice(cut + 1)
        }
      }
      if (rest) await append(rest)
      code = (await child.result).code
    } catch (err) {
      await append(`error: ${err instanceof Error ? err.message : String(err)}`)
    }
    await update($, job, j => (j ? { ...j, isRunning: false, exitCode: code } : j))
    $.ui.toast(`model-router: ${spec.title} ${code === 0 ? 'done' : `failed (exit ${code ?? '?'})`}`)
    await refresh($)
  })()
  return true
}

// ---- Routing each Agent call to the model and effort the benchmark measured for its kind of task.
// The keyword lists mirror tools/consumption.py (LOOKUP, SYNTHESIS, CODE), so the ledger and the router agree.
const LOOKUP = ['what is the', 'which version', 'latest version', 'look up', 'find out', 'check the docs', 'default value',
  'release date', 'is it supported', 'what does the doc', 'current version', 'find the url']
const SYNTHESIS = ['research', 'compare', 'comparison', 'report', 'compile', 'deep dive', 'survey', 'landscape', 'fact-dense',
  'summarize the', 'write up', 'notes that let']
const CODE = ['fix', 'implement', 'refactor', 'write tests', 'bug', 'add a', 'change the', 'migrate', 'failing test']
const RUNNER = ['failing test', 'test command', 'run the tests', 'run the test', 'npm test', 'vitest', 'pytest', 'cargo test', 'go test',
  'make test', 'tests pass', 'test passes', 'the suite']
const BROWSER = ['in the browser', 'chrome', 'web page', 'the page at', 'fill the form', 'fill in the form', 'click', 'sign in', 'log in',
  'navigate to', 'open http', 'checklist', 'pass/fail']
const EXPLORE_TYPES = new Set(['Explore', 'Codebase Onboarding Engineer'])
const MODELS = new Set(['sonnet', 'opus', 'haiku', 'fable'])
const EFFORTS = new Set(['low', 'medium', 'high', 'xhigh', 'max'])
/** A routing decision waiting for its spawn: the Agent call's id (and its words, for a spawn whose id is not known) → what the subagent runs on. */
type PendingRoute = { at: number; description: string; prompt: string; model: string; effort: string; family: string }
const pendingRoutes = new Map<string, PendingRoute>()
const PENDING_MS = 10 * 60000
/** The last prompt the person sent: the run a spawn belongs to takes its words. */
let lastPrompt = ''
/** Where runs are saved: <config>/model-router/runs; the session's working directory, for the reports. */
let runsDir = ''
let sessionCwd = ''
const RUNNER_NOTE = '\n\nRun the test command before you finish; the task counts as done only when the suite passes.'

type Match = { family: string; why: string }
/** The measured family a call belongs to, from its agent type and prompt; null where none covers it (no blind downgrade). */
const matchFamily = (agent: string, prompt: string): Match | null => {
  const p = prompt.toLowerCase()
  if (EXPLORE_TYPES.has(agent)) return { family: 'find_feature', why: `${agent}: read-only code search` }
  if (agent === 'Web Researcher') return { family: 'web_research', why: 'the lookup agent' }
  if (agent === 'Evidence Collector') return { family: 'browser_flow', why: 'the browser agent' }
  if (p.length < 900 && LOOKUP.some(k => p.includes(k))) return { family: 'web_research', why: 'a short fact lookup' }
  if (SYNTHESIS.some(k => p.includes(k))) return { family: 'research_synthesis', why: 'a research note' }   // acts only once the family is decided
  if (BROWSER.filter(k => p.includes(k)).length >= 2) return { family: 'browser_flow', why: 'a browser flow' }
  if (CODE.some(k => p.includes(k)) && RUNNER.some(k => p.includes(k))) return { family: 'repo_fix', why: 'a fix with the test runner in the loop' }
  return null
}

type Candidate = { family: string; why: string; agent: string; asked: string; model: string; effort: string; rate: string; cost: string }
/** What the evidence says this call should run on, or null when it already does or nothing measured covers it. */
const FAMILY_CLASS: Record<string, string> = { find_feature: 'code-explore', web_research: 'fact-lookup', browser_flow: 'browser-flow', repo_fix: 'code-change', research_synthesis: 'research-synthesis' }
/** The consumption scan's class of this call, for the per-project overrides. */
const classOf = (agent: string, family: string | null) => family ? FAMILY_CLASS[family] ?? 'other' : agent.toLowerCase().includes('review') ? 'code-review' : 'other'

const decideCall = (s: StatusJson, agent: string, prompt: string, model?: string, effort?: string): Candidate | null => {
  const m = matchFamily(agent, prompt)
  const asked = model ? `${model} ${effort ?? '(default effort)'}` : (s.agents.routed.find(r => r.name === agent)?.have ?? 'inherit')
  // The person's override for this project and class comes first: what they chose after a learned suggestion.
  const ov = s.overrides?.[projectKey]?.[classOf(agent, m?.family ?? null)]
  if (ov && MODELS.has(ov.model) && EFFORTS.has(ov.effort)) {
    if (asked === `${ov.model} ${ov.effort}`) return null
    return { family: m?.family ?? 'override', why: `${m?.why ?? agent}: your override for this project`, agent, asked, model: ov.model, effort: ov.effort, rate: 'your choice', cost: '-' }
  }
  if (!m) return null
  const f = s.families.find(x => x.name === m.family)
  if (!f?.model || !f.effort || !MODELS.has(f.model) || !EFFORTS.has(f.effort)) return null
  if (asked === `${f.model} ${f.effort}`) return null
  return { family: f.name, why: m.why, agent, asked, model: f.model, effort: f.effort, rate: f.rate ?? '?',
    cost: f.cost_per_success === null ? '?' : f.cost_per_success.toFixed(3) }
}

/** Asks the person; 'keep' when they keep what was asked, dismiss, or no one can be asked (a -p run, a background loop). */
async function askRoute($: Dollar, c: Candidate): Promise<'route' | 'keep' | 'auto'> {
  const route = c.cost === '-' ? `${c.model} ${c.effort} (your override for this project)` : `${c.model} ${c.effort} (measured ${c.rate}, $${c.cost}/success)`
  const keep = `Keep ${c.asked}`
  const always = 'Always route this session'
  try {
    const a = await $.ui.ask(`Run ${c.why} on ${c.model} ${c.effort} instead of ${c.asked}? (${c.family} on the benchmark: ${c.rate})`,
      { options: [route, keep, always], header: 'Router' })
    return a === route ? 'route' : a === always ? 'auto' : 'keep'
  } catch {
    return 'keep'
  }
}

export const register: Register = (on, options) => {
  repoOption = String(options.repo || '~/Projects/Github/model-router')
  pythonOption = String(options.python || '')
  refreshMinutes = Number(options.refreshMinutes ?? 30)
  const mode = String(options.routing ?? 'ask')
  routingMode = mode === 'auto' || mode === 'off' ? mode : 'ask'
  const sm = String(options.statusLine ?? 'full')
  const me = String(options.mainEffort ?? 'advise')
  mainEffortMode = me === 'off' || me === 'auto' ? me : 'advise'
  plans.clear(); currentTurn = ''
  statusMode = sm === 'minimal' || sm === 'off' ? sm : 'full'
  struggleOption = Math.max(5, Math.min(95, Number(options.struggle ?? 25) || 25))
  contextWarn = Math.max(20000, Number(options.contextWarn ?? 100000) || 100000)
  vocab.clear(); ticketsSeen.clear(); vocabSeeded = false; lastSwitchTurn = -100; driftOff = false
  repo = repoOption
  python = ''

  on('session.start', async ($, e, next) => {
    projectKey = keyOf(e.cwd)
    sessionCwd = e.cwd
    const home0 = (await $.env.get('HOME')) || (await $.env.get('USERPROFILE')) || ''
    runsDir = `${(await $.env.get('CLAUDE_CONFIG_DIR')) || `${home0}/.claude`}/model-router/runs`
    await $.command.register({
      name: 'router',
      description: 'Model router: the session live, where the routing stands, first-run setup, installation check, re-check it, ledger, apply, prune, pinned agent sources, pull',
      argumentHint: 'open | monitor [save [id]] | task start <name>|end | runs [import|show <id>] | setup | doctor | check | fetch | update | ledger | apply | prune [move|revert] | agents pin <url>|check|update [file]|list | pull | routing ask|auto|off | effort advise|auto|off | mark <note> | prefer <class> <model> <effort> | dismiss <n|id>',
    })
    void refresh($)
    $.clock.every(1000, async () => {
      if (Object.keys((await read($, live)).agents).length > 0) await update($, tick, n => n + 1)
    })
    if (refreshMinutes > 0) {
      $.clock.every(Math.max(1, refreshMinutes) * 60000, () => {
        void refresh($)
      })
    }
    return next(e)
  })

  // Every prompt: does it read as a different task, in a session that re-reads a lot per turn? Then say what that
  // costs per turn against a fresh window, and offer to compact down to the new task. Nothing is dropped or rewritten.
  on('prompt.submit', async ($, e, next) => {
    if (driftOff || e.text.trim().startsWith('/')) return next(e)
    await seedVocab($)
    const words = wordsOf(e.text)
    const tk = ticketsOf(e.text)
    const novel = [...words].filter(w => !vocab.has(w)).length
    const newTicket = [...tk].find(t => !ticketsSeen.has(t))
    const drift = vocab.size >= 20 && words.size >= 6 && (novel / words.size >= 0.7 || !!newTicket)
    for (const w of words) vocab.add(w)
    for (const t of tk) ticketsSeen.add(t)
    if (!drift) return next(e)
    const turns = await $.session.turns().catch(() => 0)
    if (turns - lastSwitchTurn < 10) return next(e)
    const ctx = await contextTokens($)
    if (!ctx?.tokens || ctx.tokens < contextWarn) return next(e)
    lastSwitchTurn = turns
    const model = await $.session.model().catch(() => '')
    const rate = cacheRate(model)
    const perTurn = (ctx.tokens / 1e6) * rate
    const fresh = (PREFIX_TOKENS / 1e6) * rate
    const why = `${newTicket ? newTicket + ', ' : ''}${Math.round((100 * novel) / Math.max(1, words.size))}% new words`
    const at = await $.clock.now()
    const compact = 'Compact now, keeping only this task'
    const here = 'Send it here as it is'
    const never = 'Send it, and stop asking this session'
    let action: Switch['action'] = 'asked'
    try {
      const a = await $.ui.ask(
        `This reads as a different task (${why}) in a session that re-reads ${kilo(ctx.tokens)} tokens every turn: ${money(perTurn)} per turn on ${model || 'this model'}; a new window or terminal starts at ${kilo(PREFIX_TOKENS)}, ${money(fresh)}. Over 50 turns: ${money(perTurn * 50)} against ${money(fresh * 50)}. Next time, open a new window for a new task.`,
        { options: [compact, here, never], header: 'Context' })
      if (a === compact) {
        pendingCompact = `Keep only what this task needs: "${e.text.slice(0, 240)}". Drop the earlier, unrelated tasks.`
        action = 'compacted'
        $.ui.toast('this turn runs as it is; the session compacts down to this task when it ends')
      } else {
        action = 'kept'
        if (a === never) driftOff = true
      }
    } catch {
      action = 'kept'   // no one to ask: a -p run, or dismissed
    }
    await update($, switches, xs => [...xs, { at, ctx: ctx.tokens ?? 0, why, action }].slice(-20))
    return next(e)
  })

  // After each turn the context grew: keep the status line's ctx figure current without re-running the scripts.
  on('turn.complete', async ($, e, next) => {
    if (pendingCompact) {
      const instructions = pendingCompact
      pendingCompact = null
      try {
        await $.session.compact({ instructions })
        $.ui.toast('compacted: the earlier tasks are summarised away; the next turns re-read less')
      } catch (err) {
        $.ui.toast(`could not compact: ${err instanceof Error ? err.message : String(err)}`)
      }
    }
    const s = await read($, status)
    if (s?.json && statusMode !== 'off') {
      const ctx = await contextTokens($)
      $.ui.status(statusLine(s.json, s.rateLimits, (await read($, routed)).length, statusMode, ctx?.tokens ?? null, await $.session.model().catch(() => '')))
    }
    if (e.agentId !== undefined) {
      const id = e.agentId
      const now = await $.clock.now()
      await update($, live, v => {
        const a = v.agents[id]
        if (!a) return v
        const u = e.usage
        const stopped = e.reason === 'aborted' || e.isAborted
        const done: RunningAgent = { ...a, done: now, cost: u ? turnCost(u) : null, out: u?.output_tokens ?? 0, failed: e.reason === 'error' || e.reason === 'refusal', stopped, model: u?.model ?? a.model, answer: (e.answer ?? '').slice(0, 2000) }
        const { [id]: _gone, ...rest } = v.agents
        const nn = String(a.n).padStart(2, '0')
        const ev: RunEvent = done.stopped
          ? { at: now, runId: a.runId, text: `${nn} ${a.type} stopped after ${secs(now - a.startedAt)}`, color: 'red' }
          : done.failed
            ? { at: now, runId: a.runId, text: `${nn} ${a.type} failed (${e.reason}) after ${secs(now - a.startedAt)}`, color: 'red' }
            : { at: now, runId: a.runId, text: `${nn} ${a.type} done in ${secs(now - a.startedAt)}${done.cost !== null ? `, ${money(done.cost)}` : ''}`, color: 'green' }
        const runs = v.runs.map(r => (r.id === a.runId ? { ...r, cost: r.cost + (done.cost ?? 0), failedN: r.failedN + (done.failed ? 1 : 0), stoppedN: r.stoppedN + (done.stopped ? 1 : 0) } : r))
        return { ...v, agents: rest, finished: [...v.finished, done].slice(-200), doneN: v.doneN + 1, doneCost: v.doneCost + (done.cost ?? 0), failedN: v.failedN + (done.failed ? 1 : 0), stoppedN: v.stoppedN + (done.stopped ? 1 : 0), events: [...v.events, ev].slice(-400), runs }
      })
      await closeIdleRuns($)
    }
    if (e.agentId === undefined) {
      const p = plans.get(e.turnId)
      plans.delete(e.turnId)
      const u = e.usage
      const t: Turn = { at: await $.clock.now(), turnId: e.turnId, model: u?.model ?? '', effort: p?.applied ?? p?.sessionEffort ?? '', sessionEffort: p?.sessionEffort ?? '',
        in: u?.input_tokens ?? 0, out: u?.output_tokens ?? 0, cacheRead: u?.cache_read_input_tokens ?? 0, cacheWrite: u?.cache_creation_input_tokens ?? 0,
        cost: u ? turnCost(u) : 0, errors: p?.errors ?? 0, agentCalls: p?.agentCalls ?? 0, routed: p?.routed ?? 0, family: p?.family ?? null, gear: p?.gear ?? 'same', advised: p?.wouldApply ?? null }
      await update($, live, v => ({ ...v, turns: [...v.turns, t].slice(-60), main: { ...v.main, busy: false, lastAt: t.at } }))
      await closeIdleRuns($)
    }
    return next(e)
  })

  on('command.run', { command: 'router' }, async ($, e) => {
    // No argument is 'open': an empty string splits to [''], which would miss the default.
    const [verb = 'open', arg = ''] = e.args.trim().split(/\s+/).filter(Boolean)
    const tail = e.args.trim().split(/\s+/).filter(Boolean).slice(1).join(' ')   // every word after the verb: agents pin <url>, agents update <file...>
    if (verb === 'open') {
      const opened = await $.ui.open({ id: PANE, title: 'Model router' })
      void refresh($)
      return { text: opened.isPlaced ? 'Model router pane opened.' : `The pane waits for room: ${opened.reason}` }
    }
    if (verb === 'monitor') {
      if (arg === 'save') return { text: await saveReport($, tail.split(/\s+/)[1] ?? null) }
      const opened = await $.ui.open({ id: MONITOR, title: 'Agent run' })
      const lv = await read($, live)
      const text = monitorLines(lv, await $.clock.now(), await read($, monitorRun)).map(l => l.text).join('\n')
      return { text: (opened.isPlaced ? 'Agent run pane opened.' : `The pane waits for room: ${opened.reason}`) + '\n' + text + (lv.runs.length > 1 ? `\n(${lv.runs.length} runs this session: h in the pane lists them; /router runs lists the saved ones)` : '') }
    }
    // A named task: every agent from now joins one run, until it is ended; the run is saved then.
    if (verb === 'task') {
      const lv = await read($, live)
      if (arg === 'start') {
        const name = tail.replace(/^start\s*/, '').trim()
        if (!name) return { text: 'task start needs a name, e.g. /router task start cache invalidation bug' }
        if (lv.task) return { text: `task "${lv.task}" is open; /router task end closes it first.` }
        await update($, live, v => ({ ...v, task: name }))
        return { text: `task "${name}" open: every agent from now joins it, whatever prompts follow, until /router task end.` }
      }
      if (arg === 'end') {
        if (!lv.task) return { text: 'no task open.' }
        const id = `task:${slug(lv.task)}`
        const now = await $.clock.now()
        await update($, live, v => ({ ...v, task: null, runs: v.runs.map(r => (r.id === id ? { ...r, endedAt: now } : r)) }))
        const file = runOf(lv, id) ? await saveRun($, id) : null
        return { text: `task "${lv.task}" closed${file ? `; saved to ${file}` : ' (no agent ran under it)'}.` }
      }
      return { text: lv.task ? `task "${lv.task}" open (/router task end closes it).` : 'no task open; /router task start <name> groups the agents that follow under one run until /router task end.' }
    }
    // The runs saved on this machine: list them, show one, import the days before the widget watched from the transcripts.
    if (verb === 'runs') {
      const py = await findPython($)
      const words = tail.split(/\s+/).filter(Boolean)
      if (arg === 'import' || arg === 'show') {
        const r = await $.process.run([py, 'tools/runs.py', ...words], { cwd: repo, env: pyEnv(), timeoutMs: 180000 })
        if (arg === 'import') void listSavedRuns($)
        return { text: r.exitCode === 0 ? r.stdout.trim() || 'nothing' : `runs ${arg} failed: ${r.stderr.trim().split('\n').pop() ?? ''}` }
      }
      const rows = await listSavedRuns($)
      if (rows.length === 0) return { text: `no run saved yet under ${runsDir || '<config>/model-router/runs'}; a run is saved when its last agent ends (or the task is ended). /router runs import rebuilds the days before the widget watched from the transcripts.` }
      return { text: [`${rows.length} saved run${rows.length === 1 ? '' : 's'} (${runsDir}):`, ...rows.slice(-30).map(r => `  ${stamp(r.startedAt)}  ${(r.name ? `task ${r.name}` : r.prompt).slice(0, 60).padEnd(60)}  ${String(r.agentN).padStart(3)} agents  ${money(r.cost).padStart(6)}  ${r.source === 'transcript' ? 'from transcripts' : ''}  ${r.id}`), '/router runs show <id> prints one; /router monitor save <id> writes its report into docs/runs/.'].join('\n') }
    }
    if (verb === 'check' || verb === 'fetch') {
      await refresh($, verb === 'fetch')
      const s = await read($, status)
      const ctx = await contextTokens($)
      const modelNow = await $.session.model().catch(() => '')
      const lv = await read($, live)
      return { text: [...liveLines(lv, ctx?.tokens ?? null, modelNow, s?.json ?? null, mainEffortMode), ...agentsLines(lv, await $.clock.now(), true), ...versionLines(s?.json ?? null, true), BLANK, ...(s?.json ? summaryLines(s.json, s.at, await read($, routed), s.where, true, await read($, switches), ctx?.tokens ?? null, modelNow) : [line(s?.error ?? 'no status')])].map(l => l.text).join('\n') }
    }
    if (verb === 'prefer') {
      const words = e.args.trim().split(/\s+/).slice(1)
      const s = await read($, status)
      if (words.length === 0) {
        const mine = Object.entries(s?.json?.overrides?.[projectKey] ?? {})
        return { text: mine.length ? `overrides for this project (${projectKey}): ${mine.map(([c, o]) => `${c} -> ${o.model} ${o.effort} since ${o.since}`).join('; ')}` : `no override for this project (${projectKey}); /router prefer <class> <model> <effort>` }
      }
      const py = await findPython($)
      if (words[0] === 'clear' && words[1]) {
        await $.process.run([py, 'tools/overrides.py', 'clear', '--', projectKey, words[1]], { cwd: repo, env: pyEnv(), timeoutMs: 20000 })
        await recordChange($, 'override', `cleared ${words[1]} in ${projectKey}`)
        return { text: `override cleared: ${words[1]} in this project; the family default applies again.` }
      }
      const [cls, mdl, eff] = words
      if (!cls || !mdl || !eff || !MODELS.has(mdl) || !EFFORTS.has(eff)) return { text: 'prefer needs <class> <model> <effort>, e.g. /router prefer research-synthesis opus low (models haiku|sonnet|opus|fable; efforts low|medium|high|xhigh|max)' }
      const r = await $.process.run([py, 'tools/overrides.py', 'set', '--why', 'set from the pane', '--', projectKey, cls, mdl, eff], { cwd: repo, env: pyEnv(), timeoutMs: 20000 })
      if (r.exitCode !== 0) return { text: `could not set the override: ${r.stderr.trim().split('\n').pop() ?? ''}` }
      await recordChange($, 'override', `${cls} -> ${mdl} ${eff} in ${projectKey}`)
      return { text: `override set for this project: ${cls} calls run on ${mdl} ${eff} (ask or auto mode). The pane counts the saving from now; /router prefer clear ${cls} undoes it.` }
    }
    if (verb === 'dismiss' || verb === 'undismiss') {
      const s = await read($, status)
      const list = s?.json ? orderedSuggestions(s.json, verb === 'undismiss') : []
      const pick = /^\d+$/.test(arg) ? list[Number(arg) - 1]?.id : arg
      if (!pick) return { text: `${verb} needs the suggestion's number from the pane or its id (e.g. /router dismiss 2, /router undismiss effort)` }
      const py = await findPython($)
      await $.process.run([py, 'tools/overrides.py', verb, pick], { cwd: repo, env: pyEnv(), timeoutMs: 20000 })
      await refresh($)
      return { text: verb === 'dismiss' ? `dismissed ${pick}: hidden from the glance, listed under Details; /router undismiss ${pick} brings it back.` : `${pick} is back in the list.` }
    }
    if (verb === 'mark') {
      const note = e.args.trim().replace(/^mark\s*/, '')
      if (!note) return { text: 'mark needs a note of what you changed, e.g. /router mark effort low from today' }
      await recordChange($, 'mark', note)
      return { text: `change recorded: ${note}. The pane counts what the transcripts save from now.` }
    }
    if (verb === 'effort') {
      if (arg === 'off' || arg === 'auto' || arg === 'advise') {
        if (arg === 'auto' && mainEffortMode !== 'auto') void recordChange($, 'routing', 'main-session effort auto for this session')
        mainEffortMode = arg
      }
      return { text: `main-session effort ${mainEffortMode} for this session${arg ? '' : ' (effort advise|auto|off sets it)'}: a prompt that reads as a measured family runs at its measured effort (auto), or the pane says what it would have done (advise); /config makes it permanent.` }
    }
    if (verb === 'routing') {
      if (arg === 'ask' || arg === 'auto' || arg === 'off') {
        const was = routingMode
        routingMode = arg
        if (arg === 'auto' && was !== 'auto') void recordChange($, 'routing', 'auto for this session', measuredProjected((await read($, status))?.json))
      }
      return { text: `routing ${routingMode} for this session${arg ? '' : ' (routing ask|auto|off sets it)'}; /config makes it permanent.` }
    }
    // First run on a machine: install the routed agents, then say what the pane's yellow lines mean and what comes next.
    if (verb === 'setup') {
      await $.ui.open({ id: PANE, title: 'Model router' })
      const started = await runJob($, 'apply')
      const s = await read($, status)
      const a = s?.json?.agents
      return { text: [
        started ? 'apply agents started: the routed agent files this repository ships are installed or updated in ~/.claude/agents (the pane shows the output).' : 'apply agents did not start (see the toast); the rest still applies.',
        'What the pane shows: the yellow "to check" lines are things to do, not failures; a suggestion line is an estimate from your own transcripts or the benchmark, with its basis under Details.',
        'Routing: in ask mode (the default) the router asks before moving an Agent call to the measured model; /router routing auto moves them without asking; /config makes it permanent.',
        a && a.files > 20 ? `Then: ${a.files} agent files sit in ~/.claude/agents and every one adds its description to every request; /router prune lists the ones nothing here has called, /router prune move parks them (reversible: /router prune revert).` : 'Then: /router check any time for the text of the pane; /router prune lists the agent files nothing here has called.',
      ].join('\n') }
    }
    // The installation piece by piece, as a job in the pane: what is there, what is missing and the step for it.
    if (verb === 'doctor') {
      await $.ui.open({ id: PANE, title: 'Model router' })
      const started = await runJob($, 'doctor')
      return { text: started ? 'installation check started; the pane lists each piece as ok or the step to take (python3 tools/status.py --doctor prints the same at a terminal).' : 'Not started.' }
    }
    if (verb === 'agents') {
      const j = agentsJob(tail)
      if (!j) return { text: 'agents takes: pin <repository url> | check | update [file.md ...] [--accept-flags] | list. A flagged change is taken only by name with --accept-flags.' }
      await $.ui.open({ id: PANE, title: 'Model router' })
      const started = await runJob($, j.name, j.extra)
      return { text: started ? `${JOBS[j.name].title} started; the pane shows its output${j.name === 'agents-check' ? '; /router agents update takes the unflagged changes, /router agents update <file> --accept-flags a flagged one you have read' : j.name === 'agents-update' ? '; /router apply then puts the routed model and effort back' : ''}.` : 'Not started.' }
    }
    if (verb === 'prune') {
      const name = pruneJob(arg)
      if (!name) return { text: 'prune takes nothing (dry run), move or revert: /router prune | /router prune move | /router prune revert' }
      await $.ui.open({ id: PANE, title: 'Model router' })
      const started = await runJob($, name)
      return { text: started ? `${JOBS[name].title} started; the pane shows its output${name === 'prune' ? '; /router prune move does it, /router prune revert undoes it' : name === 'prune-move' ? '; /router prune revert undoes it' : ''}.` : 'Not started.' }
    }
    const spec = JOBS[verb]
    if (spec) {
      await $.ui.open({ id: PANE, title: 'Model router' })
      const started = await runJob($, verb)
      return { text: started ? `${spec.title} started; the pane shows its output.` : 'Not started.' }
    }
    return { text: 'Usage: /router [open | monitor [save [id]] | task start <name>|end | runs [import [--days N] | show <id>] | setup | doctor | check | fetch | update | ledger | apply | prune [move|revert] | agents pin <url>|check|update [file] [--accept-flags]|list | pull | routing ask|auto|off | effort advise|auto|off | mark <note> | prefer <class> <model> <effort> | dismiss <n|id>]' }
  })

  // A subagent starts: one row in the agents block, under its parent when it has one.
  // The routing decision for this Agent call (made in tool.call below) is applied here, on the spawn, never on the
  // Agent tool's input: a tool input a hook changes loses the auto-mode review and the call is bounced once.
  on('agent.spawn', async ($, e, next) => {
    const now = await $.clock.now()
    for (const [k, v] of pendingRoutes) if (now - v.at > PENDING_MS) pendingRoutes.delete(k)
    const key = pendingRoutes.has(e.tool_use_id) ? e.tool_use_id : [...pendingRoutes].find(([, v]) => v.description === e.description && v.prompt === e.prompt)?.[0]
    const want = key !== undefined ? pendingRoutes.get(key) : undefined
    if (key !== undefined) pendingRoutes.delete(key)
    const r = await next(want ? { ...e, model: want.model as 'haiku' | 'sonnet' | 'opus' | 'fable', ...(want.family === 'repo_fix' ? { prompt: e.prompt + RUNNER_NOTE } : {}) } : e)
    if (r.agentId) {
      const a: RunningAgent = { id: r.agentId, parent: e.parentAgentId ?? null, type: e.subagentType, description: e.description, model: r.model, effort: want?.effort ?? '', wantEffort: want?.effort ?? null,
        family: want?.family ?? matchFamily(e.subagentType, e.prompt)?.family ?? null, startedAt: 0, lastStepAt: 0, steps: 0, done: null, cost: null, out: 0, failed: false, stopped: false,
        ctx: Math.round(e.prompt.length / 4), n: 0, run: 1, recent: [], runId: '', answer: '' }
      a.startedAt = a.lastStepAt = now
      await update($, live, v => {
        // The engine resumes an agent under the same id (a hand-back, a follow-up message): that is a new run of the same box, not a new agent.
        const prior = v.finished.filter(x => x.id === a.id)
        const n = prior.length ? prior[0].n : v.nextN
        const run = prior.length + 1
        const nn = String(n).padStart(2, '0')
        const parentRec = a.parent ? (v.agents[a.parent] ?? [...v.finished].reverse().find(x => x.id === a.parent)) : undefined
        const by = a.parent ? ` by ${String(parentRec?.n ?? 0).padStart(2, '0')}` : ''
        // The run it joins: the open named task; else the run of its earlier self (a resume) or of its spawner; else this prompt's.
        const runId = v.task ? `task:${slug(v.task)}` : prior.length ? prior[prior.length - 1].runId : parentRec ? parentRec.runId : `turn:${currentTurn || 'start'}`
        const have = v.runs.find(r => r.id === runId)
        const meta: RunMeta = have ? { ...have, endedAt: null, agentN: have.agentN + 1 } : { id: runId, startedAt: now, endedAt: null, prompt: (v.task ?? lastPrompt).slice(0, 120), name: v.task, agentN: 1, cost: 0, failedN: 0, stoppedN: 0, saved: null }
        const ev: RunEvent = { at: now, runId, text: run > 1 ? `${nn} ${a.type} resumed (run ${run}, ~${kilo(a.ctx)} ctx)` : `${nn} ${a.type} spawned on ${shortModel(a.model)}${a.effort ? ' ' + a.effort : ''} (~${kilo(a.ctx)} ctx)${by}` }
        return { ...v, nextN: prior.length ? v.nextN : n + 1, agents: { ...v.agents, [a.id]: { ...a, n, run, runId } }, events: [...v.events, ev].slice(-400), runs: have ? v.runs.map(r => (r.id === runId ? meta : r)) : [...v.runs, meta] }
      })
    }
    return r
  }).catch(($, e, next) => {
    $.ui.toast(`router: the spawn hook failed (${failureText(next.error)}); ${e.subagentType} runs as asked`)
    return next(e)
  })

  // The main loop's turn begins: what its prompt reads as decides the effort its requests may run at.
  on('turn.start', async ($, e, next) => {
    if (e.agentId !== undefined) return next(e)
    currentTurn = e.turnId
    lastPrompt = e.text ?? ''
    const began = await $.clock.now()
    await update($, live, v => ({ ...v, main: { ...v.main, busy: true, since: began } }))
    const m = e.text ? matchFamily('', e.text) : null
    const s = await read($, status)
    const f = m && s?.json ? s.json.families.find(x => x.name === m.family) : null
    const escalated = m ? (await read($, live)).escalated[m.family] : undefined
    plans.set(e.turnId, { family: m?.family ?? null, effort: f?.effort && EFFORTS.has(f.effort) && !escalated ? f.effort : null, sessionEffort: '', applied: null, wouldApply: null, errors: 0, agentCalls: 0, routed: 0, gear: 'same' })
    return next(e)
  })

  // Before each main-loop request: the family's measured effort when the prompt read as one (auto), the session's own
  // effort again once the turn hit 3 tool errors (the task is harder than its words), nothing otherwise.
  on('turn.step', async function* ($, e, next) {
    if (e.agentId !== undefined) {
      const id = e.agentId
      const a0 = (await read($, live)).agents[id]
      const want = a0?.wantEffort && EFFORTS.has(a0.wantEffort) ? a0.wantEffort as 'low' | 'medium' | 'high' | 'xhigh' | 'max' : null
      if (a0) {
        const at = await $.clock.now()
        await update($, live, v => {
          const a = v.agents[id]
          return a ? { ...v, agents: { ...v.agents, [id]: { ...a, steps: a.steps + 1, lastStepAt: at, model: e.model || a.model, effort: want ?? (typeof e.effort === 'string' ? e.effort : a.effort) } } } : v
        })
      }
      // The routed effort rides on the subagent's own requests (the spawn carries the model, not the effort).
      return yield* next(want && e.effort !== want ? { ...e, effort: want } : e)
    }
    const p = plans.get(e.turnId)
    if (!p) return yield* next(e)
    if (e.index === 0 || !p.sessionEffort) p.sessionEffort = typeof e.effort === 'string' ? e.effort : e.effort === undefined ? '' : String(e.effort)
    if (mainEffortMode === 'off' || !p.effort || p.effort === p.sessionEffort) return yield* next(e)
    if (p.errors >= ESCALATE_ERRORS) {
      if (p.applied && p.applied !== p.sessionEffort) { p.gear = 'up'; $.ui.toast(`router: ${p.errors} tool errors this turn: back to ${p.sessionEffort || 'the session\'s'} effort`) }
      p.applied = p.sessionEffort || null
      return yield* next(e)
    }
    if (mainEffortMode === 'advise') { p.wouldApply = p.effort; return yield* next(e) }
    if (!p.applied) $.ui.toast(`router: this turn reads as ${p.family} (measured at ${p.effort}); running at ${p.effort}`)
    p.applied = p.effort
    p.gear = 'down'
    return yield* next({ ...e, effort: p.effort as 'low' | 'medium' | 'high' | 'xhigh' | 'max' })
  })

  // What every main-loop tool call came to: the errors and Agent calls of the turn in progress.
  on('tool.call', async ($, e, next) => {
    const r = await next(e)
    const agentId = (e as { agentId?: string }).agentId
    if (agentId !== undefined && (await read($, live)).agents[agentId]) {
      const rec: Recent = { at: await $.clock.now(), text: toolText(e as unknown as Record<string, unknown>), err: (r as { isError?: boolean }).isError === true }
      await update($, live, v => {
        const a = v.agents[agentId]
        return a ? { ...v, agents: { ...v.agents, [agentId]: { ...a, recent: [...a.recent, rec].slice(-8) } } } : v
      })
    }
    if (agentId === undefined) {
      const p = plans.get(currentTurn)
      if (p) {
        if (e.tool === 'Agent') p.agentCalls++
        if ((r as { isError?: boolean }).isError) p.errors++
      }
      // The main session's own tail, for the monitor's root panel.
      const rec: Recent = { at: await $.clock.now(), text: toolText(e as unknown as Record<string, unknown>), err: (r as { isError?: boolean }).isError === true }
      await update($, live, v => ({ ...v, main: { ...v.main, recent: [...v.main.recent, rec].slice(-8) } }))
    }
    return r
  })

  // Every Agent call: when a measured family covers the task and the call asks for something dearer than
  // the family's decision, route it (auto), ask (ask), or leave it (off). Nothing unmeasured is touched.
  // The decision is kept for the agent.spawn this call makes; the Agent tool's own input stays as the model wrote it.
  // A family escalated this session (a routed call failed, or was re-issued within minutes) runs as asked.
  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    if (routingMode === 'off') return next(e)
    const s = await read($, status)
    const agent = e.subagent_type ?? 'general-purpose'
    const fam = matchFamily(agent, e.prompt)?.family ?? null
    if (fam) {
      const lv = await read($, live)
      const now = await $.clock.now()
      const reissued = !lv.escalated[fam] && (await read($, routed)).some(r => r.family === fam && r.agent === agent && r.decision !== 'kept' && r.decision !== 'escalated' && now - r.at < REISSUE_MS && similar(r.description, e.description))
      const why = lv.escalated[fam] ?? (reissued ? 're-issued within 10 min of a routed call' : null)
      if (why) {
        if (reissued) await update($, live, v => ({ ...v, escalated: { ...v.escalated, [fam]: why } }))
        const asked = e.model ? `${e.model} ${e.effort ?? '(default effort)'}` : (s?.json?.agents.routed.find(r => r.name === agent)?.have ?? 'inherit')
        await update($, routed, r => [...r, { at: now, agent, family: fam, from: asked, to: 'as asked', decision: 'escalated' as const, description: e.description }].slice(-50))
        await logRouted($, fam, agent, asked, 'as asked', 'escalated')
        $.ui.toast(`router: ${agent} runs as asked (${fam} escalated this session: ${why})`)
        return next(e)
      }
    }
    const c = s?.json ? decideCall(s.json, agent, e.prompt, e.model, e.effort) : null
    if (!c) return next(e)
    let decision: Routed['decision'] = 'auto'
    if (routingMode === 'ask') {
      const choice = await askRoute($, c)
      if (choice === 'auto') {
        routingMode = 'auto'
        void recordChange($, 'routing', 'auto for this session (always)', measuredProjected(s?.json))
      }
      decision = choice === 'keep' ? 'kept' : choice === 'auto' ? 'auto' : 'routed'
    }
    const at = await $.clock.now()
    await update($, routed, r => [...r, { at, agent, family: c.family, from: c.asked, to: `${c.model} ${c.effort}`, decision, description: e.description }].slice(-50))
    await logRouted($, c.family, agent, c.asked, `${c.model} ${c.effort}`, decision)
    if (decision === 'kept') return next(e)
    $.ui.toast(`router: ${agent} on ${c.model} ${c.effort} (${c.family} ${c.rate})`)
    const p = plans.get(currentTurn)
    if (p) p.routed++
    // Not a rewrite of the tool input (auto mode would bounce the call): the spawn inside this call picks it up.
    pendingRoutes.set(e.tool_use_id ?? `${at}:${e.description}`, { at, description: e.description, prompt: e.prompt, model: c.model, effort: c.effort, family: c.family })
    const r = await next(e)
    // The routed call failed: the family runs as asked for the rest of the session, and the pane says why.
    if ((r as { isError?: boolean }).isError && c.family !== 'override') {
      await update($, live, v => ({ ...v, escalated: { ...v.escalated, [c.family]: `a call routed to ${c.model} ${c.effort} failed` } }))
      $.ui.toast(`router: the ${c.family} call on ${c.model} ${c.effort} failed; the next ones run as asked`)
    }
    return r
  }).catch(($, e, next) => {
    $.ui.toast(`router: the routing hook failed (${failureText(next.error)}); the Agent call runs as asked`)
    return next(e)
  })

  // The run monitor: its own pane. The graph view draws the scene (boxes with a border in the state's colour, the arrows
  // between them) beside the live panels when the pane is wide, under them when it is not; the list view is the text.
  on('ui.render', { component: 'Pane', requestId: MONITOR }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const lvAll = await read($, live)
    const view = await read($, monitorView)
    const picked = await read($, monitorRun)
    const history = await read($, monitorHistory)
    const saved = await read($, savedRuns)
    await read($, tick)
    const now = await $.clock.now()
    const width = Math.max(40, (e.props as { bodyColumns?: number }).bodyColumns ?? (e.viewport?.columns ?? 100) - 1)
    const shownId = picked ?? latestRunId(lvAll)
    const lv = scopeOf(lvAll, picked)
    const running = Object.values(lv.agents)
    const spin = running.length ? SPIN[Math.floor(now / 1000) % SPIN.length] + ' ' : ''
    const footer = (
      <Box flexDirection="row" gap={1} flexWrap="wrap">
        <Button key="view" hotkey="g" onPress={() => { void update($, monitorView, v => (v === 'graph' ? 'list' : 'graph')) }}>{view === 'graph' ? 'List' : 'Graph'}</Button>
        <Button key="history" hotkey="h" onPress={() => { void update($, monitorHistory, v => !v); void listSavedRuns($) }}>{history ? 'Back' : `History (${lvAll.runs.length})`}</Button>
        <Button key="save" hotkey="s" onPress={() => { void saveReport($, shownId).then(t => $.ui.toast(`router: ${t}`)) }}>Save report</Button>
        {picked !== null && <Button key="current" hotkey="c" onPress={() => { void update($, monitorRun, () => null) }}>Current run</Button>}
        <Button key="main" hotkey="m" onPress={() => { void $.ui.open({ id: PANE, title: 'Model router' }) }}>Model router</Button>
      </Box>
    )
    const runText = <Text dimColor>{runLine(lvAll, picked)}</Text>
    if (history) {
      const inSession = new Set(lvAll.runs.map(r => r.id))
      const older = saved.filter(r => !inSession.has(r.id)).slice(-20).reverse()
      const row = (r: RunMeta) => `${clock(r.startedAt)}  ${(r.name ? `task ${r.name}` : r.prompt).slice(0, 56).padEnd(56)}  ${String(r.agentN).padStart(2)} agents  ${money(r.cost).padStart(6)}${r.endedAt ? '' : '  running'}${r.failedN || r.stoppedN ? `  ${r.failedN + r.stoppedN} failed/stopped` : ''}`
      return (
        <Box flexDirection="column">
          <Text color="cyan" bold>[ Runs this session ]</Text>
          {lvAll.runs.length === 0 && <Text dimColor>none yet</Text>}
          {[...lvAll.runs].reverse().map((r, i) => (
            <Button key={`run-${r.id}`} hotkey={i < 9 ? String(i + 1) : undefined} onPress={() => { void update($, monitorRun, () => r.id); void update($, monitorHistory, () => false) }}>{(r.id === shownId ? '▶ ' : '  ') + row(r)}</Button>
          ))}
          <Text> </Text>
          <Text color="cyan" bold>[ Saved on this machine ]</Text>
          {older.length === 0 && <Text dimColor>{saved.length ? 'all listed above' : 'none listed; /router runs lists them, /router runs import rebuilds the days before the widget watched'}</Text>}
          {older.map(r => <Text dimColor>{`${stamp(r.startedAt)}  ${(r.name ? `task ${r.name}` : r.prompt).slice(0, 56).padEnd(56)}  ${String(r.agentN).padStart(2)} agents  ${money(r.cost).padStart(6)}  ${r.source === 'transcript' ? 'from transcripts' : ''}  ${r.id}`}</Text>)}
          <Text dimColor>/router runs show &lt;id&gt; prints a saved run; /router monitor save &lt;id&gt; writes its report into docs/runs/</Text>
          {footer}
        </Box>
      )
    }
    if (view === 'list') {
      const cut = (t: string) => (t.length > width ? t.slice(0, width - 1) + '…' : t)
      return (
        <Box flexDirection="column">
          {monitorLines(lvAll, now, picked).map(l => (
            <Text color={l.color} weight={l.bold ? 'bold' : undefined} dimColor={l.dim}>{l.text === '' ? ' ' : cut(l.text)}</Text>
          ))}
          {footer}
        </Box>
      )
    }
    const twoCol = width >= 130
    const rightW = 50
    const graphW = (twoCol ? width - rightW - 1 : width) - 4
    const scene = sceneOf(lv, now, graphW)
    const { all } = treeOf(lv)
    const tails = [...[...running].sort((x, y) => y.lastStepAt - x.lastStepAt).slice(0, 2)]
    tails.push(...[...lv.finished].sort((x, y) => Number(bad(y)) - Number(bad(x)) || (y.done ?? 0) - (x.done ?? 0)).slice(0, 2 - tails.length))
    const panel = (a: RunningAgent) => {
      const { color } = stateOf(a, now)
      const state = a.done === null ? `RUNNING ${secs(now - a.startedAt)}` : endWord(a)
      return (
        <Box borderStyle="round" borderColor={color} borderDimColor={!color} flexDirection="column" paddingX={1}>
          <Box flexDirection="row" justifyContent="space-between">
            <Text color={color} bold>{`● ${String(a.n).padStart(2, '0')} ${a.type}${a.run > 1 ? ` · run ${a.run}` : ''} / ${a.done === null ? 'live' : 'stopped'}`}</Text>
            <Text color={color}>{`[${state}]`}</Text>
          </Box>
          {a.recent.length === 0 && <Text dimColor>no tool call yet</Text>}
          {a.recent.slice(-5).map(r => (
            <Text><Text dimColor>{clockS(r.at)}  </Text><Text color={r.err ? 'red' : undefined}>{`${r.err ? 'ERROR ' : ''}${r.text}`}</Text></Text>
          ))}
          {a.done === null && <Text color="cyan">{`$ ${Math.floor(now / 1000) % 2 ? '▌' : ' '}`}</Text>}
        </Box>
      )
    }
    const graph = (
      <Box borderStyle="single" borderDimColor flexDirection="column" paddingX={1}>
        <Text color="cyan" bold>[ Run graph ]</Text>
        <Text dimColor>{`${all.length} agent${all.length === 1 ? '' : 's'} this session · graph: live · ${running.length ? 'at work' : lv.main.busy ? 'main session at work' : 'idle'}`}</Text>
        {all.length === 0 && <Text dimColor>no agent spawned yet; Agent calls hang under the session box as they spawn</Text>}
        <Box position="relative" width={scene.width} height={scene.height}>
          {[...scene.rows].flatMap(([y, segs]) => segs.map(s => (
            <Box position="absolute" top={y} left={s.x}><Text color={s.color} dimColor={!s.color}>{s.text}</Text></Box>
          )))}
          {scene.boxes.map(b => (
            <Box position="absolute" top={b.y} left={b.x} width={b.w} borderStyle="round" borderColor={b.color} borderDimColor={!b.color} flexDirection="column">
              <Text bold wrap="truncate">{b.title}</Text>
              <Text wrap="truncate"><Text color={b.color}>{b.state}</Text><Text>{b.figures ? `  ${b.figures}` : ''}</Text></Text>
              <Text dimColor wrap="truncate">{b.desc}</Text>
            </Box>
          ))}
        </Box>
        <Text dimColor>arrow = context sent, estimated from the prompt (4 chars/token): ━━ ≥16k  ── 4k–16k  ┄┄ &lt;4k</Text>
      </Box>
    )
    const events = (
      <Box borderStyle="single" borderDimColor flexDirection="column" paddingX={1}>
        <Text color="cyan" bold>[ Event log ]</Text>
        {lv.events.length === 0 && <Text dimColor>none yet</Text>}
        {lv.events.slice(-8).map(ev => <Text><Text dimColor>{clockS(ev.at)}  </Text><Text color={ev.color}>{ev.text}</Text></Text>)}
      </Box>
    )
    const header = (
      <Box flexDirection="column">
        <Box borderStyle="single" borderColor="cyan" paddingX={1} flexDirection="row" justifyContent="space-between">
          <Text><Text color="cyan" bold>model-router</Text><Text dimColor>  /  </Text><Text bold>Agent run</Text></Text>
          <Text dimColor>{`${spin}${running.length} running · ${lv.doneN} done (${money(lv.doneCost)}${lv.failedN ? `, ${lv.failedN} failed` : ''}${lv.stoppedN ? `, ${lv.stoppedN} stopped` : ''}) · ${clockS(now)}`}</Text>
        </Box>
        {runText}
      </Box>
    )
    // The main session's own panel when there is room: alone before any agent runs, beside a lone agent after.
    const mainPanel = tails.length < 2 && (
      <Box borderStyle="round" borderColor="cyan" flexDirection="column" paddingX={1}>
        <Box flexDirection="row" justifyContent="space-between">
          <Text color="cyan" bold>● 00 main session / live</Text>
          <Text color="cyan">{`[${mainWord(lv.main, now)}]`}</Text>
        </Box>
        {lv.main.recent.length === 0 && <Text dimColor>no tool call yet</Text>}
        {lv.main.recent.slice(-5).map(r => (
          <Text><Text dimColor>{clockS(r.at)}  </Text><Text color={r.err ? 'red' : undefined}>{`${r.err ? 'ERROR ' : ''}${r.text}`}</Text></Text>
        ))}
        {lv.main.busy && <Text color="cyan">$ ▌</Text>}
      </Box>
    )
    const right = <Box flexDirection="column" width={twoCol ? rightW : undefined}>{tails.map(panel)}{mainPanel}</Box>
    return (
      <Box flexDirection="column">
        {header}
        {twoCol ? (
          <Box flexDirection="row" gap={1}>
            <Box flexDirection="column" flexGrow={1}>{graph}{events}</Box>
            {right}
          </Box>
        ) : (
          <Box flexDirection="column">{graph}{right}{events}</Box>
        )}
        {footer}
      </Box>
    )
  })

  // The main pane, drawn like the run monitor: a header bar, then every section in a frame with a title, the border in
  // the section's colour (limits by how full a window is, agents green while any runs, to-check yellow), the buttons
  // in a footer. The lines inside are the same as /router check prints: the producers are shared, only the framing is here.
  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const s = await read($, status)
    const j = await read($, job)
    const busy = j?.isRunning === true
    const full = await read($, details)
    await read($, tick)   // read so the second counter redraws the pane while agents run
    const lv = await read($, live)
    const now = await $.clock.now()
    const ctx = (await contextTokens($))?.tokens ?? null
    const modelNow = await $.session.model().catch(() => '')
    const limits = s?.rateLimits ?? []
    const width = Math.max(40, (e.props as { bodyColumns?: number }).bodyColumns ?? (e.viewport?.columns ?? 100) - 1)
    const inner = width - 4
    // One line stays one line: cut to the frame's width instead of wrapping (/router check keeps the full text).
    const cut = (t: string) => (t.length > inner ? t.slice(0, inner - 1) + '…' : t)
    const row = (l: Line) => <Text color={l.color} weight={l.bold ? 'bold' : undefined} dimColor={l.dim}>{l.text === '' ? ' ' : l.wrap ? l.text : cut(l.text)}</Text>
    const frame = (title: string, lines: Line[], color?: string) => (lines.length === 0 ? null : (
      <Box borderStyle="single" borderColor={color} borderDimColor={!color} flexDirection="column" paddingX={1}>
        <Text color={color ?? 'cyan'} bold>{`[ ${title} ]`}</Text>
        {lines.map(row)}
      </Box>
    ))
    const liveAll = liveLines(lv, ctx, modelNow, s?.json ?? null, mainEffortMode)
    const ver = versionLines(s?.json ?? null, true)[0]
    const worst = Math.max(0, ...limits.map(l => l.percentUsed))
    const summary = s?.json
      ? summaryLines(s.json, s.at, await read($, routed), s.where, full, await read($, switches), ctx, modelNow)
      : [line(s?.error ?? 'reading the checkout…', { color: s?.error ? 'yellow' : undefined, wrap: true })]
    // The summary's sections are separated by blank lines; each becomes a frame, titled by what its first line says.
    const groups: Line[][] = [[]]
    for (const l of summary) {
      if (l.text === '') { if (groups[groups.length - 1].length) groups.push([]) } else groups[groups.length - 1].push(l)
    }
    const titleOf = (first: Line): [string, string | undefined] => {
      const t = first.text.toLowerCase()
      if (t.startsWith('suggestions')) return ['Suggestions', undefined]
      if (t.startsWith('families')) return ['Routing', first.color === 'yellow' ? 'yellow' : undefined]
      if (t.startsWith('to check')) return ['To check', 'yellow']
      if (t.startsWith('by week')) return ['By week', undefined]
      if (t.startsWith('consumption')) return ['Consumption', undefined]
      if (t.startsWith('learned')) return ['Learned on this machine', undefined]
      if (t.startsWith('context')) return ['Context', undefined]
      if (t.startsWith('routed this session')) return ['Routed', 'cyan']
      if (t.startsWith('since') || t.startsWith('no change')) return ['Changes', undefined]
      if (t.startsWith('no model-router checkout') || t.startsWith('reading')) return ['Status', 'yellow']
      return ['Status', undefined]
    }
    const named = groups.filter(g => g.length).map(g => ({ g, t: titleOf(g[0]) }))
    // The glance: what is acted on (the session live, the agents, the limits, what is to check, the top suggestions) and a
    // few dim facts under the header; Details (d) adds every other section, the way /router check prints them.
    const GLANCE_SUGGESTIONS = 3
    const quick: Line[] = []
    if (!full) {
      const status = named.find(x => x.t[0] === 'Status')?.g ?? []
      for (const l of status) if (/^(read |repo |spend )/.test(l.text)) quick.push(line(l.text.replace(/ · prev .*$/, ''), { dim: true }))
      const routedG = named.find(x => x.t[0] === 'Routed')?.g
      if (routedG) quick.push(line(routedG[0].text.replace(/ \(mode .*$/, ''), { dim: true }))
    }
    // a Status that is a warning (no checkout, an error reading it) stays in the glance, in yellow
    const shown = full ? named : named.filter(x => x.t[0] === 'To check' || x.t[0] === 'Suggestions' || (x.t[0] === 'Status' && x.t[1] === 'yellow')).map(x => {
      if (x.t[0] !== 'Suggestions' || x.g.length <= GLANCE_SUGGESTIONS + 1) return x
      return { ...x, g: [...x.g.slice(0, GLANCE_SUGGESTIONS + 1), line(`${x.g.length - GLANCE_SUGGESTIONS - 1} more under Details (d)`, { dim: true })] }
    })
    const sections = busy && j
      ? [frame('Job', [line(`running ${j.name} since ${clock(j.startedAt)} · the summary returns when it ends`, { bold: true })], 'cyan')]
      : [
          frame('Session live', liveAll.slice(1), 'cyan'),
          frame('Agents', agentsLines(lv, now, full), Object.keys(lv.agents).length ? 'green' : undefined),
          frame('Limits', limitLines(limits), worst >= 80 ? 'red' : worst >= 50 ? 'yellow' : 'green'),
          ...shown.map(x => frame(x.t[0], x.g, x.t[1])),
        ]
    const header = (
      <Box flexDirection="column">
        <Box borderStyle="single" borderColor="cyan" paddingX={1} flexDirection="row" justifyContent="space-between">
          <Text><Text color="cyan" bold>model-router</Text><Text dimColor>  /  </Text><Text bold>Model router</Text></Text>
          <Text dimColor>{liveAll[0]?.text.replace(/^this session · /, '') ?? ''}</Text>
        </Box>
        {ver ? <Text color={ver.color} dimColor={ver.dim}>{ver.text}</Text> : null}
        {quick.map(row)}
      </Box>
    )
    const rows = Math.max(12, (e.viewport?.rows ?? 40) - 2)
    const used = busy ? 8 : liveAll.length + 3 + limits.length + summary.length + groups.length * 3 + 8
    const logRoom = Math.max(3, rows - used)
    // A job that ended well keeps one line; its whole output stays under Details, and a failure shows it all.
    const log = j ? (busy || j.exitCode !== 0 || full ? j.lines.slice(-logRoom) : j.lines.slice(-1)) : []
    const jobFrame = j && log.length
      ? frame(busy ? `Job: ${j.name}, running since ${clock(j.startedAt)}` : `Last job: ${j.name}${j.exitCode === null ? '' : ` (exit ${j.exitCode})`}`, log.map(t => line(t, { dim: true })), busy ? 'cyan' : j.exitCode ? 'red' : undefined)
      : null
    return (
      <Box flexDirection="column">
        {header}
        {sections}
        {jobFrame}
        <Box flexDirection="row" gap={1} flexWrap="wrap">
          <Button key="refresh" hotkey="r" onPress={() => { void refresh($) }}>Refresh</Button>
          <Button key="fetch" hotkey="f" onPress={() => { void refresh($, true) }}>Fetch origin</Button>
          <Button key="update" hotkey="u" variant="primary" dimColor={busy} onPress={() => { void runJob($, 'update') }}>Re-check routing</Button>
          <Button key="details" hotkey="d" onPress={() => { void update($, details, v => !v) }}>{full ? 'Less' : 'Details'}</Button>
          <Button key="monitor" hotkey="g" onPress={() => { void $.ui.open({ id: MONITOR, title: 'Agent run' }) }}>Monitor</Button>
          <Button key="ledger" hotkey="l" dimColor={busy} onPress={() => { void runJob($, 'ledger') }}>Ledger now</Button>
          <Button key="apply" hotkey="a" dimColor={busy} onPress={() => { void runJob($, 'apply') }}>Apply agents</Button>
          <Button key="pull" hotkey="p" dimColor={busy} onPress={() => { void runJob($, 'pull') }}>Pull</Button>
        </Box>
      </Box>
    )
  })
}
