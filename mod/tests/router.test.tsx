import { expect, mock, test } from 'claude-code/testing'

const STATUS = {
  at: '2026-11-01T12:00', platform: 'Linux', claude: '2.1.316',
  repo: { is_repo: true, head: 'abc1234', dirty: 0, ahead: 0, behind: 0, fetched: false },
  routing: { version: 1.1, decided: '2026-11-01' },
  families: [
    { name: 'find_feature', model: 'haiku', effort: 'low', variant: '', rate: '214/216', cost_per_success: 0.0046, can_run: true, why: '',
      last_check: { sample: '6', successes: '6', verdict: 'ok' }, step_up: { model: 'sonnet', effort: 'low', rate: '144/144 over 2 cold trials', cost_per_success: 0.1173 } },
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
/** Lets a job's detached loop (process.spawn, then the refresh) run to its end before the next command. */
const settled = () => new Promise(r => setTimeout(r, 20))

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
  on('ui.close', () => ({ value: undefined }))

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
  expect(pinned.at(-1)).toBe('saved $13 since 10-30 · up to $72 less last 30d (12%; $0.00 measured) · 1 to check · /router')
  expect(text).toContain('suggestions (the last 30 days could have consumed up to $72 less of $592 (12%): $72 extrapolated):')
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
    expect((await ui.find({ type: 'Text', text: /^\[ Suggestions \]$/ }))?.text).toBe('[ Suggestions ]')
    expect((await ui.find({ type: 'Text', text: /^Model router$/ }))?.text).toBe('Model router')             // the header bar
    expect(await ui.find({ type: 'Button', text: /Monitor/ })).toBeTruthy()
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

test('/router setup installs the agents and says what the pane means; /router prune runs the dry run, move and revert', async ($, on) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => ({ value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify({ ...STATUS, agents: { ...STATUS.agents, files: 180 } }) } }))
  const spawned: string[] = []
  on('process.spawn', async function* (_, e) {
    spawned.push(e.argv.slice(1).join(' '))
    yield { stream: 'stdout', text: '2 files would move\n' }
    return { value: { code: 0 } }
  })
  on('ui.status', () => ({ value: undefined }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const setup = await $.command.run({ ...RUN, command: 'router', args: 'setup' })
  expect(setup.text).toContain('apply agents started')
  expect(setup.text).toContain('yellow "to check" lines are things to do, not failures')
  expect(setup.text).toContain('180 agent files sit in ~/.claude/agents')
  expect(spawned.at(-1)).toBe('apply_agents.py')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prune' })).text).toContain('prune agents (dry run) started')
  expect(spawned.at(-1)).toBe('tools/prune_agents.py --dry-run')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prune move' })).text).toContain('/router prune revert undoes it')
  expect(spawned.at(-1)).toBe('tools/prune_agents.py')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prune revert' })).text).toContain('restore the pruned agents started')
  expect(spawned.at(-1)).toBe('tools/prune_agents.py --revert')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prune skills' })).text).toContain('prune skills (dry run) started')
  await settled()
  expect(spawned.at(-1)).toBe('tools/prune_skills.py --dry-run')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prune skills move' })).text).toContain('/router prune skills revert undoes it')
  await settled()
  expect(spawned.at(-1)).toBe('tools/prune_skills.py')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prune all move' })).text).toContain('prune agents and skills started')
  await settled()
  expect(spawned.at(-1)).toBe('tools/prune_skills.py --agents')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prune all revert' })).text).toContain('restore the pruned agents and skills started')
  await settled()
  expect(spawned.at(-1)).toBe('tools/prune_skills.py --agents --revert')
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prune everything' })).text).toContain('prune takes nothing (dry run), move or revert')
  await settled()   // the last job's loop ends inside the test
})

test('/router doctor runs the installation check; /router agents pins, checks and updates by name, a flagged change needs --accept-flags', async ($, on) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => ({ value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(STATUS) } }))
  const spawned: string[] = []
  on('process.spawn', async function* (_, e) {
    spawned.push(e.argv.slice(1).join(' '))
    yield { stream: 'stdout', text: 'ok\n' }
    return { value: { code: 0 } }
  })
  on('ui.status', () => ({ value: undefined }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  expect((await $.command.run({ ...RUN, command: 'router', args: 'doctor' })).text).toContain('installation check started')
  expect(spawned.at(-1)).toBe('tools/status.py --doctor')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'agents pin https://github.com/someone/agents' })).text).toContain('pin the agent sources started')
  expect(spawned.at(-1)).toBe('tools/agent_sources.py pin --repo https://github.com/someone/agents')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'agents check' })).text).toContain('--accept-flags a flagged one you have read')
  expect(spawned.at(-1)).toBe('tools/agent_sources.py check')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'agents update testing-api-tester.md --accept-flags' })).text).toContain('/router apply then puts the routed model and effort back')
  expect(spawned.at(-1)).toBe('tools/agent_sources.py update testing-api-tester.md --accept-flags')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'agents' })).text).toContain('pinned agent sources started')
  expect(spawned.at(-1)).toBe('tools/agent_sources.py list')
  await settled()
  expect((await $.command.run({ ...RUN, command: 'router', args: 'agents pin not-a-url' })).text).toContain('agents takes: pin <repository url>')
  expect((await $.command.run({ ...RUN, command: 'router', args: 'agents update ../../etc/passwd' })).text).toContain('agents takes:')
  expect(spawned.at(-1)).toBe('tools/agent_sources.py list')   // neither bad argument reached a process
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
  on('fs.exists', (_, e) => ({ value: posix(e.path).startsWith(CLONE) }))
  on('fs.read', (_, e) => ({
    value: posix(e.path) === '/home/me/.claude/plugins/known_marketplaces.json' ? JSON.stringify({ 'model-router': { installLocation: CLONE } }) : '{}',
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
  SPAWN_MOCKS(on, seen)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const NOTE = { tool: 'Agent', description: 'compare options', prompt: 'Research and compare three message queues; write up a report.', subagent_type: 'general-purpose' } as const
  await $.tool.call(NOTE)
  const sp = await $.agent.spawn(spawnOf(NOTE))
  expect(spawnSeen(seen)?.model).toBe('sonnet')
  await drain($.turn.step({ turnId: 'ta', index: 0, model: 'claude-sonnet-5-5', effort: 'high', messageCount: 1, agentId: sp.agentId }))
  expect((seen.filter(x => x.tool === '$step').at(-1) as { effort?: string })?.effort).toBe('low')
  // an orchestrator that delegates a lookup is not the lookup: left on the session's model (a real misroute, 2026-11-17: routed to haiku, it had no Agent tool)
  const ORCH = { tool: 'Agent', description: 'delegate a lookup', prompt: 'Use the Agent tool to launch a Web Researcher subagent: what is the default value of shared_buffers?', subagent_type: 'general-purpose' } as const
  await $.tool.call(ORCH)
  await $.agent.spawn(spawnOf(ORCH))
  expect(spawnSeen(seen)?.model).toBeUndefined()
  // running a test command and reporting what it said is not a research note: left on the session's model (a real misroute, 2026-11-09)
  const TESTS = { tool: 'Agent', description: 'run the cart tests', prompt: 'Run python3 -m pytest cart -q and report the failures with their assertion messages. Do not change any file.', subagent_type: 'general-purpose' } as const
  await $.tool.call(TESTS)
  await $.agent.spawn(spawnOf(TESTS))
  expect(spawnSeen(seen)?.model).toBeUndefined()
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('routed this session: 1 routed')
  expect(text).toMatch(/general-purpose\s+fable\s+unmeasured\s+run the cart tests/)   // the agents row: the session's model, no family
  expect(text).not.toMatch(/\[research_synthesis\] auto\s+run the cart tests/)         // and no routed line for it
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
  SPAWN_MOCKS(on, seen)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBe('opus')   // the family says haiku low; the project's override wins
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prefer' })).text).toContain('code-explore -> opus low')
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prefer research-synthesis opus low' })).text).toContain('override set for this project')
  expect(argvs.some(a => a.includes('tools/overrides.py set --why set from the pane -- - research-synthesis opus low'))).toBe(true)   // the key after --: it may start with a dash
  expect(argvs.some(a => a.includes('tools/routed_log.py add find_feature Explore inherit opus low auto --project=-'))).toBe(true)
  expect((await $.command.run({ ...RUN, command: 'router', args: 'prefer nope' })).text).toContain('prefer needs')
})

test('a Windows working directory keys its overrides and its routed log the way Claude Code names the transcript folder', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const argvs: string[] = []
  // C:\Users\me\proj -> C--Users-me-proj: every character that is not a letter or a digit is a dash
  const withOverride = { ...STATUS, overrides: { 'C--Users-me-proj': { 'code-explore': { model: 'opus', effort: 'low', since: '2026-11-03T10:00Z' } } } }
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { USERPROFILE: 'C:\\Users\\me', OS: 'Windows_NT' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => {
    argvs.push(e.argv.join(' '))
    return { value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: e.argv[1] === 'tools/status.py' ? JSON.stringify(withOverride) : '{}' } }
  })
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('tool.call', (_, e) => { seen.push(e as unknown as Record<string, unknown>); return { result: {} } })
  SPAWN_MOCKS(on, seen)
  await $.session.start({ cwd: 'C:\\Users\\me\\proj', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBe('opus')                                                       // the project's override found under its Windows key
  expect(argvs.some(a => a.includes('tools/routed_log.py add find_feature Explore inherit opus low auto --project=C--Users-me-proj'))).toBe(true)
  expect(argvs.some(a => a.startsWith('python3 tools/status.py') || a.startsWith('python tools/status.py'))).toBe(true)   // the first Python 3 found serves
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
  SPAWN_MOCKS(on, seen)
}
/** The engine side of a spawn and a subagent's request, recorded in `seen` as `$spawn` and `$step` rows: what the subagent runs on. */
let spawned = 0
const SPAWN_MOCKS = (on: On, seen: Record<string, unknown>[]) => {
  on('agent.spawn', (_, e) => { seen.push({ tool: '$spawn', ...e }); return { model: e.model ?? 'claude-fable-5-1', agentId: `a${++spawned}` } })
  on('turn.step', async function* (_, e) { seen.push({ tool: '$step', ...e }); return { turnId: e.turnId, index: e.index, answer: '', toolUses: [] } })
}
/** The spawn an Agent call makes, as the engine reports it. */
const spawnOf = (call: { tool_use_id?: string; prompt: string; description: string; subagent_type?: string }) =>
  ({ tool_use_id: call.tool_use_id ?? 'tu', prompt: call.prompt, description: call.description, subagentType: call.subagent_type ?? 'general-purpose', provider: { kind: 'model' }, parentModel: 'claude-fable-5-1' } as const)
/** A path as the test wrote it: the engine on Windows resolves it to D:\\home\\me\\... before the mocks see it. */
const posix = (p: string) => p.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')
const spawnSeen = (seen: Record<string, unknown>[]) => seen.filter(x => x.tool === '$spawn').at(-1) as { model?: string } | undefined

const EXPLORE = { tool: 'Agent', tool_use_id: 'tu-explore', description: 'find the parser', prompt: 'Find where the config file is parsed and report the function.', subagent_type: 'Explore' } as const

test('auto mode runs an Explore call on haiku low, the measured find_feature default', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  ROUTING_MOCKS(on, seen, 'deny')
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  const call = seen.find(x => x.tool === 'Agent')
  expect([call?.model, call?.effort]).toEqual([undefined, undefined])   // the tool input is never rewritten: auto mode's review of it stands
  const sp = await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBe('haiku')                           // the spawn inside the call carries the model
  await drain($.turn.step({ turnId: 'ta', index: 0, model: 'claude-haiku-5-5', effort: 'high', messageCount: 1, agentId: sp.agentId }))
  expect((seen.filter(x => x.tool === '$step').at(-1) as { effort?: string })?.effort).toBe('low')   // and its requests the effort
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
  await $.agent.spawn(spawnOf({ prompt: 'What is the default value of shared_buffers?', description: 'look up', subagent_type: 'Web Researcher' }))
  expect(spawnSeen(seen)?.model).toBeUndefined()
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
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBeUndefined()
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('[find_feature] kept')
})

test('off mode touches nothing', { options: { routing: 'off' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  ROUTING_MOCKS(on, seen, 'deny')
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(seen.find(x => x.tool === 'Agent')?.model).toBeUndefined()
  expect(spawnSeen(seen)?.model).toBeUndefined()
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
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('[find_feature] routed')
})

const LIVE_MOCKS = (on: On, seen: Record<string, unknown>[], steps: unknown[], failing: string | null, runsJson: unknown[] | null = null) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  // the status this machine would read: find_feature and fix_bug as the shared fixture, plus web_research decided at haiku low
  const LIVE_STATUS = { ...STATUS, families: [...STATUS.families, { name: 'web_research', model: 'haiku', effort: 'low', variant: '', rate: '76/78', cost_per_success: 0.0197, can_run: true, why: '', last_check: null }] }
  on('process.run', (_, e) => ({ value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : e.argv[1] === 'tools/runs.py' ? { ...ok, stdout: e.argv.includes('--json') ? JSON.stringify(runsJson ?? []) : `${(runsJson ?? []).length} saved` } : { ...ok, stdout: JSON.stringify(LIVE_STATUS) } }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('session.model', () => ({ value: 'claude-fable-5-1' }))
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
  on('turn.step', async function* (_, e) { steps.push(e.effort); return { turnId: e.turnId, index: e.index, answer: '', toolUses: [] } })
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('tool.call', (_, e) => { seen.push(e as unknown as Record<string, unknown>); return failing && e.tool === failing ? { result: {}, isError: true } : { result: {} } })
}
/** A streaming event's hooks run as its stream is read: read it to the end. */
const drain = async (st: AsyncIterable<unknown>) => { for await (const _ of st) { /* chunks */ } }
const USAGE = { model: 'claude-fable-5-1', input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 100000, cache_creation_input_tokens: 0 }

test('main-session effort auto: a lookup prompt runs at the measured low effort, goes back to the session effort after 3 tool errors, and the pane shows the live turn', { options: { mainEffort: 'auto', routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, 'Bash')
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'What is the default value of shared_buffers in PostgreSQL 17?', turnId: 't1' })
  await drain($.turn.step({ turnId: 't1', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 1 }))
  expect(steps.at(-1)).toBe('low')                                   // web_research is measured at low: the request runs there
  for (let i = 0; i < 3; i++) await $.tool.call({ tool: 'Bash', command: 'false' })
  await drain($.turn.step({ turnId: 't1', index: 1, model: 'claude-fable-5-1', effort: 'high', messageCount: 7 }))
  expect(steps.at(-1)).toBe('high')                                  // three tool errors: the session's own effort again
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 't1', reason: 'answer', usage: USAGE })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('this session · 1 turn · $0.14 · cache hit 99% · fable-5-1 high')   // 1000*10 + 2000*50 + 100000*0.25 per Mtok
  expect(text).toContain('1 turn with 3+ tool errors')
  expect(text).toContain('auto: 0 at the measured effort (est $0.00 less), 1 back up after errors')
  // a prompt nothing measured covers runs as the session has it
  await $.turn.start({ text: 'Refactor the billing module and write the release notes', turnId: 't2' })
  await drain($.turn.step({ turnId: 't2', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 9 }))
  expect(steps.at(-1)).toBe('high')
  await settled()   // the detached work (log writes, the change record) ends inside the test
})

