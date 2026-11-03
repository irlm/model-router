import { atom, read, update } from 'claude-code'
import type { Hook, Register } from 'claude-code'

import type { Job, RateLimit, Realized, RealizedMainSide, RealizedSide, Routed, Status, StatusJson } from '../types'

type Dollar = Parameters<Hook<'session.start'>>[0]
type RoutingMode = 'ask' | 'auto' | 'off'

const PANE = 'model-router'
// status-3: `where` joined the value (which checkout served: the configured one, or the install's clone)
const status = atom({ plugin: 'model-router', key: 'status' } as const, null, { shape: 'status-3' })
const job = atom({ plugin: 'model-router', key: 'job' } as const, null, { shape: 'job-1' })
// routed-1: the Agent calls the router saw this session, newest last
const routed = atom({ plugin: 'model-router', key: 'routed' } as const, [] as Routed[], { shape: 'routed-1' })
// details-1: whether the pane shows the long sections (agents, dates, consumption, each suggestion's basis)
const details = atom({ plugin: 'model-router', key: 'details' } as const, false, { shape: 'details-1' })

// What the buttons and /router <verb> run, from the checkout's root. In the clone the plugin install
// made (`clone`), nothing is committed: the ledger prints its entry, the re-check keeps its results local.
const JOBS: Record<string, { title: string; argv: (python: string, clone: boolean) => string[] }> = {
  update: { title: 'regression check', argv: (py, clone) => [py, 'tools/update.py', '--sample', '6', ...(clone ? ['--no-commit'] : [])] },
  ledger: { title: 'usage ledger', argv: (py, clone) => [py, 'tools/ledger.py', clone ? '--stdout' : '--commit'] },
  apply: { title: 'apply agents', argv: py => [py, 'apply_agents.py'] },
  pull: { title: 'git pull', argv: () => ['git', 'pull', '--ff-only'] },
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
const savingsUpTo = (s: StatusJson) => (s.suggestions ?? []).reduce((n, g) => n + (g.saving?.[1] ?? 0), 0)

/** The status line under the prompt (the host prefixes the plugin's name): the rate-limit windows, what the
 * router did this session, what a change saved, what the suggestions add up to, what to check. Only what
 * changes a decision; `minimal` keeps the windows, the routed count and the to-check count. */
const statusLine = (s: StatusJson, limits: RateLimit[], routedN = 0, mode: StatusMode = 'full') => {
  const parts = [limitsText(limits)]
  if (routedN > 0) parts.push(`routed ${routedN}`)
  const r = s.changes?.realized
  if (mode === 'full' && r && r.saved !== 0 && !caveats(r)) parts.push(`${r.saved > 0 ? 'saved' : 'cost up'} ${money(Math.abs(r.saved))} since ${r.since.slice(5, 10)}`)
  const upTo = savingsUpTo(s)
  if (mode === 'full' && upTo >= 1) parts.push(`${money(upTo)} to save`)
  if (s.advice.length > 0) parts.push(`${s.advice.length} to check`)
  if (parts.filter(Boolean).length === 0) parts.push('ok')
  return `${parts.filter(Boolean).join(' · ')} · /router`
}

/** One line of the pane or of /router check's text, with how the pane paints it. */
type Line = { text: string; color?: string; bold?: boolean; dim?: boolean; wrap?: boolean }
const line = (text: string, style: Omit<Line, 'text'> = {}): Line => ({ text, ...style })
const BLANK = line('')

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

/** The pane's body and /router check's text. `full` (the text, or the pane with Details on) adds the long
 * sections; the pane's default is a glance: checkout, spend, families, to check, one line per suggestion. */
const summaryLines = (s: StatusJson, at: number, seen: Routed[] = [], where = '', full = true): Line[] => {
  const g = s.repo
  const sync = !g.is_repo
    ? 'not a git checkout'
    : [g.dirty ? `${g.dirty} dirty` : 'clean',
       g.behind ? `${g.behind} behind` : g.behind === 0 ? (g.fetched ? 'up to date' : 'up to date at last fetch') : 'origin unknown',
       g.ahead ? `${g.ahead} ahead` : '']
        .filter(Boolean).join(', ')
  const reg = s.ledger.regress_last
  const u = s.usage
  const total = u ? u.main_total + u.subagents_total : 0
  const lines: Line[] = full
    ? [line(`read ${clock(at)} · ${s.platform} · Claude Code ${s.claude ?? 'not found'} · routing v${s.routing.version}, decided ${s.routing.decided}`, { dim: true }),
       line(`repo ${g.head ?? '-'} · ${sync}${where ? ' · ' + where : ''}`, { dim: true })]
    : [line(`read ${clock(at)} · Claude Code ${s.claude ?? 'not found'} · routing v${s.routing.version} · repo ${g.head ?? '-'} ${sync}${where ? ' · ' + where : ''}`, { dim: true })]
  if (u) {
    const prev = u.previous.main_total + u.previous.subagents_total
    const daily = u.daily ?? []
    lines.push(line(`spend ${u.days}d ${daily.length ? spark(daily.map(d => d.cost)) + ' ' : ''}${money(total)} (main ${money(u.main_total)}, agents ${money(u.subagents_total)}) · prev ${money(prev)}`, { bold: true }))
  }
  // The triple check after a change: projected (the benchmark), realized (your transcripts since), regress (the family here).
  const r = s.changes?.realized
  if (r) {
    const checks = r.classes.filter(c => c.family && c.check).map(c => `${c.family} ${c.check!.verdict}`)
    const span = r.span ? `, ${r.span}${r.until ? ' until the next change' : ' so far'}` : r.days ? `, ${r.days} days` : ''
    lines.push(line(`since ${when(r.since)} (${r.kind}: ${r.what})${span}: ${saidSaved(r.saved)}${caveats(r)}${r.projected != null ? ` · projected ${money(r.projected)} per ${u?.days ?? 30}d` : ''}${checks.length ? ` · regress ${checks.join(', ')}` : ''}`,
      { color: caveats(r) ? undefined : savedColor(r.saved), bold: true, wrap: true }))
  } else if (full) {
    lines.push(line('no change recorded yet: Apply agents (when it changes a file), /router routing auto and /router mark <note> start the before/after count', { dim: true }))
  }
  lines.push(BLANK, line(`${'family'.padEnd(13)}${'default'.padEnd(19)}${'ok'.padEnd(11)}${'evidence'.padEnd(9)}${'$/ok'.padEnd(8)}${'here'.padEnd(5)}last check`, { bold: true }))
  for (const f of s.families) {
    const d = f.model ? `${f.model} ${f.effort}${f.variant ? ' +' + f.variant : ''}` : 'none'
    const lc = f.last_check
    const last = lc ? (lc.sample ? `${lc.verdict} ${lc.successes}/${lc.sample}` : lc.verdict) : '-'
    const cost = f.cost_per_success === null ? '-' : f.cost_per_success.toFixed(4)
    const fr = rateFrac(f.rate)
    lines.push(line(`${f.name.padEnd(13)}${d.padEnd(19)}${fr === null ? '-'.padEnd(10) : bar(fr)} ${(f.rate ?? '-').padEnd(9)}${cost.padEnd(8)}${(f.can_run ? 'yes' : 'no').padEnd(5)}${last}`,
      { color: rateColor(fr), dim: fr === null }))
  }
  const present = s.agents.routed.filter(r => r.state !== 'absent')
  const applied = present.filter(r => r.state === 'applied').length
  const absent = s.agents.routed.length - present.length
  if (full) {
    lines.push(
      BLANK,
      line(`agents: ${s.agents.files} files, ${s.agents.unused} unused; routed ${applied}/${present.length} applied${absent ? `, ${absent} not on this machine` : ''}`, { dim: true }),
      line(`prices verified ${s.catalog.verified_oldest ?? '?'} (${s.catalog.age_days ?? '?'} days) · ledger: usage ${s.ledger.usage_last ?? 'none'}, regress ${reg?.date ?? 'none'} on ${reg?.claude ?? '-'}`, { dim: true }),
      line(`timer: ${s.timer.next ? 'next ' + s.timer.next : s.timer.note ?? 'none'}`, { dim: true }),
    )
  }
  lines.push(BLANK)
  const GLANCE = 3   // items a section shows before Details
  const more = (n: number) => line(`  … ${n} more (Details)`, { dim: true })
  if (s.advice.length === 0) lines.push(line('nothing to check', { color: 'green', bold: true }))
  else {
    const shown = full ? s.advice : s.advice.slice(0, GLANCE)
    lines.push(line('to check:', { bold: true }), ...shown.map(a => line(`  - ${a}`, { color: 'yellow', wrap: true })))
    if (shown.length < s.advice.length) lines.push(more(s.advice.length - shown.length))
  }
  if (u && full) {
    lines.push(BLANK, line(`consumption, last ${u.days} days since ${u.since} (catalog $ = headroom on a subscription): main ${money(u.main_total)} (output ${money(u.main_out_cost)}) · subagents ${money(u.subagents_total)} in ${u.subagent_calls} calls`, { bold: true }))
    const top = Math.max(0, ...u.main_rows.map(r => r.cost), ...Object.values(u.by_class).map(b => b.cost))
    for (const r of u.main_rows.slice(0, 6)) {
      lines.push(line(`  ${r.model.padEnd(30)}${r.effort.padEnd(8)}${bar(top > 0 ? r.cost / top : 0, 20)} ${money(r.cost).padStart(5)}  ${String(r.msgs).padStart(5)} msgs`))
    }
    if (u.main_rows.some(r => r.effort === '?')) lines.push(line('  effort ? = not recorded in the transcript: the default effort of the session at the time', { dim: true }))
    for (const [cls, b] of Object.entries(u.by_class).sort((a, b) => b[1].cost - a[1].cost)) {
      const types = Object.entries(b.types).sort((a, b) => b[1] - a[1])
      const shown = types.slice(0, 3).map(([t, n]) => `${t} x${n}`).join(', ') + (types.length > 3 ? ` +${types.length - 3} more` : '')
      lines.push(line(`  ${('agents ' + cls).padEnd(30)}${''.padEnd(8)}${bar(top > 0 ? b.cost / top : 0, 20)} ${money(b.cost).padStart(5)}  ${String(b.n).padStart(5)} calls${b.last ? `  last ${b.last.slice(0, 10)}` : ''}`))
      lines.push(line(`${''.padEnd(40)}${shown}`, { dim: true }))
    }
  }
  if (r && full) {
    lines.push(BLANK, line(`since the change: cost per unit of the same work before vs after, times the units after (the regress column: the family still passes here)`, { bold: true }))
    const side = (x: RealizedSide) => `${x.n} calls${x.per_call === null ? '' : ` ${fine(x.per_call)}/call`} (${Object.entries(x.models).map(([m, n]) => `${m.replace(/^claude-/, '')} x${n}`).join(', ')})`
    for (const c of r.classes) {
      const check = c.family ? ` · ${c.family} regress ${c.check ? c.check.verdict + (c.check.sample ? ` ${c.check.successes}/${c.check.sample}` : '') : 'not checked here'}` : ' · no family measures this'
      lines.push(line(`  ${c.class.padEnd(19)}before ${side(c.before)} · after ${side(c.after)} · ${saidSaved(c.saved)}${check}`, { color: savedColor(c.saved) }))
    }
    const ms = (x: RealizedMainSide | { msgs: number; per_msg: number }) => `${x.msgs} msgs${x.per_msg === null ? '' : ` ${fine(x.per_msg)}/msg`}`
    lines.push(line(`  ${'main sessions'.padEnd(19)}before ${ms(r.main.before)} · after ${ms(r.main.after)} · ${saidSaved(r.main.saved)} (same unit, a message; the mix of work may differ)`, { color: savedColor(r.main.saved) }))
    for (const row of r.main.rows.slice(0, 4)) {
      lines.push(line(`    ${row.model.replace(/^claude-/, '')} ${row.effort}: ${row.before ? ms(row.before) : '-'} -> ${row.after ? ms(row.after) : '-'}`, { dim: true }))
    }
    const earlier = (s.changes?.history ?? []).slice(1, 6)
    if (earlier.length) {
      lines.push(line('  earlier changes, each measured in its own window (from the change to the next one):', { dim: true }))
      for (const h of earlier) {
        lines.push(line(`    ${when(h.since)} (${h.kind}: ${h.what})${h.span ? ` · ${h.span}` : ''}: ${saidSaved(h.saved)}${caveats(h)}${h.projected != null ? ` · projected ${money(h.projected)}` : ''}`, { color: caveats(h) ? undefined : savedColor(h.saved), wrap: true }))
      }
    }
  }
  // Suggestions: largest saving first, unknown last; each with its share of the window's spend.
  // Largest saving first; a learned suggestion ranks by what the struggling calls cost; unknown last.
  const rank = (g: { saving: [number, number] | null; kind: string; stake: number }) => g.saving?.[1] ?? (g.kind === 'learned' ? g.stake : -1)
  const sug = [...(s.suggestions ?? [])].sort((a, b) => rank(b) - rank(a))
  const upTo = savingsUpTo(s)
  lines.push(BLANK, line(sug.length === 0 ? 'suggestions: none from the last window'
    : `suggestions: up to ${money(upTo)} of ${money(total)} in ${u?.days ?? 30} days${total > 0 ? ` (${Math.round((upTo / total) * 100)}%)` : ''}${full ? '; the kind says how far the evidence reaches' : ''}`, { bold: true }))
  const shownSug = full ? sug : sug.slice(0, GLANCE)
  for (const g of shownSug) {
    const sv = g.saving === null ? 'unknown' : g.saving[0] === g.saving[1] ? `saves ${money(g.saving[0])}` : `saves ${money(g.saving[0])}-${money(g.saving[1])}`
    const share = g.saving && total > 0 ? g.saving[1] / total : 0
    lines.push(line(`${sv.padEnd(16)}${bar(share)} ${String(Math.round(share * 100)).padStart(2)}%  [${g.kind}] ${g.title}`, { color: KIND_COLOR[g.kind] }))
    if (full) lines.push(line(`    basis: ${g.basis}`, { dim: true }), line(`    do: ${g.action}`, { dim: true }))
  }
  if (shownSug.length < sug.length) lines.push(more(sug.length - shownSug.length))
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
      lines.push(line(`  ${sx.project}: ${sx.sessions} session${sx.sessions === 1 ? '' : 's'}, ${sx.msgs} msgs, ${sx.errors} tool errors, ${sx.compactions} context boundaries (${sx.per_session} per session)`, { dim: true }))
    }
    lines.push(line(mine.length ? `  this project's overrides: ${mine.map(([c, o]) => `${c} -> ${o.model} ${o.effort}`).join(', ')} (/router prefer clear <class>)` : '  this project: no override (/router prefer <class> <model> <effort> sets one)', { dim: true }))
  }
  if (seen.length > 0) {
    const kept = seen.filter(r => r.decision === 'kept').length
    lines.push(BLANK, line(`routed this session: ${seen.length - kept} routed, ${kept} kept (mode ${routingMode}; /router routing ask|auto|off${full ? '' : '; Details lists them'})`, { bold: true }))
    if (full) for (const r of seen.slice(-8)) lines.push(line(`  ${clock(r.at)}  ${r.agent}: ${r.from} -> ${r.to}  [${r.family}] ${r.decision}  ${r.description}`, { dim: r.decision === 'kept' }))
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
let routingMode: RoutingMode = 'ask'
let statusMode: StatusMode = 'full'
let struggleOption = 25
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
  throw new Error('no Python 3 on PATH: set "Python command" in /config (model-router)')
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
    $.ui.status(statusMode === 'off' ? undefined : statusLine(json, rateLimits, (await read($, routed)).length, statusMode))
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

async function runJob($: Dollar, name: string) {
  const spec = JOBS[name]
  if (!spec) return false
  const current = await read($, job)
  if (current?.isRunning) {
    $.ui.toast(`model-router: ${current.name} is still running`)
    return false
  }
  let argv: string[]
  try {
    argv = spec.argv(await findPython($), where !== '')
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
  statusMode = sm === 'minimal' || sm === 'off' ? sm : 'full'
  struggleOption = Math.max(5, Math.min(95, Number(options.struggle ?? 25) || 25))
  repo = repoOption
  python = ''

  on('session.start', async ($, e, next) => {
    projectKey = keyOf(e.cwd)
    await $.command.register({
      name: 'router',
      description: 'Model router: where the routing stands, re-check it, ledger, apply, pull',
      argumentHint: 'open | check | fetch | update | ledger | apply | pull | routing ask|auto|off | mark <note> | prefer <class> <model> <effort> | prefer clear <class>',
    })
    void refresh($)
    if (refreshMinutes > 0) {
      $.clock.every(Math.max(1, refreshMinutes) * 60000, () => {
        void refresh($)
      })
    }
    return next(e)
  })

  on('command.run', { command: 'router' }, async ($, e) => {
    // No argument is 'open': an empty string splits to [''], which would miss the default.
    const [verb = 'open', arg = ''] = e.args.trim().split(/\s+/).filter(Boolean)
    if (verb === 'open') {
      const opened = await $.ui.open({ id: PANE, title: 'Model router' })
      void refresh($)
      return { text: opened.isPlaced ? 'Model router pane opened.' : `The pane waits for room: ${opened.reason}` }
    }
    if (verb === 'check' || verb === 'fetch') {
      await refresh($, verb === 'fetch')
      const s = await read($, status)
      return { text: s?.json ? summaryLines(s.json, s.at, await read($, routed), s.where).map(l => l.text).join('\n') : (s?.error ?? 'no status') }
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
        await $.process.run([py, 'tools/overrides.py', 'clear', projectKey, words[1]], { cwd: repo, env: pyEnv(), timeoutMs: 20000 })
        await recordChange($, 'override', `cleared ${words[1]} in ${projectKey}`)
        return { text: `override cleared: ${words[1]} in this project; the family default applies again.` }
      }
      const [cls, mdl, eff] = words
      if (!cls || !mdl || !eff || !MODELS.has(mdl) || !EFFORTS.has(eff)) return { text: 'prefer needs <class> <model> <effort>, e.g. /router prefer research-synthesis opus low (models haiku|sonnet|opus|fable; efforts low|medium|high|xhigh|max)' }
      const r = await $.process.run([py, 'tools/overrides.py', 'set', projectKey, cls, mdl, eff, '--why', 'set from the pane'], { cwd: repo, env: pyEnv(), timeoutMs: 20000 })
      if (r.exitCode !== 0) return { text: `could not set the override: ${r.stderr.trim().split('\n').pop() ?? ''}` }
      await recordChange($, 'override', `${cls} -> ${mdl} ${eff} in ${projectKey}`)
      return { text: `override set for this project: ${cls} calls run on ${mdl} ${eff} (ask or auto mode). The pane counts the saving from now; /router prefer clear ${cls} undoes it.` }
    }
    if (verb === 'mark') {
      const note = e.args.trim().replace(/^mark\s*/, '')
      if (!note) return { text: 'mark needs a note of what you changed, e.g. /router mark effort low from today' }
      await recordChange($, 'mark', note)
      return { text: `change recorded: ${note}. The pane counts what the transcripts save from now.` }
    }
    if (verb === 'routing') {
      if (arg === 'ask' || arg === 'auto' || arg === 'off') {
        const was = routingMode
        routingMode = arg
        if (arg === 'auto' && was !== 'auto') void recordChange($, 'routing', 'auto for this session', measuredProjected((await read($, status))?.json))
      }
      return { text: `routing ${routingMode} for this session${arg ? '' : ' (routing ask|auto|off sets it)'}; /config makes it permanent.` }
    }
    const spec = JOBS[verb]
    if (spec) {
      await $.ui.open({ id: PANE, title: 'Model router' })
      const started = await runJob($, verb)
      return { text: started ? `${spec.title} started; the pane shows its output.` : 'Not started.' }
    }
    return { text: 'Usage: /router [open | check | fetch | update | ledger | apply | pull | routing ask|auto|off]' }
  })

  // Every Agent call: when a measured family covers the task and the call asks for something dearer than
  // the family's decision, rewrite it (auto), ask (ask), or leave it (off). Nothing unmeasured is touched.
  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    if (routingMode === 'off') return next(e)
    const s = await read($, status)
    const agent = e.subagent_type ?? 'general-purpose'
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
    if (decision === 'kept') return next(e)
    $.ui.toast(`router: ${agent} on ${c.model} ${c.effort} (${c.family} ${c.rate})`)
    return next({
      ...e,
      model: c.model as 'sonnet' | 'opus' | 'haiku' | 'fable',
      effort: c.effort as 'low' | 'medium' | 'high' | 'xhigh' | 'max',
      ...(c.family === 'repo_fix' ? { prompt: e.prompt + RUNNER_NOTE } : {}),
    })
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const s = await read($, status)
    const j = await read($, job)
    const busy = j?.isRunning === true
    const full = await read($, details)
    const limits = s?.rateLimits ?? []
    // While a job runs the pane is the job: its output, nothing else; the summary returns when it ends.
    const body: Line[] = busy && j
      ? [line(`running ${j.name} since ${clock(j.startedAt)} · the summary returns when it ends`, { bold: true })]
      : [
          ...limitLines(limits),
          ...(s?.json ? summaryLines(s.json, s.at, await read($, routed), s.where, full) : [line(s?.error ?? 'reading the checkout…', { color: s?.error ? 'yellow' : undefined, wrap: true })]),
        ]
    const rows = Math.max(12, (e.viewport?.rows ?? 40) - 2)
    // One line stays one line: cut to the pane's width instead of wrapping (/router check keeps the full text).
    const width = Math.max(40, (e.viewport?.columns ?? 100) - 1)
    const cut = (t: string) => (t.length > width ? t.slice(0, width - 1) + '…' : t)
    const logRoom = Math.max(3, rows - body.length - 3)
    // A job that ended well keeps one line; its whole output stays under Details, and a failure shows it all.
    const log = j ? (busy || j.exitCode !== 0 || full ? j.lines.slice(-logRoom) : j.lines.slice(-1)) : []
    return (
      <Box flexDirection="column">
        <Box flexDirection="row" gap={1} flexWrap="wrap">
          <Button key="refresh" hotkey="r" onPress={() => { void refresh($) }}>Refresh</Button>
          <Button key="fetch" hotkey="f" onPress={() => { void refresh($, true) }}>Fetch origin</Button>
          <Button key="update" hotkey="u" variant="primary" dimColor={busy} onPress={() => { void runJob($, 'update') }}>Re-check routing</Button>
          <Button key="details" hotkey="d" onPress={() => { void update($, details, v => !v) }}>{full ? 'Less' : 'Details'}</Button>
        </Box>
        <Box flexDirection="row" gap={1} flexWrap="wrap">
          <Button key="ledger" hotkey="l" dimColor={busy} onPress={() => { void runJob($, 'ledger') }}>Ledger now</Button>
          <Button key="apply" hotkey="a" dimColor={busy} onPress={() => { void runJob($, 'apply') }}>Apply agents</Button>
          <Button key="pull" hotkey="p" dimColor={busy} onPress={() => { void runJob($, 'pull') }}>Pull</Button>
        </Box>
        {body.map(l => (
          <Text color={l.color} weight={l.bold ? 'bold' : undefined} dimColor={l.dim}>
            {l.text === '' ? ' ' : l.wrap ? l.text : cut(l.text)}
          </Text>
        ))}
        {j && (
          <Text weight="bold">
            {busy ? 'running' : 'last job'}: {j.name}
            {j.exitCode === null ? '' : ` (exit ${j.exitCode})`}
          </Text>
        )}
        {log.map(line => (
          <Text dimColor>{line === '' ? ' ' : cut(line)}</Text>
        ))}
      </Box>
    )
  })
}
