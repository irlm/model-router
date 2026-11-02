import { atom, read, update } from 'claude-code'
import type { Hook, Register } from 'claude-code'

import type { Job, RateLimit, Status, StatusJson } from '../types'

type Dollar = Parameters<Hook<'session.start'>>[0]

const PANE = 'model-router'
// status-2: the rate-limit windows and the consumption block joined the value
const status = atom({ plugin: 'model-router', key: 'status' } as const, null, { shape: 'status-2' })
const job = atom({ plugin: 'model-router', key: 'job' } as const, null, { shape: 'job-1' })

// What the buttons and /router <verb> run, from the checkout's root.
const JOBS: Record<string, { title: string; argv: (python: string) => string[] }> = {
  update: { title: 'regression check', argv: py => [py, 'tools/update.py', '--sample', '6'] },
  ledger: { title: 'usage ledger', argv: py => [py, 'tools/ledger.py', '--commit'] },
  apply: { title: 'apply agents', argv: py => [py, 'apply_agents.py'] },
  pull: { title: 'git pull', argv: () => ['git', 'pull', '--ff-only'] },
}

// Python reads and writes UTF-8 everywhere (transcripts, ledger, git output), also on Windows,
// where its default is the console code page.
const PY_ENV = { PYTHONUTF8: '1' }

