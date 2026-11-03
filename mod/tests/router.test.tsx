import { expect, mock, test } from 'claude-code/testing'

const STATUS = {
  at: '2026-11-01T12:00', platform: 'Linux', claude: '2.1.316',
  repo: { is_repo: true, head: 'abc1234', dirty: 0, ahead: 0, behind: 0, fetched: false },
  routing: { version: 1.1, decided: '2026-11-01' },
  families: [
    { name: 'find_feature', model: 'haiku', effort: 'low', variant: '', rate: '214/216', cost_per_success: 0.0046, can_run: true, why: '',
      last_check: { sample: '6', successes: '6', verdict: 'ok' } },
    { name: 'fix_bug', model: 'haiku', effort: 'low', variant: 'kunit', rate: '16/21', cost_per_success: 0.0158, can_run: false,
      why: 'needs a kernel worktree', last_check: null },
  ],
  agents: { files: 6, unused: 179, routed: [{ file: 'web-researcher.md', name: 'Web Researcher', want: 'haiku low', have: 'haiku low', state: 'applied' },
    { file: 'testing-evidence-collector.md', want: 'haiku low', have: null, state: 'absent' }] },
  catalog: { verified_oldest: '2026-10-06', age_days: 26 },
  ledger: { usage_last: '2026-11-01', regress_last: { date: '2026-11-01', claude: '2.1.316' } },
  timer: { kind: 'systemd', installed: true, next: 'Tue 2026-12-01 09:00:00 EST' },
  advice: ['prices verified 40 days ago: check the sources'],
  usage: { days: 30, since: '2026-10-02', main_total: 517.2, main_out_cost: 133.1,
    main_rows: [{ model: 'claude-opus-5-5', effort: 'medium', msgs: 2152, cost: 258.86, out_cost: 53.1 }],
    subagents_total: 74.75, subagent_calls: 20, by_class: { 'research-synthesis': { n: 19, cost: 73.12, types: { 'general-purpose': 19 } } },
    previous: { since: '2026-09-02', main_total: 491.9, subagents_total: 7.8 },
    daily: [{ date: '2026-10-28', cost: 1 }, { date: '2026-10-29', cost: 2 }, { date: '2026-10-30', cost: 4 }, { date: '2026-10-31', cost: 6 }, { date: '2026-11-01', cost: 8 }] },
  suggestions: [{ id: 'effort', kind: 'extrapolated', title: 'main sessions at high/xhigh effort: $225 in 30 days', stake: 225,
    saving: [72, 72], basis: 'results/cell8 sweep', action: 'claude --effort low' }],
  changes: { events: [{ at: '2026-10-30T10:00Z', kind: 'apply', detail: 'agents: web-researcher.md', projected: 25 }],
    history: [{ since: '2026-10-30T10:00Z', until: null, span: '2.0 days', kind: 'apply', what: 'agents: web-researcher.md', projected: 25, days: 2, classes: [],
      main: { before: { msgs: 1, cost: 1, per_msg: 1 }, after: { msgs: 1, cost: 1, per_msg: 1 }, saved: 0, rows: [] }, saved: 12.59 },
      { since: '2026-10-28T09:00Z', until: '2026-10-30T10:00Z', span: '2.0 days', kind: 'mark', what: 'effort low', projected: null, days: 4, classes: [],
      main: { before: { msgs: 100, cost: 12, per_msg: 0.12 }, after: { msgs: 100, cost: 13.2, per_msg: 0.132 }, saved: -1.2,
        rows: [{ model: 'claude-fable-5-1', effort: 'xhigh', before: { msgs: 100, per_msg: 0.12 }, after: { msgs: 100, per_msg: 0.132 } }] }, saved: -1.2 }],
    realized: { since: '2026-10-30T10:00Z', until: null, span: '2.0 days', kind: 'apply', what: 'agents: web-researcher.md', projected: 25, days: 2,
      classes: [{ class: 'code-explore', family: 'find_feature', saved: 7.69, check: { sample: '6', successes: '6', verdict: 'ok' },
        same_work: true, ref_model: 'claude-opus-5-5',
        before: { n: 16, cost: 24.71, per_call: 1.544, per_mtok: 13.08, tok_per_call: 118000, models: { 'claude-opus-5-5': 16 } }, after: { n: 5, cost: 0.03, per_call: 0.006, per_mtok: 0.063, tok_per_call: 95000, models: { 'claude-haiku-5-5': 5 } } }],
      main: { before: { msgs: 2000, cost: 234, per_msg: 0.117, tok_per_msg: 12000 }, after: { msgs: 140, cost: 11.48, per_msg: 0.082, tok_per_msg: 15000 }, saved: 4.9, same_work: true, rows: [] }, saved: 12.59 } },
}