test('main-session effort advise (the default) changes nothing and says what it would have done; /router effort auto switches', async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, null)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'What is the default value of shared_buffers in PostgreSQL 17?', turnId: 't1' })
  await drain($.turn.step({ turnId: 't1', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 1 }))
  expect(steps.at(-1)).toBe('high')
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 't1', reason: 'answer', usage: USAGE })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('advise: 1 turn read as a measured task and would run at low (est $0.01 less): /router effort auto')
  expect((await $.command.run({ ...RUN, command: 'router', args: 'effort auto' })).text).toContain('main-session effort auto for this session')
  await $.turn.start({ text: 'What is the default value of shared_buffers in PostgreSQL 17?', turnId: 't2' })
  await drain($.turn.step({ turnId: 't2', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 3 }))
  expect(steps.at(-1)).toBe('low')
  await settled()   // the detached work (log writes, the change record) ends inside the test
})

test('a routed Agent call that fails escalates its family: the next call runs as asked and the pane says why', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, 'Agent')
  on('agent.spawn', (_, e) => { seen.push({ tool: '$spawn', ...e }); return { model: e.model ?? 'claude-fable-5-1', agentId: `a${++spawned}` } })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'find where the config loader is', turnId: 't1' })
  await $.tool.call(EXPLORE)
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBe('haiku')     // routed, then it failed
  const again = { ...EXPLORE, tool_use_id: 'tu-explore-2', description: 'find the schema loader' }
  await $.tool.call(again)
  await $.agent.spawn(spawnOf(again))
  expect(spawnSeen(seen)?.model).toBe('sonnet')    // escalated to the measured step up (sonnet low, 144/144), not straight to the session model
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 't1', reason: 'answer', usage: USAGE })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('agents   2 calls · 1 routed · escalated: find_feature (the step up (sonnet low) failed too)')   // every Agent call fails in this test: the default, then the step up
  expect(text).toContain('inherit -> sonnet low (step up)  [find_feature] escalated')
  await settled()   // the detached work (log writes, the change record) ends inside the test
})

test('an Agent call re-issued within minutes of a routed one, with the same words, escalates its family', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  // LIVE_MOCKS with a clock that can move: a re-issue needs half a minute to have passed since the routed call
  let clockNow = 1_762_000_000_000
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('clock.now', () => ({ value: clockNow }))
  on('clock.every', () => ({ value: undefined }))
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => ({ value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(STATUS) } }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('session.model', () => ({ value: 'claude-fable-5-1' }))
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
  on('turn.step', async function* (_, e) { steps.push(e.effort); return { turnId: e.turnId, index: e.index, answer: '', toolUses: [] } })
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('tool.call', (_, e) => { seen.push(e as unknown as Record<string, unknown>); return { result: {} } })
  on('agent.spawn', (_, e) => { seen.push({ tool: '$spawn', ...e }); return { model: e.model ?? 'claude-fable-5-1', agentId: `a${++spawned}` } })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  const first = await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  // a sibling with similar words, launched while the first still runs (two searches in parallel), is routed too, not an escalation
  const sibling = { ...EXPLORE, tool_use_id: 'tu-explore-sib', description: EXPLORE.description + ' too' }
  await $.tool.call(sibling)
  const second = await $.agent.spawn(spawnOf(sibling))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  // two calls issued together, before either spawned (the engine launches a parallel batch that way): both routed
  const pairA = { ...EXPLORE, tool_use_id: 'tu-pair-a', description: EXPLORE.description + ' here' }
  const pairB = { ...EXPLORE, tool_use_id: 'tu-pair-b', description: EXPLORE.description + ' there' }
  await $.tool.call(pairA)
  await $.tool.call(pairB)
  const pa = await $.agent.spawn(spawnOf(pairA))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  const pb = await $.agent.spawn(spawnOf(pairB))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  for (const [id, turnId] of [[pa.agentId, 'tpa'], [pb.agentId, 'tpb']] as const) await $.turn.complete({ answer: 'ok', durationMs: 1000, isAborted: false, turnId, reason: 'answer', agentId: id })
  await $.turn.complete({ answer: 'ok', durationMs: 1000, isAborted: false, turnId: 'te1', reason: 'answer', agentId: first.agentId })
  await $.turn.complete({ answer: 'ok', durationMs: 1000, isAborted: false, turnId: 'te2', reason: 'answer', agentId: second.agentId })
  // the same call again, a minute later, after the routed ones ended: a re-issue, the family escalates
  clockNow += 60_000
  const again = { ...EXPLORE, tool_use_id: 'tu-explore-2', description: EXPLORE.description + ' again' }
  await $.tool.call(again)
  await $.agent.spawn(spawnOf(again))
  expect(spawnSeen(seen)?.model).toBe('sonnet')    // the re-issue goes to the step up first
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('escalated: find_feature (re-issued within 10 min of a routed call)')
  expect(text).toContain('inherit -> sonnet low (step up)  [find_feature] escalated')
  // setting the mode clears the escalations: the same call is routed again
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'routing auto' }))
  expect(text).toContain('escalated families cleared')
  const third = { ...EXPLORE, tool_use_id: 'tu-explore-3', description: EXPLORE.description + ' once more' }
  await $.tool.call(third)
  const t3 = await $.agent.spawn(spawnOf(third))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  await $.turn.complete({ answer: 'ok', durationMs: 1000, isAborted: false, turnId: 'te3', reason: 'answer', agentId: t3.agentId })
  // a similar search under a new prompt is new work, not a re-issue: routed (the chains of 2026-11-17 phrased every search alike)
  await $.turn.start({ text: 'now find the loader too', turnId: 'tnext' })
  const fourth = { ...EXPLORE, tool_use_id: 'tu-explore-4', description: EXPLORE.description + ' as well' }
  await $.tool.call(fourth)
  await $.agent.spawn(spawnOf(fourth))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  await settled()   // the detached work (log writes, the change record) ends inside the test
})

