export type Family = {
  name: string
  model: string | null
  effort: string | null
  variant: string
  rate: string | null
  cost_per_success: number | null
  can_run: boolean
  why: string
  last_check: { sample: string; successes: string; verdict: string } | null
}

export type RoutedAgent = { file: string; want: string; have: string | null; state: 'applied' | 'drifted' | 'missing' }

export type StatusJson = {
  at: string
  platform: string
  claude: string | null
  repo: { is_repo: boolean; head?: string; dirty?: number; ahead?: number | null; behind?: number | null; fetched?: boolean }
  routing: { version: number; decided: string }
  families: Family[]
  agents: { files: number; unused: number; routed: RoutedAgent[] }
  catalog: { verified_oldest: string | null; age_days: number | null }
  ledger: { usage_last: string | null; regress_last: { date: string | null; claude: string | null } | null }
  timer: { kind: string; installed?: boolean; next?: string; note?: string }
  advice: string[]
}

/** The last status read: the JSON when the script ran, else why not. */
export type Status = { at: number; json: StatusJson | null; error: string | null }

/** One command the widget is running or last ran, with its output. */
export type Job = { name: string; lines: string[]; isRunning: boolean; exitCode: number | null; startedAt: number }

declare module 'claude-code' {
  interface PluginState {
    'model-router': { status: Shaped<Status | null>; job: Shaped<Job | null> }
  }
}