const clock = (ms: number) => {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const windowName = (kind: string) => (kind === 'five_hour' ? '5h' : kind === 'seven_day' ? '7d' : kind)

const limitsText = (limits: RateLimit[]) => limits.map(l => `${windowName(l.kind)} ${Math.round(l.percentUsed)}%`).join(' · ')

/** The status line under the prompt: the rate-limit windows, then what is worth doing. */
const statusLine = (s: StatusJson, limits: RateLimit[], at: number) => {
  const parts = [limitsText(limits)]
  const n = s.suggestions?.length ?? 0
  if (s.advice.length > 0) parts.push(`${s.advice.length} to check`)
  if (n > 0) parts.push(`${n} suggestion${n > 1 ? 's' : ''}`)
  if (s.advice.length === 0 && n === 0) parts.push(`router ok · v${s.routing.version}`)
  return `router: ${parts.filter(Boolean).join(' · ')} · /router · ${clock(at)}`
}

/** The pane's body and /router check's text: the same lines. */
const summaryLines = (s: StatusJson, at: number): string[] => {
  const g = s.repo
  const sync = !g.is_repo
    ? 'not a git checkout'
    : [g.dirty ? `${g.dirty} dirty` : 'clean',
       g.behind ? `${g.behind} behind` : g.behind === 0 ? (g.fetched ? 'up to date' : 'up to date at last fetch') : 'origin unknown',
       g.ahead ? `${g.ahead} ahead` : '']
        .filter(Boolean).join(', ')
  const reg = s.ledger.regress_last
  const lines = [
    `read ${clock(at)} · ${s.platform} · Claude Code ${s.claude ?? 'not found'} · repo ${g.head ?? '-'} (${sync})`,
    `routing v${s.routing.version}, decided ${s.routing.decided}`,
    '',
    `${'family'.padEnd(13)}${'default'.padEnd(19)}${'evidence'.padEnd(9)}${'$/ok'.padEnd(8)}${'here'.padEnd(5)}last check`,
  ]
  for (const f of s.families) {
    const d = f.model ? `${f.model} ${f.effort}${f.variant ? ' +' + f.variant : ''}` : 'none'
    const lc = f.last_check
    const last = lc ? (lc.sample ? `${lc.verdict} ${lc.successes}/${lc.sample}` : lc.verdict) : '-'
    const cost = f.cost_per_success === null ? '-' : f.cost_per_success.toFixed(4)
    lines.push(`${f.name.padEnd(13)}${d.padEnd(19)}${(f.rate ?? '-').padEnd(9)}${cost.padEnd(8)}${(f.can_run ? 'yes' : 'no').padEnd(5)}${last}`)
  }
  const applied = s.agents.routed.filter(r => r.state === 'applied').length
  lines.push(
    '',
    `agents: ${s.agents.files} files, ${s.agents.unused} unused; routed ${applied}/${s.agents.routed.length} applied`,
    `prices verified ${s.catalog.verified_oldest ?? '?'} (${s.catalog.age_days ?? '?'} days) · ledger: usage ${s.ledger.usage_last ?? 'none'}, regress ${reg?.date ?? 'none'} on ${reg?.claude ?? '-'}`,
    `timer: ${s.timer.next ? 'next ' + s.timer.next : s.timer.note ?? 'none'}`,
    '',
  )
  if (s.advice.length === 0) lines.push('nothing to do')
  else lines.push('to check:', ...s.advice.map(a => `  - ${a}`))
  const u = s.usage
  if (u) {
    lines.push(
      '',
      `consumption, last ${u.days} days since ${u.since} (catalog $ = headroom on a subscription):`,
      `  main sessions $${u.main_total.toFixed(0)} (output $${u.main_out_cost.toFixed(0)}) · subagents $${u.subagents_total.toFixed(0)} in ${u.subagent_calls} calls · previous ${u.days} days: main $${u.previous.main_total.toFixed(0)}, subagents $${u.previous.subagents_total.toFixed(0)}`,
    )
    for (const r of u.main_rows.slice(0, 6)) {
      lines.push(`  ${r.model.padEnd(30)}${r.effort.padEnd(8)}${String(r.msgs).padStart(5)} msgs  $${r.cost.toFixed(2).padStart(7)}`)
    }
    for (const [cls, b] of Object.entries(u.by_class).sort((a, b) => b[1].cost - a[1].cost)) {
      const types = Object.entries(b.types).map(([t, n]) => `${t} x${n}`).join(', ')
      lines.push(`  subagents ${cls.padEnd(20)}${String(b.n).padStart(4)} calls  $${b.cost.toFixed(2).padStart(7)}  ${types}`)
    }
  }
  const sug = s.suggestions ?? []
  lines.push('', sug.length === 0 ? 'suggestions: none from the last window' : 'suggestions (catalog $ per window; the kind says how far the evidence reaches):')
  for (const g of sug) {
    const sv = g.saving === null ? 'saving unknown' : g.saving[0] === g.saving[1] ? `saves $${g.saving[0].toFixed(0)}` : `saves $${g.saving[0].toFixed(0)}-${g.saving[1].toFixed(0)}`
    lines.push(`* [${g.kind}] ${g.title}: ${sv}`, `    basis: ${g.basis}`, `    do: ${g.action}`)
  }
  return lines
}

// Set by register() from the mod's options; module variables start over on a reload, as register runs again.
let repoOption = '~/Projects/Github/model-router'
let pythonOption = ''
let refreshMinutes = 30
let repo = repoOption
let python = ''

async function resolveRepo($: Dollar) {
  const home = (await $.env.get('HOME')) || (await $.env.get('USERPROFILE')) || ''
  repo = repoOption.replace(/^~(?=$|[\\/])/, home)
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
    if (!(await $.fs.exists(`${repo}/routing.json`))) {
      throw new Error(`no model-router checkout at ${repo}: clone it there or set the path in /config`)
    }
    const py = await findPython($)
    const argv = [py, 'tools/status.py', '--json', ...(fetch ? ['--fetch'] : [])]
    const r = await $.process.run(argv, { cwd: repo, env: PY_ENV, timeoutMs: 180000 })
    if (r.exitCode !== 0) throw new Error(`status.py exit ${r.exitCode}: ${r.stderr.trim().split('\n').pop() ?? ''}`)
    const json = JSON.parse(r.stdout) as StatusJson
    const rateLimits = await readLimits($)
    await update($, status, () => ({ at, json, error: null, rateLimits }))
    $.ui.status(statusLine(json, rateLimits, at))
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    const rateLimits = await readLimits($)
    await update($, status, () => ({ at, json: null, error, rateLimits }))
    $.ui.status(`router: ${error}`)
  }
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
    argv = spec.argv(await findPython($))
  } catch (err) {
    $.ui.toast(err instanceof Error ? err.message : String(err))
    return false
  }
  const startedAt = await $.clock.now()
  await update($, job, () => ({ name: spec.title, lines: [`$ ${argv.join(' ')}`], isRunning: true, exitCode: null, startedAt }))
  // The child outlives this dispatch: its loop runs on and ends with the child.
  void (async () => {
    let code: number | null = null
    let rest = ''
    const append = (text: string) =>
      update($, job, j => (j ? { ...j, lines: [...j.lines, ...text.split('\n')].slice(-400) } : j))
    try {
      const child = $.process.spawn({ argv, cwd: repo, env: PY_ENV })
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

export const register: Register = (on, options) => {
  repoOption = String(options.repo || '~/Projects/Github/model-router')
  pythonOption = String(options.python || '')
  refreshMinutes = Number(options.refreshMinutes ?? 30)
  repo = repoOption
  python = ''

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'router',
      description: 'Model router: where the routing stands, re-check it, ledger, apply, pull',
      argumentHint: 'open | check | fetch | update | ledger | apply | pull',
    })
    await resolveRepo($)
    void refresh($)
    if (refreshMinutes > 0) {
      $.clock.every(Math.max(1, refreshMinutes) * 60000, () => {
        void refresh($)
      })
    }
    return next(e)
  })

  on('command.run', { command: 'router' }, async ($, e) => {
    const verb = e.args.trim().split(/\s+/)[0] || 'open'
    if (verb === 'open') {
      const opened = await $.ui.open({ id: PANE, title: 'Model router' })
      void refresh($)
      return { text: opened.isPlaced ? 'Model router pane opened.' : `The pane waits for room: ${opened.reason}` }
    }
    if (verb === 'check' || verb === 'fetch') {
      await refresh($, verb === 'fetch')
      const s = await read($, status)
      return { text: s?.json ? summaryLines(s.json, s.at).join('\n') : (s?.error ?? 'no status') }
    }
    const spec = JOBS[verb]
    if (spec) {
      await $.ui.open({ id: PANE, title: 'Model router' })
      const started = await runJob($, verb)
      return { text: started ? `${spec.title} started; the pane shows its output.` : 'Not started.' }
    }
    return { text: 'Usage: /router [open | check | fetch | update | ledger | apply | pull]' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const s = await read($, status)
    const j = await read($, job)
    const busy = j?.isRunning === true
    const limits = s?.rateLimits ?? []
    const body = [
      ...(limits.length ? [`rate limits: ${limits.map(l => `${windowName(l.kind)} ${l.percentUsed}% used${l.resetsAt ? ', resets ' + clock(Date.parse(l.resetsAt)) : ''}`).join(' · ')}`] : []),
      ...(s?.json ? summaryLines(s.json, s.at) : [s?.error ?? 'reading the checkout…']),
    ]
    const rows = Math.max(12, (e.viewport?.rows ?? 40) - 2)
    const logRoom = Math.max(3, rows - body.length - 3)
    const log = j ? j.lines.slice(-logRoom) : []
    return (
      <Box flexDirection="column">
        <Box flexDirection="row" gap={1} flexWrap="wrap">
          <Button key="refresh" hotkey="r" onPress={() => { void refresh($) }}>Refresh</Button>
          <Button key="fetch" hotkey="f" onPress={() => { void refresh($, true) }}>Fetch origin</Button>
          <Button key="update" hotkey="u" variant="primary" dimColor={busy} onPress={() => { void runJob($, 'update') }}>Re-check routing</Button>
          <Button key="ledger" hotkey="l" dimColor={busy} onPress={() => { void runJob($, 'ledger') }}>Ledger now</Button>
          <Button key="apply" hotkey="a" dimColor={busy} onPress={() => { void runJob($, 'apply') }}>Apply agents</Button>
          <Button key="pull" hotkey="p" dimColor={busy} onPress={() => { void runJob($, 'pull') }}>Pull</Button>
        </Box>
        {body.map(line => (
          <Text
            color={line.startsWith('  - ') ? 'yellow' : line.startsWith('* [measured]') ? 'green' : line.startsWith('* [') ? 'cyan' : undefined}
            weight={line.startsWith('* [') || line.startsWith('rate limits:') ? 'bold' : undefined}
            dimColor={line === '' || line.startsWith('    basis:')}
          >
            {line === '' ? ' ' : line}
          </Text>
        ))}
        {j && (
          <Text weight="bold">
            {busy ? 'running' : 'last job'}: {j.name}
            {j.exitCode === null ? '' : ` (exit ${j.exitCode})`}
          </Text>
        )}
        {log.map(line => (
          <Text dimColor>{line === '' ? ' ' : line}</Text>
        ))}
      </Box>
    )
  })
}