const PANE = {
  plugin: 'model-router',
  component: 'Pane',
  requestId: 'model-router',
  props: { title: 'Model router', isFocused: false, bodyColumns: 100, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} },
} as const

const ok = { exitCode: 0, stderr: '', isStdoutTruncated: false, isStderrTruncated: false }
const RUN = { origin: { kind: 'composer' }, presentation: { isFullscreen: false, columns: 120 } } as const

test('/router check prints the table and the status line counts the advice', async ($, on) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  const argvs: string[] = []
  on('process.run', (_, e) => {
    argvs.push(e.argv.join(' '))
    return { value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(STATUS) } }
  })
  const pinned: (string | undefined)[] = []
  on('ui.status', (_, e) => { pinned.push(e.text); return { value: undefined } })
  on('ui.open', () => ({ value: { isPlaced: true } }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('find_feature haiku low          ██████████ 214/216  0.0046  yes  ok 6/6')
  expect(text).toContain('spend 30d ▂▃▅▆█ $592 (main $517, agents $75) · prev $500')
  expect(text).toContain('agents: 6 files, 179 unused; routed 1/1 applied, 1 not on this machine')
  expect(text).toContain('(apply: agents: web-researcher.md), 2.0 days so far: vs previous saved $13 · projected $25 per 30d · regress find_feature ok')
  expect(text).toContain('(mark: effort low) · 2.0 days: cost up $1.20 (main sessions run on the same model and effort as before, so the change is not in effect)')
  expect(text).toContain('code-explore       $/Mtok   13.08 -> 0.06    ████████ -> ▏░░░░░░░  saved $7.69    same work · 5 after · 118k -> 95k tok/call')
  expect(text).toContain('main sessions      $/Mtok    9.75 -> 5.47    ████████ -> ████░░░░  saved $4.90    same work · 140 msgs after · 12k -> 15k tok/msg')
  expect((await $.command.run({ ...RUN, command: 'router', args: 'mark effort low from today' })).text).toContain('change recorded: effort low from today')
  expect(argvs.some(a => a.endsWith('tools/changes.py add mark effort low from today'))).toBe(true)

  expect((await $.command.run({ ...RUN, command: 'router', args: '' })).text).toBe('Model router pane opened.')
  expect((await $.command.run({ ...RUN, command: 'router', args: '  ' })).text).toBe('Model router pane opened.')
  expect(text).toContain('fix_bug      haiku low +kunit   ████████░░ 16/21    0.0158  no   -')
  expect(text).toContain('  - prices verified 40 days ago')
  expect(pinned.at(-1)).toBe('saved $13 since 10-30 · up to $72 less last 30d ($0.00 measured) · 1 to check · /router')
  expect(text).toContain('suggestions (the last 30 days could have consumed up to $72 less of $592: $72 extrapolated):')
  expect(text).toContain(' 1. [extrapolated] main sessions at high/xhigh effort: $225 in 30 days')
  expect(text).toContain('est $72/30d')
  expect(text).toContain('families: 2 decided · 1 checkable here · last checks ok')
  expect((await $.command.run({ ...RUN, command: 'router', args: 'dismiss 1' })).text).toContain('dismissed effort')
  expect(argvs.some(a => a.endsWith('tools/overrides.py dismiss effort'))).toBe(true)
  expect(text).toContain('agents research-synthesis')
  expect(text).toContain('general-purpose x19')

  for (const surface of ['terminal', 'desktop', 'vscode', 'mobile'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /routing v1.1/ }))?.text).toContain('routing v1.1')
    expect(await ui.find({ type: 'Button', text: /Re-check routing/ })).toBeTruthy()
    await ui.unmount()
  }

  // The pane is a glance by default; Details adds the long sections.
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /\[extrapolated\]/ }))?.text).toContain('est $72/30d')
  expect(await ui.find({ type: 'Text', text: /^find_feature haiku low/ })).toBeUndefined()   // the table is under Details
  expect(await ui.find({ type: 'Text', text: /^routed this session/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /basis:/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /consumption, last 30 days/ })).toBeUndefined()
  await ui.press({ key: 'details' })
  expect((await ui.find({ type: 'Text', text: /basis:/ }))?.text).toContain('results/cell8 sweep')
  expect(await ui.find({ type: 'Text', text: /consumption, last 30 days/ })).toBeTruthy()
  expect(await ui.find({ type: 'Button', text: /Less/ })).toBeTruthy()
  await ui.unmount()
})