test('the pane names the loaded widget version, and warns when the checkout has another', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  let have = '0.9.0'
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => ({ value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify({ ...STATUS, widget: { version: have, tagged: true } }) } }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('tool.call', (_, e) => { seen.push(e as unknown as Record<string, unknown>); return { result: {} } })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toMatch(/widget \d+\.\d+\.\d+ loaded; the checkout has 0\.9\.0: \/router upgrade/)
  have = text.match(/widget (\d+\.\d+\.\d+) loaded/)![1]
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).toMatch(/widget \d+\.\d+\.\d+ loaded$/m)
  expect(text).not.toContain('the checkout has')
  await settled()
})

test('the run monitor: the main session at the root, each agent a box under its spawner with the arrow weighted by the context sent, live tails from tool calls, and the event log', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, 'Bash')
  let n = 0
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: `m${++n}` }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const SPAWN = { tool_use_id: 'tm1', prompt: 'Find where the config file is parsed and report the function. ' + 'x'.repeat(70000), description: 'find the parser', subagentType: 'Explore', provider: { kind: 'model' }, parentModel: 'claude-fable-5-1', model: 'claude-haiku-5-5' } as const
  await $.agent.spawn(SPAWN)
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tm2', description: 'look up the RFC', subagentType: 'Web Researcher', prompt: 'What is the RFC number of TLS 1.3?', parentAgentId: 'm1' })
  await drain($.turn.step({ turnId: 'tm1', index: 0, model: 'claude-haiku-5-5', effort: 'low', messageCount: 1, agentId: 'm1' }))
  await $.tool.call({ tool: 'Grep', pattern: 'parse_config', path: 'tools', agentId: 'm1' })
  await $.tool.call({ tool: 'Bash', command: 'python3 -m pytest -q', agentId: 'm1' })
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 'tm2', reason: 'answer', agentId: 'm2', usage: { model: 'claude-haiku-5-5', input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 10000, cache_creation_input_tokens: 0 } })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' })
  expect(text).toContain('Agent run pane opened.')
  expect(text).toContain('agent run · 1 running · 1 done ($0.00)')
  expect(text).toContain('┌ 00 main session')
  expect(text).toMatch(/┗━━ ~18k ━━▶\n\s*┌ 01 Explore/)              // 70k characters: a heavy arrow, on the row above the box
  expect(text).toMatch(/● RUNNING\s+haiku low\s+\S+\s+1 step/)
  expect(text).toMatch(/┗┄┄ ~\d+ ┄┄▶\n\s*┌ 02 Web Researcher/)     // a short prompt: a light arrow, under its spawner
  expect(text).toMatch(/● DONE\s+haiku\s+\S+\s+0 steps\s+\$0\.00/)
  expect(text).toContain('● 01 Explore / live')
  expect(text).toMatch(/\d\d:\d\d:\d\d  Grep "parse_config" tools/)
  expect(text).toMatch(/ERROR \$ python3 -m pytest -q/)
  expect(text).toContain('01 Explore spawned on haiku (~18k ctx)')   // not routed here, so no effort known at the spawn
  expect(text).toMatch(/└──┬[─]+┘\n {3}┗━━/)                          // the trunk leaves the parent's box where the ┬ is, three columns in
  expect(text).toContain('02 Web Researcher spawned on haiku (~9 ctx) by 01')
  expect(text).toMatch(/02 Web Researcher done in \S+, \$0\.00/)
  expect(text).toMatch(/● 02 Web Researcher \/ stopped\s+\[DONE in \S+\]/)   // one agent at work: the finished one keeps its tail
  // every line of a box is the same width: the top border, the inner lines and the bottom
  const rows = text.split('\n')
  const i = rows.findIndex(l => l.includes('┌ 01 Explore'))
  const box = rows.slice(i, i + 4).map(l => l.trimEnd().length)
  expect(box.length).toBe(4)
  expect(new Set(box).size).toBe(1)
  // the engine resumes an agent under the same id: the same box, its runs counted, and 02's child count does not double
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tm3', description: 'look up the RFC', subagentType: 'Web Researcher', prompt: 'What is the RFC number of TLS 1.3? (again)', parentAgentId: 'm1' })
  n = 1   // the mock hands out m2 again
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 'tm3', reason: 'answer', agentId: 'm3' })
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tm4', description: 'look up the RFC', subagentType: 'Web Researcher', prompt: 'And the year?', parentAgentId: 'm1' })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toContain('┌ 02 Web Researcher · 2 runs ')                      // one box for the agent, its runs counted
  expect(text).not.toContain('· run 2')
  expect(text).toContain('02 Web Researcher resumed (run 2, ~3 ctx)')          // the events keep every resume
  expect((text.match(/┌ 02 Web Researcher/g) ?? []).length).toBe(1)
  expect((text.match(/┌ 03 Web Researcher/g) ?? []).length).toBe(1)
  // a resume that comes without a parent id (a hand-back) keeps its spawner: the box stays on 01's trunk
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 'tm4', reason: 'answer', agentId: 'm2' })
  n = 1
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tm5', description: 'look up the RFC', subagentType: 'Web Researcher', prompt: 'And the section?' })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toMatch(/[┣┗]┄┄ ~\d+ ┄┄▶\n\s*┃?┌ 02 Web Researcher · 3 runs/)   // on 01's trunk, not the session's
  expect(text).toContain('02 Web Researcher resumed (run 3, ~4 ctx)')
  expect(text).toMatch(/02 Web Researcher · 3 runs\s+claude-haiku-5-5\s+web_research\s+kept\s+already on the routed model/)   // one Routing row too
  await settled()
})

const MONITOR_PANE = { plugin: 'model-router', component: 'Pane', requestId: 'model-router-monitor', props: { title: 'Agent run', isFocused: false, bodyColumns: 150, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} } } as const

test('the run monitor before any agent: the main session drawn alone, WORKING while its turn runs and IDLE after, with its own tool tail', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, 'Bash')
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  let n = 0
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: `mm${++n}` }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' })
  expect(text).toContain('┌ 00 main session')
  expect(text).toMatch(/● IDLE\s+0 turns · \$0\.00 · 0 agents spawned/)
  expect(text).toContain('no agent spawned yet; Agent calls hang under the session box as they spawn')
  expect(text).toMatch(/● 00 main session \/ live\s+\[IDLE\]/)
  expect(text).toContain('no tool call yet')
  // a turn begins: the box says WORKING, the panel counts the time and lists the main session's own tool calls
  await $.turn.start({ text: 'look at how the parser loads its schema', turnId: 'mt1' })
  await $.tool.call({ tool: 'Grep', pattern: 'parse_config', path: 'tools' })
  await $.tool.call({ tool: 'Bash', command: 'python3 -m pytest -q' })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toMatch(/● WORKING\s+0 turns/)
  expect(text).toMatch(/● 00 main session \/ live\s+\[WORKING \S+\]/)
  expect(text).toMatch(/\d\d:\d\d:\d\d  Grep "parse_config" tools/)
  expect(text).toMatch(/ERROR \$ python3 -m pytest -q/)
  const ui = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /^00 main session$/ }))?.text).toBe('00 main session')
  expect((await ui.find({ type: 'Text', text: /^● WORKING$/ }))?.text).toBe('● WORKING')
  expect((await ui.find({ type: 'Text', text: /^● 00 main session \/ live$/ }))?.text).toBe('● 00 main session / live')
  expect((await ui.find({ type: 'Text', text: /Grep "parse_config" tools/ }))?.text).toContain('Grep "parse_config" tools')
  expect((await ui.find({ type: 'Text', text: /main session at work/ }))?.text).toContain('main session at work')
  await ui.unmount()
  // the turn ends: IDLE since its end, one turn counted
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 'mt1', reason: 'answer', usage: { model: 'claude-fable-5-1', input_tokens: 1000, output_tokens: 200, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toMatch(/● IDLE\s+1 turn · /)
  expect(text).toMatch(/\[IDLE since \d\d:\d\d:\d\d\]/)
  // a run of two agents ends: the finished ones keep their tail, and the main session's panel is back beside them
  const SPAWN = { tool_use_id: 'mq1', prompt: 'Find where the config is parsed.', description: 'find the parser', subagentType: 'Explore', provider: { kind: 'model' }, parentModel: 'claude-fable-5-1', model: 'claude-haiku-5-5' } as const
  await $.agent.spawn(SPAWN)
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'mq2', description: 'find the loader' })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).not.toContain('● 00 main session / live')                       // two at work: their tails have the room
  await $.turn.complete({ answer: 'ok', durationMs: 1000, isAborted: false, turnId: 'mq1', reason: 'answer', agentId: 'mm1' })
  await $.turn.complete({ answer: 'ok', durationMs: 1000, isAborted: false, turnId: 'mq2', reason: 'answer', agentId: 'mm2' })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toContain('● 01 Explore / stopped')
  expect(text).toContain('● 00 main session / live')
  const ui2 = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  expect((await ui2.find({ type: 'Text', text: /^● 00 main session \/ live$/ }))?.text).toBe('● 00 main session / live')
  await ui2.unmount()
  await settled()
})

