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

export type RoutedAgent = { file: string; name?: string; want: string; have: string | null; state: 'applied' | 'drifted' | 'missing' }

export type StatusJson = {
  at: string
  platform: string
  claude: string | null
  repo: { path?: string; is_repo: boolean; head?: string; dirty?: number; ahead?: number | null; behind?: number | null; fetched?: boolean }
  routing: { version: number; decided: string }
  families: Family[]
  agents: { files: number; unused: number; routed: RoutedAgent[] }
  catalog: { verified_oldest: string | null; age_days: number | null }
  ledger: { usage_last: string | null; regress_last: { date: string | null; claude: string | null } | null }
  timer: { kind: string; installed?: boolean; next?: string; note?: string }
  advice: string[]
  usage?: Usage
  suggestions?: Suggestion[]
}

/** The last 30 days of interactive work, catalog-priced: headroom on a subscription. */
export type Usage = {
  days: number
  since: string
  main_total: number
  main_out_cost: number
  main_rows: { model: string; effort: string; msgs: number; cost: number; out_cost: number }[]
  subagents_total: number
  subagent_calls: number
  by_class: Record<string, { n: number; cost: number; types: Record<string, number>; models?: Record<string, { n: number; cost: number }> }>
  previous: { since: string; main_total: number; subagents_total: number }
  /** catalog $ per day over the window, oldest first: the pane's sparkline */
  daily?: { date: string; cost: number }[]
}

/** One place the window could have consumed less for the same work, with its evidence. */
export type Suggestion = {
  id: string
  kind: 'measured' | 'extrapolated' | 'unmeasured'
  title: string
  stake: number
  saving: [number, number] | null
  basis: string
  action: string
}

export type RateLimit = { kind: string; percentUsed: number; resetsAt?: string }

/** The last status read: the JSON when the script ran, else why not. */
export type Status = {
  at: number
  json: StatusJson | null
  error: string | null
  rateLimits: RateLimit[]
  /** '' when the configured checkout served the read; 'marketplace clone' when the clone the plugin install made did */
  where: string
}

/** One Agent call the router saw: what was asked, which measured family covered it, what ran. */
export type Routed = {
  at: number
  agent: string
  family: string
  from: string
  to: string
  /** auto: rewritten without asking; routed: the person chose it; kept: the person kept what was asked, or no one could be asked */
  decision: 'auto' | 'routed' | 'kept'
  description: string
}

/** One command the widget is running or last ran, with its output. */
export type Job = { name: string; lines: string[]; isRunning: boolean; exitCode: number | null; startedAt: number }

declare module 'claude-code' {
  interface PluginState {
    'model-router': { status: Shaped<Status | null>; job: Shaped<Job | null>; routed: Shaped<Routed[]>; details: Shaped<boolean> }
  }
}