test('a missing checkout is said in the pane, not thrown', async ($, on) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: false }))
  on('fs.read', () => ({ value: '{}' }))
  on('ui.status', () => ({ value: undefined }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('no model-router checkout at /home/me/Projects/Github/model-router')

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /no model-router checkout/ }))?.text).toContain('set the path in /config')
  await ui.unmount()
})

test('no checkout at the configured path: the clone the plugin install made serves', async ($, on) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  const CLONE = '/home/me/.claude/plugins/marketplaces/model-router'
  on('fs.exists', (_, e) => ({ value: e.path.startsWith(CLONE) }))
  on('fs.read', (_, e) => ({
    value: e.path === '/home/me/.claude/plugins/known_marketplaces.json' ? JSON.stringify({ 'model-router': { installLocation: CLONE } }) : '{}',
  }))
  const runs: { argv: readonly string[]; cwd?: string }[] = []
  on('process.run', (_, e) => {
    runs.push({ argv: e.argv, cwd: e.init?.cwd })
    return { value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(STATUS) } }
  })
  on('ui.status', () => ({ value: undefined }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('repo abc1234 · clean, up to date at last fetch · marketplace clone')
  expect(runs.find(r => r.argv[1] === 'tools/status.py')?.cwd).toBe(CLONE)
})

test('auto mode routes a research note to the decided family once it is measured', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const withNotes = { ...STATUS, families: [...STATUS.families,
    { name: 'research_synthesis', model: 'sonnet', effort: 'low', variant: '', rate: '12/12', cost_per_success: 0.0935, can_run: true, why: '', last_check: null }] }
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => ({ value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(withNotes) } }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('tool.call', (_, e) => { seen.push(e as unknown as Record<string, unknown>); return { result: {} } })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call({ tool: 'Agent', description: 'compare options', prompt: 'Research and compare three message queues; write up a report.', subagent_type: 'general-purpose' })
  const call = seen.find(x => x.tool === 'Agent')
  expect([call?.model, call?.effort]).toEqual(['sonnet', 'low'])
})

test('an override for this project routes before the family default, and prefer sets one', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const argvs: string[] = []
  const withOverride = { ...STATUS, overrides: { '-': { 'code-explore': { model: 'opus', effort: 'low', since: '2026-11-03T10:00Z' } } } }
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => {
    argvs.push(e.argv.join(' '))
    return { value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: e.argv[1] === 'tools/status.py' ? JSON.stringify(withOverride) : '{}' } }
  })
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('tool.call', (_, e) => { seen.push(e as unknown as Record<string, unknown>); return { result: {} } })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  const call = seen.find(x => x.tool === 'Agent')
  expect([call?.model, call?.effort]).toEqual(['opus', 'low'])   // the family says haiku low; the project's override wins
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prefer' })).text).toContain('code-explore -> opus low')
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prefer research-synthesis opus low' })).text).toContain('override set for this project')
  expect(argvs.some(a => a.includes('tools/overrides.py set - research-synthesis opus low'))).toBe(true)
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prefer nope' })).text).toContain('prefer needs')
})

const PAST = [
  'Find where the config parser loads the yaml schema and reports validation errors with line numbers',
  'The include directive in the parser should resolve relative paths from the document root, not the cwd',
  'Write a unit test for the grammar tokenizer covering quoted strings, escapes and multiline literals',
  'Why does the loader cache stale schema versions after a reload; trace the invalidation path',
]
test('a prompt that reads as a different task in a big session gets the context question; compact is one answer', async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const compacts: unknown[] = []
  const COMPACT = 'Compact now, keeping only this task'
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => ({ value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(STATUS) } }))
  on('ui.status', () => ({ value: undefined }))
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: 240000, window: 1000000 }, rateLimits: [] } }))
  on('session.model', () => ({ value: 'claude-fable-5-1' }))
  on('session.turns', () => ({ value: 40 }))
  on('session.messages', () => ({ value: PAST.map(text => ({ role: 'user' as const, text, toolUses: [] })) }))
  on('session.compact', (_, e) => { compacts.push(e); return { skip: 'test' } })
  const toasts: string[] = []
  on('ui.toast', (_, e) => { toasts.push(e.text); return { value: undefined } })
  on('prompt.submit', (_, e) => ({ text: e.text }))
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('tool.call', (_, e) => {
    seen.push(e as unknown as Record<string, unknown>)
    if (e.tool === 'AskUserQuestion') return { result: { questions: e.questions, answers: { [e.questions[0]?.question ?? '']: COMPACT, [e.questions[0]?.header ?? '']: COMPACT } } }
    return { result: {} }
  })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const SUBMIT = { wait: false, origin: { kind: 'composer' } } as const
  await $.prompt.submit({ ...SUBMIT, text: 'Also check that the parser config loader handles the include directive the same way for the schema' })
  expect(seen.filter(x => x.tool === 'AskUserQuestion').length).toBe(0)   // the same task: no question
  const r = await $.prompt.submit({ ...SUBMIT, text: 'Now look at issue PAY-4421: the payment webhook retries fail with a timeout in the billing service' })
  // The kit returns from $.prompt.submit before the hooks have finished: yield until the answer was recorded.
  for (let i = 0; i < 60 && !toasts.some(t => t.startsWith('this turn runs')); i++) await $.command.run({ ...RUN, command: 'router', args: 'routing' })
  const asks = seen.filter(x => x.tool === 'AskUserQuestion') as { questions: { question: string }[] }[]
  expect(compacts.length).toBe(0)   // never under the prompt hook: the host refuses that
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 't1', reason: 'answer' })   // the turn ends: now the chosen compaction runs
  for (let i = 0; i < 60 && compacts.length === 0; i++) await $.command.run({ ...RUN, command: 'router', args: 'routing' })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(asks.length).toBe(1)
  expect(asks[0]?.questions[0]?.question).toContain('240k tokens every turn')
  expect(asks[0]?.questions[0]?.question).toContain('PAY-4421')
  expect(compacts.length).toBe(1)
  expect(toasts.some(t => t.startsWith('compacted'))).toBe(true)
  expect(r.text).toContain('PAY-4421')   // the prompt itself is never dropped or rewritten
  expect(text).toContain('context: 240k tokens re-read every turn ($0.06 per turn) · 1 task switch seen, 1 compacted · a new window starts at 23k')
})