test('the run monitor pane draws the graph: a box per agent in its state colour, the arrow label between spawner and child, the live panel of the agent at work, the event log; the list view is the text; a narrow pane stacks', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, 'Bash')
  let n = 0
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: `p${++n}` }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const SPAWN = { tool_use_id: 'tp1', prompt: 'Find where the config file is parsed and report the function. ' + 'x'.repeat(70000), description: 'find the parser', subagentType: 'Explore', provider: { kind: 'model' }, parentModel: 'claude-fable-5-1', model: 'claude-haiku-5-5' } as const
  await $.agent.spawn(SPAWN)
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tp2', description: 'look up the RFC', subagentType: 'Web Researcher', prompt: 'What is the RFC number of TLS 1.3?', parentAgentId: 'p1' })
  await drain($.turn.step({ turnId: 'tp1', index: 0, model: 'claude-haiku-5-5', effort: 'low', messageCount: 1, agentId: 'p1' }))
  await $.tool.call({ tool: 'Grep', pattern: 'parse_config', path: 'tools', agentId: 'p1' })
  await $.turn.complete({ answer: '', durationMs: 1000, isAborted: false, turnId: 'tp2', reason: 'error', agentId: 'p2' })
  // wide: graph and panels side by side
  let ui = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /^Agent run$/ }))?.text).toBe('Agent run')
  expect((await ui.find({ type: 'Text', text: /┌ 00 main session/ }))?.text).toContain('00 main session')   // a 95-column graph: the staircase, boxes kept
  expect((await ui.find({ type: 'Text', text: /┌ 01 Explore/ }))?.text).toContain('01 Explore')
  expect((await ui.find({ type: 'Text', text: /┌ 02 Web Researcher/ }))?.text).toContain('02 Web Researcher')
  expect((await ui.find({ type: 'Text', text: /● RUNNING/ }))?.text).toContain('● RUNNING')
  expect((await ui.find({ type: 'Text', text: /● FAILED/ }))?.text).toContain('● FAILED')
  expect((await ui.find({ type: 'Text', text: /~18k/ }))?.text).toContain('~18k')                       // the arrow's label, on the branch
  expect((await ui.find({ type: 'Text', text: /^● 01 Explore \/ live$/ }))?.text).toBe('● 01 Explore / live')   // the live panel of the agent at work
  expect((await ui.find({ type: 'Text', text: /Grep "parse_config" tools/ }))?.text).toContain('Grep "parse_config" tools')
  expect((await ui.find({ type: 'Text', text: /^\[ Event log \]$/ }))?.text).toBe('[ Event log ]')
  expect((await ui.find({ type: 'Text', text: /02 Web Researcher failed \(error\)/ }))?.text).toContain('02 Web Researcher failed (error)')
  await ui.unmount()
  // an agent aborted before its answer is STOPPED, red, counted apart
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tp3', description: 'a long check', subagentType: 'general-purpose', prompt: 'Run the whole suite and wait.' })
  await $.turn.complete({ answer: '', durationMs: 1000, isAborted: true, turnId: 'tp3', reason: 'aborted', agentId: 'p3' })
  ui = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /● STOPPED/ }))?.text).toContain('● STOPPED')
  expect((await ui.find({ type: 'Text', text: /03 general-purpose stopped after/ }))?.text).toContain('03 general-purpose stopped after')
  expect((await ui.find({ type: 'Text', text: /2 done \(\$0\.00, 1 failed, 1 stopped\)/ }))?.text).toContain('1 failed, 1 stopped')
  await ui.unmount()
  // narrow: the same parts, stacked
  ui = await $.ui.mount({ ...MONITOR_PANE, props: { ...MONITOR_PANE.props, bodyColumns: 90 }, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /┌ 01 Explore/ }))?.text).toContain('01 Explore')
  expect((await ui.find({ type: 'Text', text: /^● 01 Explore \/ live$/ }))?.text).toBe('● 01 Explore / live')
  // the g button switches to the list view: the text drawing
  await ui.press({ key: 'view' })
  expect((await ui.find({ type: 'Text', text: /^\s*┃?┌ 01 Explore/ }))?.text).toContain('┌ 01 Explore')
  await ui.unmount()
  await settled()
})

test('runs: the agents a prompt spawned are one run, saved when its last agent ends; a named task groups what follows until it ends; the monitor shows the current run and lists the others; a report is written into docs/runs', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  const writes: { path: string; text: string }[] = []
  const SAVED = [{ file: '/home/me/.claude/model-router/runs/2026-11-01/101500-old-task-transcript.json', id: 'transcript:abc:20261101T1015', startedAt: 1_761_992_100_000, prompt: 'an old task', name: null, agentN: 2, cost: 0.03, source: 'transcript' }]
  LIVE_MOCKS(on, seen, steps, null, SAVED)
  let n = 0
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: `r${++n}` }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('fs.write', (_, e) => { writes.push(e as { path: string; text: string }); return { value: undefined } })
  await $.session.start({ cwd: '/work/proj', surface: 'terminal', isInteractive: true })
  // run 1: a prompt spawns two agents; the run ends and is saved when the second one ends
  await $.turn.start({ text: 'find where the parser loads the schema', turnId: 't1' })
  const SPAWN = { tool_use_id: 'tr1', prompt: 'Find where the config file is parsed and report the function.', description: 'find the parser', subagentType: 'Explore', provider: { kind: 'model' }, parentModel: 'claude-fable-5-1', model: 'claude-haiku-5-5' } as const
  await $.agent.spawn(SPAWN)
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tr2', description: 'look up the RFC', subagentType: 'Web Researcher', prompt: 'What is the RFC number of TLS 1.3?' })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' })
  expect(text).toContain('run 1/1 this session · "find where the parser loads the schema" · 2 agents · $0.00 · running')
  await $.turn.complete({ answer: 'the parser is in tools/config.py', durationMs: 1000, isAborted: false, turnId: 'tr1', reason: 'answer', agentId: 'r1', usage: { model: 'claude-haiku-5-5', input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } })
  expect(writes.length).toBe(0)                                                    // one agent still runs: not saved yet
  await $.turn.complete({ answer: 'RFC 8446', durationMs: 1000, isAborted: false, turnId: 'tr2', reason: 'answer', agentId: 'r2' })
  expect(writes.length).toBe(1)
  expect(posix(writes[0].path)).toMatch(/^\/home\/me\/\.claude\/model-router\/runs\/\d{4}-\d\d-\d\d\/\d{6}-find-where-the-parser-loads-the-schema\.json$/)
  const saved = JSON.parse(writes[0].text) as { source: string; meta: { id: string; agentN: number; endedAt: number | null }; agents: { answer: string }[] }
  expect(saved.source).toBe('live')
  expect(saved.meta.id).toBe('turn:t1')
  expect(saved.meta.agentN).toBe(2)
  expect(saved.meta.endedAt).not.toBeNull()
  expect(saved.agents.map(a => a.answer)).toEqual(['the parser is in tools/config.py', 'RFC 8446'])
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toContain('run 1/1 this session · "find where the parser loads the schema" · 2 agents · $0.00 · ended')
  expect(text).toContain('· saved')
  // run 2: a named task groups the agents of several prompts, and ends only by hand
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'task start cache invalidation bug' }))
  expect(text).toContain('task "cache invalidation bug" open')
  await $.turn.start({ text: 'trace the invalidation path', turnId: 't2' })
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tr3', description: 'trace invalidation', prompt: 'Trace the cache invalidation path.' })
  await $.turn.complete({ answer: 'found', durationMs: 1000, isAborted: false, turnId: 'tr3', reason: 'answer', agentId: 'r3' })
  await $.turn.start({ text: 'now check the tests', turnId: 't3' })
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tr4', description: 'check tests', prompt: 'Run the cache tests.' })
  await $.turn.complete({ answer: 'green', durationMs: 1000, isAborted: false, turnId: 'tr4', reason: 'answer', agentId: 'r4' })
  expect(writes.length).toBe(1)                                                    // the task is open: nothing saved yet
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toContain('run 2/2 this session · task "cache invalidation bug" · 2 agents')
  expect(text).toContain('┌ 03 Explore')
  expect(text).not.toContain('┌ 01 Explore')                                      // the current run only
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'task end' }))
  expect(text).toMatch(/task "cache invalidation bug" closed; saved to .*cache-invalidation-bug\.json/)
  expect(writes.length).toBe(2)
  // the report of the current run into the project
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor save' }))
  expect(text).toMatch(/^report written: docs\/runs\/\d{4}-\d\d-\d\d-cache-invalidation-bug\.md/)
  const report = writes[2].text
  expect(report).toContain('# Agent run: cache invalidation bug')
  expect(report).toContain('| 03 | Explore | haiku |')
  expect(report).toContain('### 03 Explore: trace invalidation')
  expect(report).toContain('found')
  // the saved runs on this machine, listed through the Python tool
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'runs' }))
  expect(text).toContain('1 saved run')
  expect(text).toContain('an old task')
  expect(text).toContain('from transcripts')
  // the pane: the history view lists the session's runs and the saved one; picking a run shows it
  const ui = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /^run 2\/2 this session/ }))?.text).toContain('task "cache invalidation bug"')
  await ui.press({ key: 'history' })
  expect((await ui.find({ type: 'Text', text: /^\[ Runs this session \]$/ }))?.text).toBe('[ Runs this session ]')
  expect((await ui.find({ type: 'Text', text: /an old task/ }))?.text).toContain('from transcripts')
  await ui.press({ key: 'run-turn:t1' })
  expect((await ui.find({ type: 'Text', text: /^run 1\/2 this session/ }))?.text).toContain('find where the parser loads the schema')
  expect((await ui.find({ type: 'Text', text: /^01 Explore$/ }))?.text).toBe('01 Explore')
  await ui.unmount()
  await settled()
})

test('the agents block before any agent ran: the full pane names the block in one dim line, the glance shows nothing', { options: { routing: 'auto' } }, async ($, on) => {
  LIVE_MOCKS(on, [], [], null)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('agents  none running yet this session')
  expect(text).not.toContain('agents running')
  await settled()
})

