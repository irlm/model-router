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
  agents: { files: 6, unused: 179, routed: [{ file: 'a.md', want: 'haiku low', have: 'haiku low', state: 'applied' }] },
  catalog: { verified_oldest: '2026-10-06', age_days: 26 },
  ledger: { usage_last: '2026-11-01', regress_last: { date: '2026-11-01', claude: '2.1.316' } },
  timer: { kind: 'systemd', installed: true, next: 'Tue 2026-12-01 09:00:00 EST' },
  advice: ['prices verified 40 days ago: check the sources'],
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
  on('process.run', (_, e) => ({
    value: e.argv[1] === '--version' ? { ...ok, stdout: 'Python 3.13.0' } : { ...ok, stdout: JSON.stringify(STATUS) },
  }))
  const pinned: (string | undefined)[] = []
  on('ui.status', (_, e) => { pinned.push(e.text); return { value: undefined } })

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('find_feature haiku low          214/216  0.0046  yes  ok 6/6')
  expect(text).toContain('fix_bug      haiku low +kunit   16/21    0.0158  no   -')
  expect(text).toContain('  - prices verified 40 days ago')
  expect(pinned.at(-1)).toContain('router: 1 to check')

  for (const surface of ['terminal', 'desktop', 'vscode', 'mobile'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /routing v1.1/ }))?.text).toBe('routing v1.1, decided 2026-11-01')
    expect(await ui.find({ type: 'Button', text: /Re-check routing/ })).toBeTruthy()
    await ui.unmount()
  }
})

test('a missing checkout is said in the pane, not thrown', async ($, on) => {
  on('command.register', () => ({ value: { command: 'router' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  mock.clock(on, { now: 1_762_000_000_000 })
  mock.env(on, { HOME: '/home/me' })
  on('fs.exists', () => ({ value: false }))
  on('ui.status', () => ({ value: undefined }))

  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  const { text } = await $.command.run({ ...RUN, command: 'router', args: 'check' })
  expect(text).toContain('no model-router checkout at /home/me/Projects/Github/model-router')

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /no model-router checkout/ }))?.text).toContain('set the path in /config')
  await ui.unmount()
})