type On = Parameters<NonNullable<Parameters<typeof test>[2]>>[1]
const ROUTING_MOCKS = (on: On, seen: Record<string, unknown>[], ask: 'deny' | string) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => ({
    value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(STATUS) },
  }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('tool.call', (_, e) => {
    seen.push(e as unknown as Record<string, unknown>)
    if (e.tool === 'AskUserQuestion') return ask === 'deny' ? { deny: 'no one to ask' } : { result: { questions: e.questions, answers: { [e.questions[0]?.question ?? '']: ask, [e.questions[0]?.header ?? '']: ask } } }
    return { result: {} }
  })
}

const EXPLORE = { tool: 'Agent', description: 'find the parser', prompt: 'Find where the config file is parsed and report the function.', subagent_type: 'Explore' } as const

test('auto mode runs an Explore call on haiku low, the measured find_feature default', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  ROUTING_MOCKS(on, seen, 'deny')
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  const call = seen.find(x => x.tool === 'Agent')
  expect(call?.model).toBe('haiku')
  expect(call?.effort).toBe('low')
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('routed this session: 1 routed, 0 kept (mode auto')
  expect(text).toContain('Explore: inherit -> haiku low  [find_feature] auto  find the parser')
})

test('a research report (unmeasured) and a routed agent already on haiku low are left alone', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  ROUTING_MOCKS(on, seen, 'deny')
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call({ tool: 'Agent', description: 'compare options', prompt: 'Research and compare three message queues; write up a report.', subagent_type: 'general-purpose' })
  await $.tool.call({ tool: 'Agent', description: 'look up', prompt: 'What is the default value of shared_buffers?', subagent_type: 'Web Researcher' })
  for (const call of seen.filter(x => x.tool === 'Agent')) expect(call.model).toBeUndefined()
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).not.toContain('routed this session')
})

test('ask mode keeps the call when no one can answer', { options: { routing: 'ask' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  ROUTING_MOCKS(on, seen, 'deny')
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  const kept = seen.find(x => x.tool === 'Agent')
  expect(kept?.model).toBeUndefined()
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('[find_feature] kept')
})

test('off mode touches nothing', { options: { routing: 'off' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  ROUTING_MOCKS(on, seen, 'deny')
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  expect(seen.find(x => x.tool === 'Agent')?.model).toBeUndefined()
  expect(seen.some(x => x.tool === 'AskUserQuestion')).toBe(false)
})

test('ask mode routes the call when the person picks the measured option', { options: { routing: 'ask' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  ROUTING_MOCKS(on, seen, 'haiku low (measured 214/216, $0.005/success)')
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  const ask = seen.find(x => x.tool === 'AskUserQuestion') as { questions?: { options?: { label: string }[] }[] } | undefined
  expect(ask?.questions?.[0]?.options?.map(o => o.label)).toEqual(['haiku low (measured 214/216, $0.005/success)', 'Keep inherit', 'Always route this session'])
  const call = seen.find(x => x.tool === 'Agent')
  expect(call?.model).toBe('haiku')
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('[find_feature] routed')
})