test('the agents block: a spawned agent is one row with its model, family and steps; its child sits under it; a finished one collapses into the counts', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, null)
  let n = 0
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: `a${++n}` }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const SPAWN = { tool_use_id: 'tu1', prompt: 'Find where the config file is parsed and report the function.', description: 'find the parser', subagentType: 'Explore', provider: { kind: 'model' }, parentModel: 'claude-fable-5-1', model: 'claude-haiku-5-5' } as const
  await $.agent.spawn(SPAWN)
  await $.agent.spawn({ ...SPAWN, tool_use_id: 'tu2', description: 'look up the RFC', subagentType: 'Web Researcher', prompt: 'What is the RFC number of TLS 1.3?', parentAgentId: 'a1' })
  await drain($.turn.step({ turnId: 'ta1', index: 0, model: 'claude-haiku-5-5', effort: 'low', messageCount: 1, agentId: 'a1' }))
  await drain($.turn.step({ turnId: 'ta1', index: 1, model: 'claude-haiku-5-5', effort: 'low', messageCount: 3, agentId: 'a1' }))
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('agents running 2')
  expect(text).toMatch(/[▖▘▝▗] agents running 2/)
  expect(text).toMatch(/\| Explore\s+haiku low\s+find_feature\s+find the parser\s+2 steps/)
  expect(text).toMatch(/└ \| Web Researcher\s+haiku\s+web_research\s+look up the RFC\s+0 steps/)
  await $.turn.complete({ answer: 'done', durationMs: 1000, isAborted: false, turnId: 'ta2', reason: 'answer', agentId: 'a2', usage: { model: 'claude-haiku-5-5', input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 10000, cache_creation_input_tokens: 0 } })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).toContain('agents running 1 · done 1 ($0.00)')
  expect(text).toMatch(/✓ Web Researcher\s+haiku\s+web_research\s+look up the RFC\s+0 steps\s+\S+\s+\$0\.00/)
  await $.turn.complete({ answer: '', durationMs: 1000, isAborted: false, turnId: 'ta1', reason: 'error', agentId: 'a1' })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).toContain('agents running 0 · done 2 ($0.00, 1 failed)')
  expect(text).toMatch(/✗ Explore/)
  await settled()
})


test("the monitor's Routing frame: each agent as asked -> ran on with the decision and its evidence, and the run's cost against the as-asked estimate", { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  ROUTING_MOCKS(on, seen, 'deny')
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
  on('turn.complete', (_, e) => ({ text: e.answer }))
  const writes: { path: string; text: string }[] = []
  on('fs.write', (_, e) => { writes.push(e as { path: string; text: string }); return { value: undefined } })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'find where the parser loads the schema, and compare the queues', turnId: 'rq1' })
  await $.tool.call(EXPLORE)
  const sp = await $.agent.spawn(spawnOf(EXPLORE))                                      // routed: inherit -> haiku low
  const NOTE = { tool: 'Agent', tool_use_id: 'tu-note', description: 'compare options', prompt: 'Research and compare three message queues; write up a report.', subagent_type: 'general-purpose' } as const
  await $.tool.call(NOTE)
  const sp2 = await $.agent.spawn(spawnOf(NOTE))                                        // a family not decided in this status: runs as asked
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' })
  expect(text).toContain('[ Routing ]')
  expect(text).toMatch(/01 Explore\s+inherit → haiku low\s+find_feature\s+auto\s+measured 214\/216, \$0\.0046\/success/)
  expect(text).toMatch(/02 general-purpose\s+inherit \(fable\)\s+research_synthesis\s+kept\s+family not decided yet: runs as asked/)
  expect(text).not.toContain('run on the decisions')                                   // still running: no cost yet
  const usage = { input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 10000, cache_creation_input_tokens: 0 }
  await $.turn.complete({ answer: 'the parser', durationMs: 1000, isAborted: false, turnId: 'ta', reason: 'answer', agentId: sp.agentId, usage: { model: 'claude-haiku-5-5', ...usage } })
  await $.turn.complete({ answer: 'a report', durationMs: 1000, isAborted: false, turnId: 'tb', reason: 'answer', agentId: sp2.agentId, usage: { model: 'claude-fable-5-1', ...usage } })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  // haiku: $0.0012 for these tokens; the same tokens on fable, as asked: $0.1125; the note on fable: $0.1125
  expect(text).toMatch(/run on the decisions: \$0\.11 · as asked, est: \$0\.2[23] \(the same tokens at catalog prices/)
  const ui = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /^\[ Routing \]$/ }))?.text).toBe('[ Routing ]')
  expect((await ui.find({ type: 'Text', text: /inherit → haiku low/ }))?.text).toContain('find_feature')
  await ui.unmount()
  // the report carries the same frame
  await $.command.run({ ...RUN, command: 'router', args: 'monitor save' })
  expect(writes.some(w => w.text.includes('## Routing') && w.text.includes('inherit → haiku low'))).toBe(true)
  // a long run: `monitor top` (r in the pane) keeps the five lines that moved the most, the routed one first; `monitor` lists all
  for (let i = 3; i <= 8; i++) {
    const call = { tool: 'Agent', tool_use_id: `tu-plain-${i}`, description: `chore ${i}`, prompt: `Tidy the changelog entry number ${i}.`, subagent_type: 'general-purpose' } as const
    await $.tool.call(call)
    await $.agent.spawn(spawnOf(call))
  }
  const routing = (t: string) => t.slice(t.indexOf('[ Routing ]'), t.indexOf('[ Events ]'))
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor top' }))
  expect(routing(text)).toContain('3 more: the 5 above moved the most')
  expect(routing(text).indexOf('01 Explore')).toBeLessThan(routing(text).indexOf('02 general-purpose'))
  expect(routing(text)).not.toContain('08 general-purpose')
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(routing(text)).toContain('08 general-purpose')
  expect(routing(text)).not.toContain('more: the 5 above')
  // a later call with the same words but its own id is not the routed one: no stale decision on it (seen 2026-11-17)
  const AGAIN = { tool: 'Agent', tool_use_id: 'tu-orch-2', description: 'delegate a lookup', prompt: 'Use the Agent tool to launch a Web Researcher subagent: what is the default value of X?', subagent_type: 'general-purpose' } as const
  await $.tool.call({ ...AGAIN, tool_use_id: 'tu-orch-1' })
  await $.agent.spawn(spawnOf({ ...AGAIN, tool_use_id: 'tu-orch-1' }))
  await $.tool.call(AGAIN)
  await $.agent.spawn(spawnOf(AGAIN))
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(routing(text)).toMatch(/10 general-purpose\s+inherit \(fable\)\s+unmeasured\s+kept\s+no measured family covers it/)
  await settled()
})

test('a forked skill (/code-review runs as a fork of the session, not an Agent call) shows in the monitor: its box, its tail, its end, and why the router left it alone', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => ({ value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(STATUS) } }))
  on('ui.status', () => ({ value: undefined }))
  on('ui.toast', () => ({ value: undefined }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('session.model', () => ({ value: 'claude-fable-5-1' }))
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
  on('turn.step', async function* (_, e) { steps.push(e.effort); return { turnId: e.turnId, index: e.index, answer: '', toolUses: [] } })
  on('turn.complete', (_, e) => ({ text: e.answer }))
  let n = 0
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: `g${++n}` }))
  // the Skill tool's answer for a forked skill, as the engine words it
  on('tool.call', (_, e) => { seen.push(e as unknown as Record<string, unknown>); return e.tool === 'Skill' ? { result: 'Skill "code-review" launched (forked execution, running in the background).\n\nRunning in the background as @code-review' } : { result: {} } })   // the engine's wording, 2.1.327
  await $.session.start({ cwd: '/work/shop', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'review my changes', turnId: 'fk1' })
  await $.tool.call({ tool: 'Skill', skill: 'code-review', args: 'medium' })
  await drain($.turn.step({ turnId: 'fkt1', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 1, agentId: 'fork-1' }))   // no agent.spawn came first
  await $.tool.call({ tool: 'Grep', pattern: 'TODO', path: 'src', agentId: 'fork-1' })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' })
  expect(text).toContain('┌ 01 fork /code-review')
  expect(text).toMatch(/● RUNNING\s+fable high\s+\S+\s+1 step/)
  expect(text).toContain('● 01 fork /code-review / live')
  expect(text).toMatch(/\d\d:\d\d:\d\d  Grep "TODO" src/)
  expect(text).toContain('01 fork /code-review started on fable high')
  expect(text).toMatch(/01 fork \/code-review\s+inherit \(fable high\)\s+unmeasured\s+kept\s+a fork of this session: runs on its model, no Agent call to route/)
  await $.turn.complete({ answer: 'two findings', durationMs: 9000, isAborted: false, turnId: 'fkt1', reason: 'answer', agentId: 'fork-1', usage: { model: 'claude-fable-5-1', input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 100000, cache_creation_input_tokens: 0 } })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toMatch(/01 fork \/code-review done in \S+, \$0\.14/)
  // a request under an id nothing announced and no fork pending is not invented
  await drain($.turn.step({ turnId: 'x', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 1, agentId: 'stranger' }))
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).not.toContain('02 ')
  // a fork launched from inside an agent hangs under its launcher
  const sp = await $.agent.spawn({ tool_use_id: 'tg1', prompt: 'Review the change and run the checks.', description: 'review with checks', subagentType: 'general-purpose', provider: { kind: 'model' }, parentModel: 'claude-fable-5-1' })
  await drain($.turn.step({ turnId: 'g-t1', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 1, agentId: sp.agentId }))
  await $.tool.call({ tool: 'Skill', skill: 'code-review', args: 'low', agentId: sp.agentId })
  await drain($.turn.step({ turnId: 'fkt2', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 1, agentId: 'fork-2' }))
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' }))
  expect(text).toMatch(/┗[━─┄]+ ~\d+k? [━─┄]+▶\n\s*┌ 03 fork \/code-review/)                   // under 02, the agent that launched it
  expect(text).toContain('03 fork /code-review started on fable high')
  await settled()
})

test('a deep tree: the pane keeps the boxes as a staircase when the grid would not fit, o cycles outline, boxes and auto, and /router monitor outline prints the outline', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, null)
  let n = 0
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: `d${++n}` }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const base = { provider: { kind: 'model' }, parentModel: 'claude-fable-5-1' } as const
  const a1 = await $.agent.spawn({ ...base, tool_use_id: 'd1', subagentType: 'general-purpose', description: 'review the change', prompt: 'Review the change with a real check.' })
  const a2 = await $.agent.spawn({ ...base, tool_use_id: 'd2', subagentType: 'general-purpose', description: 'verify the claim', prompt: 'Run the tests and report.', parentAgentId: a1.agentId })
  const a3 = await $.agent.spawn({ ...base, tool_use_id: 'd3', subagentType: 'Explore', description: 'find the callers', prompt: 'Find every caller.', parentAgentId: a2.agentId, model: 'claude-haiku-5-5' })
  await $.agent.spawn({ ...base, tool_use_id: 'd4', subagentType: 'Web Researcher', description: 'the rounding rule', prompt: 'Which rounding?', parentAgentId: a3.agentId, model: 'claude-haiku-5-5' })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor outline' })
  expect(text).toContain('[ Run outline ]')
  expect(text).toMatch(/^● WORKING|^● IDLE/m)
  expect(text).toMatch(/^  ● RUNNING  01 general-purpose/m)
  expect(text).toMatch(/^    ● RUNNING  02 general-purpose/m)
  expect(text).toMatch(/^      ● RUNNING  03 Explore/m)
  expect(text).toMatch(/^        ● RUNNING  04 Web Researcher/m)
  // four levels: the pane keeps the boxes as a staircase (the grid would not fit) and says so; o cycles outline, boxes, auto
  let ui = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /^\[ Run graph \]$/ }))?.text).toBe('[ Run graph ]')
  expect((await ui.find({ type: 'Text', text: /drawn as a staircase.*o shows an outline/ }))?.text).toContain('in a pane of')
  expect((await ui.find({ type: 'Text', text: /^ {4}┌ 01 general-purpose/ }))?.text).toContain('┌ 01 general-purpose')   // four columns in
  expect((await ui.find({ type: 'Text', text: /^ {16}┌ 04 Web Researcher/ }))?.text).toContain('04 Web Researcher')   // the fourth level, still a box, 16 columns in
  await ui.press({ key: 'outline' })                                                      // o: the outline
  expect((await ui.find({ type: 'Text', text: /^\[ Run outline \]$/ }))?.text).toBe('[ Run outline ]')
  await ui.press({ key: 'outline' })                                                      // o: the grid, however wide
  expect((await ui.find({ type: 'Text', text: /^01 general-purpose$/ }))?.text).toBe('01 general-purpose')        // a grid box's own title
  expect(await ui.find({ type: 'Text', text: /staircase/ })).toBeUndefined()
  await ui.press({ key: 'outline' })                                                      // o: back to the automatic choice
  expect((await ui.find({ type: 'Text', text: /drawn as a staircase/ }))?.text).toContain('staircase')
  await ui.unmount()
  await settled()
})

test('the timeline: the day as one bar per run with the lens on the run shown, the run at its own scale with a row per agent in start order, ticks and a live edge; t in the pane; a run of twenty rows folds its finished branches, x unfolds', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, 'Bash')
  let n = 0
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: `tl${++n}` }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'find the parser and check it', turnId: 'tt1' })
  const base = { provider: { kind: 'model' }, parentModel: 'claude-fable-5-1' } as const
  const a1 = await $.agent.spawn({ ...base, tool_use_id: 'tl-1', subagentType: 'general-purpose', description: 'check the parser', prompt: 'Run the parser tests and report.' })
  const a2 = await $.agent.spawn({ ...base, tool_use_id: 'tl-2', subagentType: 'Explore', description: 'find the parser', prompt: 'Find the parser.', parentAgentId: a1.agentId, model: 'claude-haiku-5-5' })
  await $.tool.call({ tool: 'Bash', command: 'python3 -m pytest -q', agentId: a1.agentId })
  await $.turn.complete({ answer: 'in tools/config.py', durationMs: 1000, isAborted: false, turnId: 'tl-t2', reason: 'answer', agentId: a2.agentId, usage: { model: 'claude-haiku-5-5', input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 10000, cache_creation_input_tokens: 0 } })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor timeline' })
  expect(text).toMatch(/^\[ Day \]  \d\d:\d\d .*1 run · 2 agents · \$0\.00/m)
  expect(text).toMatch(/^runs {24}[█]*▶/m)                                               // the current run, still running, ends in the live edge (one cell: the clock is frozen)
  expect(text).toMatch(/^ {28}r1/m)                                                       // tagged
  expect(text).toMatch(/^lens {24}\[/m)                                                   // the lens on it
  expect(text).toMatch(/^\[ Run 1\/1 · "find the parser and check it" · \d\d:\d\d → now · 2 agents · \$0\.00 \]/m)
  expect(text).toMatch(/^00 main session {13}[━]*▶/m)
  expect(text).toMatch(/^ {2}01 general-purpose {8}[✗▶]/m)                               // its one tool call failed in the same cell as the live edge, which wins
  expect(text).toMatch(/^ {4}02 Explore +▓ +0s {2}\$0\.00/m)                              // under 01, done, its elapsed and cost after the bar
  expect(text).toContain('▓ done   █ running   ░ quiet   ✗ failed or stopped   │ a tool call   ▶ now')
  // the pane: t shows the timeline with the Routing frame under it; t again, the graph
  const ui = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  await ui.press({ key: 'timeline' })
  expect((await ui.find({ type: 'Text', text: /^\[ Day \]/ }))?.text).toContain('[ Day ]')
  expect((await ui.find({ type: 'Text', text: /^\[ Routing \]$/ }))?.text).toBe('[ Routing ]')
  await ui.press({ key: 'timeline' })
  expect((await ui.find({ type: 'Text', text: /^\[ Run graph \]$/ }))?.text).toBe('[ Run graph ]')
  await ui.unmount()
  // twenty rows: the finished branch under 01 folds into one row once 01 and every agent under it has ended
  for (let i = 3; i <= 21; i++) {
    const sp = await $.agent.spawn({ ...base, tool_use_id: `tl-${i}`, subagentType: 'Explore', description: `search ${i}`, prompt: `Search ${i}.`, parentAgentId: a1.agentId, model: 'claude-haiku-5-5' })
    await $.turn.complete({ answer: 'ok', durationMs: 1000, isAborted: false, turnId: `tl-t${i}`, reason: 'answer', agentId: sp.agentId, usage: { model: 'claude-haiku-5-5', input_tokens: 100, output_tokens: 100, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } })
  }
  await $.turn.complete({ answer: 'checked', durationMs: 1000, isAborted: false, turnId: 'tl-t1', reason: 'answer', agentId: a1.agentId, usage: { model: 'claude-fable-5-1', input_tokens: 1000, output_tokens: 1000, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor timeline' }))
  expect(text).toMatch(/^ {2}01 general-purpose ▸ +▓ +0s {2}\$0\.06 {2}20 done under it/m)
  expect(text).toContain('(haiku ×20; x unfolds)')
  expect(text).not.toMatch(/^ {4}02 Explore/m)
  const ui2 = await $.ui.mount({ ...MONITOR_PANE, surface: 'terminal' })
  await ui2.press({ key: 'timeline' })
  await ui2.press({ key: 'fold' })
  await ui2.unmount()
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor timeline' }))
  expect(text).toMatch(/^ {4}02 Explore/m)                                                 // unfolded
  expect(text).not.toContain('done under')
  await settled()
})

/** Mocks for a routing test with a status of one's own, a clock that can move and a status line that is kept. */
const CUSTOM_MOCKS = (on: On, seen: Record<string, unknown>[], statusJson: unknown, clock: { now: number }, pinned: (string | undefined)[] = [], failing: string | null | ((e: { tool: string }) => boolean | Promise<boolean>) = null, argvs: string[] = [], answer: string | null = null) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('clock.now', () => ({ value: clock.now }))
  on('clock.every', () => ({ value: undefined }))
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: true }))
  on('process.run', (_, e) => { argvs.push(e.argv.join(' ')); return { value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(statusJson) } } })
  on('ui.status', (_, e) => { pinned.push(e.text); return { value: undefined } })
  on('ui.toast', () => ({ value: undefined }))
  on('session.model', () => ({ value: 'claude-fable-5-1' }))
  on('turn.start', (_, e) => ({ turnId: e.turnId }))
  on('turn.complete', (_, e) => ({ text: e.answer }))
  on('tool.call', async (_, e) => {
    seen.push(e as unknown as Record<string, unknown>)
    if (e.tool === 'AskUserQuestion') return answer === null ? { deny: 'no one to ask' } : { result: { questions: e.questions, answers: { [e.questions[0]?.question ?? '']: answer, [e.questions[0]?.header ?? '']: answer } } }
    const fail = typeof failing === 'function' ? await failing(e as { tool: string }) : failing !== null && e.tool === failing
    return fail ? { result: {}, isError: true } : { result: {} }
  })
  on('process.spawn', async function* (_, e) { argvs.push(e.argv.join(' ')); yield { stream: 'stdout', text: 'ok\n' }; return { value: { code: 0 } } })
  SPAWN_MOCKS(on, seen)
}

test('only a call that asks for something dearer is routed: the decided model with no effort said is left alone and not counted, a cheaper model is left alone, the decided model above its effort goes down', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const withNotes = { ...STATUS, families: [...STATUS.families, { name: 'research_synthesis', model: 'sonnet', effort: 'low', variant: '', rate: '12/12', cost_per_success: 0.0935, can_run: true, why: '', last_check: null }] }
  CUSTOM_MOCKS(on, seen, withNotes, { now: 1_762_000_000_000 })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const onHaiku = { ...EXPLORE, tool_use_id: 'tu-h', model: 'haiku' } as const           // the decided model, the effort unsaid: nothing to route
  await $.tool.call(onHaiku)
  await $.agent.spawn(spawnOf(onHaiku))
  expect(spawnSeen(seen)?.model).toBeUndefined()
  const cheaper = { tool: 'Agent', tool_use_id: 'tu-n', description: 'compare options', prompt: 'Research and compare three message queues; write up a report.', subagent_type: 'general-purpose', model: 'haiku' } as const
  await $.tool.call(cheaper)                                                              // a note asked at haiku is not moved up to sonnet
  await $.agent.spawn(spawnOf(cheaper))
  expect(spawnSeen(seen)?.model).toBeUndefined()
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).not.toContain('routed this session')
  const higher = { ...EXPLORE, tool_use_id: 'tu-hh', model: 'haiku', effort: 'high' } as const   // the decided model above its effort: routed down
  await $.tool.call(higher)
  await $.agent.spawn(spawnOf(higher))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  const bigger = { ...EXPLORE, tool_use_id: 'tu-o', model: 'opus', effort: 'low' } as const
  await $.tool.call(bigger)
  await $.agent.spawn(spawnOf(bigger))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).toContain('routed this session: 2 routed, 0 kept (mode auto')
  expect(text).toContain('Explore: haiku high -> haiku low  [find_feature] auto')
  expect(text).toContain('Explore: opus low -> haiku low  [find_feature] auto')
  await settled()
})

test("the status line's routed count is what the router moved: a kept answer is not a routing", { options: { routing: 'ask' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const pinned: (string | undefined)[] = []
  CUSTOM_MOCKS(on, seen, STATUS, { now: 1_762_000_000_000 }, pinned)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)                                   // no one to ask: kept
  await $.tool.call({ ...EXPLORE, tool_use_id: 'tu-explore-2', description: 'find the schema loader' })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('routed this session: 0 routed, 2 kept')
  expect(pinned.at(-1)).not.toContain('routed ')
  await settled()
})

test('escalation by rungs: a failed routed call sends the family to its measured step up, a failed step up to as asked, each stamped when it failed; half an hour later the pane drops it and the family is routed again', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const clock = { now: 1_762_000_000_000 }
  let fails = 2
  // The engine spawns the agent inside the Agent call and returns when it ends: the mock does the same, and the first two calls run 20 minutes, then fail
  CUSTOM_MOCKS(on, seen, STATUS, clock, [], async e => { if (e.tool !== 'Agent') return false; await $.agent.spawn(spawnOf(e as unknown as typeof EXPLORE)); if (fails-- > 0) { clock.now += 20 * 60_000; return true } return false })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'find where the config loader is', turnId: 't1' })
  await $.tool.call(EXPLORE)
  expect(spawnSeen(seen)?.model).toBe('haiku')
  clock.now += 25 * 60_000                                     // 25 minutes after the failure (45 after the call began): still escalated, rung 1
  const again = { ...EXPLORE, tool_use_id: 'tu-explore-2', description: 'find the schema loader' } as const
  await $.tool.call(again)                                     // the step up, and it fails too (20 more minutes)
  expect(spawnSeen(seen)?.model).toBe('sonnet')
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('escalated: find_feature (the step up (sonnet low) failed too)')
  const third = { ...EXPLORE, tool_use_id: 'tu-explore-3', description: 'find the route table' } as const
  await $.tool.call(third)                                     // rung 2: as asked
  expect(spawnSeen(seen)?.model).toBeUndefined()
  clock.now += 31 * 60_000                                     // past the half hour since the step up failed: over
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).not.toContain('escalated: find_feature')
  const later = { ...EXPLORE, tool_use_id: 'tu-explore-4', description: 'find the cache' } as const
  await $.tool.call(later)
  expect(spawnSeen(seen)?.model).toBe('haiku')
  await settled()
})

test('the ledger and the router classify alike: the type first (a reviewer is never a lookup, a browser agent is one on a word), then the orchestrator rule, then the prompt', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const withFlows = { ...STATUS, families: [...STATUS.families,
    { name: 'web_research', model: 'haiku', effort: 'low', variant: '', rate: '76/78', cost_per_success: 0.0197, can_run: true, why: '', last_check: null },
    { name: 'browser_flow', model: 'haiku', effort: 'low', variant: '', rate: '63/63', cost_per_success: 0.064, can_run: true, why: '', last_check: null }] }
  CUSTOM_MOCKS(on, seen, withFlows, { now: 1_762_000_000_000 })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  // the same cases as tools/test_status.py, test_the_type_first_then_the_orchestrator_rule_then_the_prompt
  const cases: [string, string, string | undefined][] = [
    ['Code Reviewer', 'what is the default value of X?', undefined],
    ['browser-tester', 'click the login button', 'haiku'],
    ['general-purpose', 'in the browser, click through the checkout; use the Agent tool for the rest', undefined],
    ['general-purpose', 'open the web page and click sign in', 'haiku'],
    ['general-purpose', 'what is the default value of X?', 'haiku'],
    ['general-purpose', 'what is the cause of this crash in parser.c?', undefined],   // a question about the code in front of the model, not a lookup
  ]
  for (const [i, [type, prompt, model]] of cases.entries()) {
    const call = { tool: 'Agent', tool_use_id: `tu-c${i}`, description: `case ${i}`, prompt, subagent_type: type } as const
    await $.tool.call(call)
    await $.agent.spawn(spawnOf(call))
    expect([type, prompt, spawnSeen(seen)?.model]).toEqual([type, prompt, model])
  }
  await settled()
})

test("a secret in a subagent's Bash line or answer is redacted before the monitor keeps it and the run is saved", { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, null)
  const written: Record<string, string> = {}
  on('fs.write', (_, e) => { written[posix(e.path)] = (e as { text: string }).text; return { value: undefined } })
  on('agent.spawn', (_, e) => ({ model: e.model ?? 'claude-fable-5-1', agentId: 'r1' }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.agent.spawn({ tool_use_id: 'tr1', prompt: 'Find where the config file is parsed.', description: 'find the parser', subagentType: 'Explore', provider: { kind: 'model' }, parentModel: 'claude-fable-5-1', model: 'claude-haiku-5-5' })
  await $.tool.call({ tool: 'Bash', command: 'curl -H "Authorization: Bearer sk-ant-abcdef0123456789" https://api.example/v1', agentId: 'r1' })
  await $.tool.call({ tool: 'Bash', command: 'GITHUB_TOKEN=ghp_ZZZZZZZZZZZZZZZZ gh api repos', agentId: 'r1' })
  await $.tool.call({ tool: 'WebFetch', url: 'https://x.example/data?api_key=0123456789abcdef&page=2', agentId: 'r1' })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' })
  expect(text).toContain('Bearer [redacted]')
  expect(text).toContain('GITHUB_TOKEN=[redacted]')
  expect(text).toContain('api_key=[redacted]&page=2')
  expect(text).not.toContain('abcdef0123456789')
  expect(text).not.toContain('ghp_ZZZZ')
  await $.turn.complete({ answer: 'done; the password: hunter2hunter2 worked, 23k tokens: fine', durationMs: 1000, isAborted: false, turnId: 'tr1', reason: 'answer', agentId: 'r1', usage: { model: 'claude-haiku-5-5', input_tokens: 1000, output_tokens: 2000, cache_read_input_tokens: 10000, cache_creation_input_tokens: 0 } })
  await settled()
  const saved = Object.entries(written).find(([p]) => p.includes('/runs/'))
  expect(saved).toBeDefined()
  expect(saved![1]).toContain('password: [redacted]')
  expect(saved![1]).toContain('23k tokens: fine')
  expect(saved![1]).not.toContain('hunter2')
  expect(saved![1]).not.toContain('ghp_ZZZZ')
})

const FIXES = { name: 'repo_fix', model: 'haiku', effort: 'low', variant: 'vitest', rate: '72/72', cost_per_success: 0.0071, can_run: true, why: '', last_check: null }

test('a family that failed its last regression check is not routed until a check passes', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const regressed = { ...STATUS, families: STATUS.families.map(f => (f.name === 'find_feature' ? { ...f, last_check: { sample: '6', successes: '3', verdict: 'REGRESSED' } } : f)) }
  CUSTOM_MOCKS(on, seen, regressed, { now: 1_762_000_000_000 })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBeUndefined()
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).not.toContain('routed this session')
  expect(text).toContain('last check not ok: find_feature')
  await settled()
})

test('the risk floor: a fix that touches payments, auth or a migration runs as asked and the log says so; a plain fix is routed with the runner note', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  CUSTOM_MOCKS(on, seen, { ...STATUS, families: [...STATUS.families, FIXES] }, { now: 1_762_000_000_000 })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const risky = { tool: 'Agent', tool_use_id: 'tu-r', description: 'fix the payments test', prompt: 'Fix the failing test in the payments module; run npm test until it passes.', subagent_type: 'general-purpose' } as const
  await $.tool.call(risky)
  await $.agent.spawn(spawnOf(risky))
  expect(spawnSeen(seen)?.model).toBeUndefined()
  const plain = { tool: 'Agent', tool_use_id: 'tu-p', description: 'fix the parser test', prompt: 'Fix the failing test in the parser; run npm test until it passes.', subagent_type: 'general-purpose' } as const
  await $.tool.call(plain)
  await $.agent.spawn(spawnOf(plain))
  const sp = spawnSeen(seen) as { model?: string; prompt?: string } | undefined
  expect(sp?.model).toBe('haiku')
  expect(sp?.prompt).toContain('Run the test command before you finish')
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('routed this session: 1 routed, 0 kept, 1 held by the risk floor')
  expect(text).toContain('[repo_fix] floor  fix the payments test')
  await settled()
})

test('a routed fix that ends without running the tests is marked and escalates its family; a routed search that answers "not found" is marked', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  CUSTOM_MOCKS(on, seen, { ...STATUS, families: [...STATUS.families, FIXES] }, { now: 1_762_000_000_000 })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'fix the parser', turnId: 't1' })
  const fix = { tool: 'Agent', tool_use_id: 'tu-f1', description: 'fix the parser test', prompt: 'Fix the failing test in the parser; run npm test until it passes.', subagent_type: 'general-purpose' } as const
  await $.tool.call(fix)
  const v1 = await $.agent.spawn(spawnOf(fix))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  await $.tool.call({ tool: 'Edit', file_path: 'parser.ts', agentId: v1.agentId })    // edits, no test command
  await $.turn.complete({ answer: 'fixed the off-by-one', durationMs: 1000, isAborted: false, turnId: 'tv1', reason: 'answer', agentId: v1.agentId, usage: { model: 'claude-haiku-5-5', input_tokens: 1000, output_tokens: 500, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toMatch(/! general-purpose .* finished without running the tests/)
  expect(text).toContain('escalated: repo_fix (a routed fix finished without running the tests)')
  const fix2 = { ...fix, tool_use_id: 'tu-f2', description: 'fix the lexer test' }
  await $.tool.call(fix2)
  await $.agent.spawn(spawnOf(fix2))
  expect(spawnSeen(seen)?.model).toBeUndefined()                                       // repo_fix has no step up: as asked
  // a fix that runs its tests is a plain success
  await $.command.run({ ...RUN, command: 'router', args: 'routing auto' })             // clears the escalation
  const fix3 = { ...fix, tool_use_id: 'tu-f3', description: 'fix the printer test' }
  await $.tool.call(fix3)
  const v3 = await $.agent.spawn(spawnOf(fix3))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  await $.tool.call({ tool: 'Bash', command: 'npm test -- printer', agentId: v3.agentId })
  await $.turn.complete({ answer: 'green', durationMs: 1000, isAborted: false, turnId: 'tv3', reason: 'answer', agentId: v3.agentId, usage: { model: 'claude-haiku-5-5', input_tokens: 1000, output_tokens: 500, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } })
  // a routed search that found nothing
  await $.tool.call(EXPLORE)
  const v4 = await $.agent.spawn(spawnOf(EXPLORE))
  await $.turn.complete({ answer: 'The config parser could not be found anywhere in the tree.', durationMs: 1000, isAborted: false, turnId: 'tv4', reason: 'answer', agentId: v4.agentId, usage: { model: 'claude-haiku-5-5', input_tokens: 1000, output_tokens: 500, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } })
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).toMatch(/! Explore .* answered "not found"/)
  expect(text).not.toContain('escalated: find_feature')
  expect(text).toMatch(/✓ general-purpose .* fix the printer test/)
  await settled()
})

test('window pressure: above the line, ask mode routes without asking and the pane says so; the burn rate names when the window runs out at this pace', { options: { routing: 'ask', mainEffort: 'advise' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const clock = { now: 1_762_000_000_000 }
  let pct = 40
  const resetsAt = new Date(clock.now + 4 * 3600_000).toISOString()
  CUSTOM_MOCKS(on, seen, { ...STATUS, families: [...STATUS.families, { name: 'web_research', model: 'haiku', effort: 'low', variant: '', rate: '76/78', cost_per_success: 0.0197, can_run: true, why: '', last_check: null }] }, clock)
  const lastStep = () => (seen.filter(x => x.tool === '$step').at(-1) as { effort?: string } | undefined)?.effort
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: 50000, window: 1000000 }, rateLimits: [{ kind: 'five_hour', percentUsed: pct, resetsAt }] } }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('5h  ████████░░░░░░░░░░░░  40% used')
  expect(text).not.toContain('at this pace')
  clock.now += 30 * 60_000; pct = 55                                                  // 15 points in 30 minutes: 45 more points is 90 minutes
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).toMatch(/55% used, resets \d\d:\d\d · at this pace out ~\d\d:\d\d/)
  expect(text).toContain('from 80% of a window, routing and effort go auto')
  await $.tool.call(EXPLORE)                                                           // under the line: ask mode, no one to answer, kept
  expect(seen.some(x => x.tool === 'AskUserQuestion')).toBe(true)
  pct = 85
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).toContain('above 80%: routing auto and effort auto')
  const again = { ...EXPLORE, tool_use_id: 'tu-explore-2', description: 'find the schema loader' } as const
  await $.tool.call(again)                                                            // no question: the measured route
  await $.agent.spawn(spawnOf(again))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  await $.turn.start({ text: 'What is the default value of shared_buffers in PostgreSQL 17?', turnId: 'tp' })
  await drain($.turn.step({ turnId: 'tp', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 1 }))
  expect(lastStep()).toBe('low')                                                      // advise acts under pressure
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'check' }))
  expect(text).toContain('(mode ask, auto under window pressure;')
  await settled()
})

test('main-session effort auto: a turn that delegates goes back to the session effort', { options: { mainEffort: 'auto', routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const steps: unknown[] = []
  LIVE_MOCKS(on, seen, steps, null)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.turn.start({ text: 'What is the default value of shared_buffers in PostgreSQL 17?', turnId: 't1' })
  await drain($.turn.step({ turnId: 't1', index: 0, model: 'claude-fable-5-1', effort: 'high', messageCount: 1 }))
  expect(steps.at(-1)).toBe('low')
  await $.tool.call(EXPLORE)                                                           // the turn orchestrates: not the measured work
  await drain($.turn.step({ turnId: 't1', index: 1, model: 'claude-fable-5-1', effort: 'high', messageCount: 3 }))
  expect(steps.at(-1)).toBe('high')
  await settled()
})

test('the ledger writes itself when the last one is a month old on a checkout of your own, once a day', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const argvs: string[] = []
  const stale = { ...STATUS, ledger: { ...STATUS.ledger, usage_last: '2025-09-20' }, thresholds: { price_days: 30, ledger_days: 35, regress_days: 60 } }   // the clock reads 2025-11-01
  CUSTOM_MOCKS(on, seen, stale, { now: 1_762_000_000_000 }, [], null, argvs)
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await settled()
  expect(argvs.filter(a => a.includes('tools/ledger.py --commit')).length).toBe(1)
  await settled()
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await settled()
  expect(argvs.filter(a => a.includes('tools/ledger.py')).length).toBe(1)             // once a day
  await settled()
})

test('shadow mode: what auto would have done is logged and shown, nothing is moved', { options: { routing: 'shadow' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  CUSTOM_MOCKS(on, seen, STATUS, { now: 1_762_000_000_000 })
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  await $.tool.call(EXPLORE)
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBeUndefined()
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('routed this session: 0 routed, 0 kept, 1 would have been routed (shadow) (mode shadow;')
  expect(text).toContain('Explore: inherit -> haiku low  [find_feature] shadow  find the parser')
  await settled()
})

test('/router replay prices the window under the current routing or a candidate file; /router recheck is the regression check and update still works', { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const argvs: string[] = []
  CUSTOM_MOCKS(on, seen, STATUS, { now: 1_762_000_000_000 }, [], null, argvs)
  on('ui.open', () => ({ value: { isPlaced: true } }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  let { text } = await $.command.run({ ...RUN, command: 'router', args: 'replay' })
  expect(text).toContain('replay started; the pane prices the last 30 days under the current routing.json')
  await settled()
  expect(argvs.some(a => a.endsWith('tools/replay.py'))).toBe(true)
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'replay /tmp/candidate.json' }))
  expect(text).toContain('under /tmp/candidate.json')
  await settled()
  expect(argvs.some(a => a.endsWith('tools/replay.py /tmp/candidate.json'))).toBe(true)
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'recheck' }))
  expect(text).toContain('regression check started')
  await settled()
  expect(argvs.filter(a => a.includes('tools/update.py --sample 6')).length).toBe(1)
  ;({ text } = await $.command.run({ ...RUN, command: 'router', args: 'update' }))
  expect(text).toContain('update is now recheck')
  await settled()
  expect(argvs.filter(a => a.includes('tools/update.py --sample 6')).length).toBe(2)
})

test('the hard pressure line: an unmeasured Agent call is asked about and can be skipped; a measured one is still routed', { options: { routing: 'ask' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  const clock = { now: 1_762_000_000_000 }
  CUSTOM_MOCKS(on, seen, STATUS, clock, [], null, [], 'Skip it: answer with what you have')
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: 50000, window: 1000000 }, rateLimits: [{ kind: 'five_hour', percentUsed: 96, resetsAt: new Date(clock.now + 3600_000).toISOString() }] } }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const notes = { tool: 'Agent', tool_use_id: 'tu-n', description: 'draft the release notes', prompt: 'Draft the release notes for 2.4 from the changelog.', subagent_type: 'general-purpose' } as const
  await $.tool.call(notes).catch(() => undefined)                                      // skipped: the engine's own handler is never reached
  expect(seen.some(x => x.tool === 'Agent' && x.description === 'draft the release notes')).toBe(false)
  expect(seen.some(x => x.tool === 'AskUserQuestion')).toBe(true)
  await $.tool.call(EXPLORE)                                                           // measured, and above the pressure line: routed without a question
  await $.agent.spawn(spawnOf(EXPLORE))
  expect(spawnSeen(seen)?.model).toBe('haiku')
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('1 skipped at the hard line')
  expect(text).toContain('general-purpose: inherit -> skipped  [unmeasured] skipped  draft the release notes')
  expect(text).toContain('from 95% an unmeasured Agent call is asked about')
  await settled()
})

test("the Routing frame says when an agent paid mostly for the prefix: the smallest asks are cheaper inline", { options: { routing: 'auto' } }, async ($, on) => {
  const seen: Record<string, unknown>[] = []
  CUSTOM_MOCKS(on, seen, STATUS, { now: 1_762_000_000_000 })
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.command.run({ ...RUN, command: 'router', args: 'check' })
  const sp = await $.agent.spawn({ tool_use_id: 'tp1', prompt: 'What is the RFC number of TLS 1.3?', description: 'look up the RFC', subagentType: 'general-purpose', provider: { kind: 'model' }, parentModel: 'claude-opus-5-5', model: 'claude-opus-5-5' })
  await drain($.turn.step({ turnId: 'tp1', index: 0, model: 'claude-opus-5-5', effort: 'low', messageCount: 1, agentId: sp.agentId }))
  await $.turn.complete({ answer: 'RFC 8446', durationMs: 1000, isAborted: false, turnId: 'tp1', reason: 'answer', agentId: sp.agentId, usage: { model: 'claude-opus-5-5', input_tokens: 100, output_tokens: 10, cache_read_input_tokens: 23000, cache_creation_input_tokens: 0 } })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'monitor' })
  expect(text).toMatch(/01 general-purpose .* prefix 88% of its cost/)   // (23000 * 0.2) / (100 * 4 + 10 * 20 + 23000 * 0.2) per Mtok
  expect(text).toContain('1 of 1 agents paid mostly for the 23k prefix')
  await settled()
})
