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

export type RoutedAgent = { file: string; name?: string; want: string; have: string | null; state: 'applied' | 'drifted' | 'missing' | 'absent' }

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
  changes?: { events: Change[]; realized: Realized | null; history?: Realized[] }
  learned?: { cells: LearnedCell[]; sessions: LearnedSession[]; threshold: number }
  /** the window in weekly slots, oldest first */
  slots?: { since: string; until: string; spend: number; calls: number; struggled: number; routed: number }[]
  /** what the router rewrote in the window, from its own log */
  routed_window?: { n: number; kept: number }
  overrides?: Record<string, Record<string, Override>>
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
  by_class: Record<string, { n: number; cost: number; types: Record<string, number>; models?: Record<string, { n: number; cost: number }>; last?: string }>
  previous: { since: string; main_total: number; subagents_total: number }
  /** catalog $ per day over the window, oldest first: the pane's sparkline */
  daily?: { date: string; cost: number }[]
}

/** One place the window could have consumed less for the same work, with its evidence. */
export type Suggestion = {
  id: string
  /** learned: from this machine's own transcripts (struggle rates, context boundaries), not from the benchmark */
  kind: 'measured' | 'extrapolated' | 'unmeasured' | 'learned'
  title: string
  stake: number
  saving: [number, number] | null
  basis: string
  action: string
  /** estimate against real, from the latest change window (tools/status.py verdicts) */
  real?: { since: string; span?: string; est: number | null; saved: number | null; per_window: number | null; state: string }
  /** the person judged it wrong: hidden from the glance, listed under Details */
  dismissed?: boolean
}

export type RateLimit = { kind: string; percentUsed: number; resetsAt?: string }

/** One project and class of Agent call on this machine: how many calls struggled against the rest of the machine. */
export type LearnedCell = {
  project: string; project_key: string; class: string; hot: boolean; rate: number; baseline: number
  n: number; retries: number; error_heavy: number; failed: number; struggled: number; cost: number; examples: string[]
  override: Override | null
}
export type LearnedSession = { project: string; project_key: string; sessions: number; msgs: number; errors: number; compactions: number; per_session: number; ctx_per_msg?: number; read_cost?: number; write_cost?: number; idle_returns?: number; idle_cost?: number }
/** A per-project routing override the person set (tools/overrides.py): applied before the family default. */
export type Override = { model: string; effort: string; since: string; why?: string }

/** A routing change recorded on this machine (tools/changes.py): the point the saving is counted from. */
export type Change = { at: string; kind: string; detail: string; projected?: number | null }
export type RealizedSide = { n: number; cost: number; per_call: number | null; tok_per_call?: number | null; per_mtok?: number | null; models: Record<string, number> }
export type RealizedMainSide = { msgs: number; cost: number; per_msg: number | null; tok_per_msg?: number | null }
/** What the transcripts saved since the last change: cost per unit of the same work before vs after, times the units after. */
export type Realized = {
  since: string
  /** the next change, which closes this window; null while it runs to now */
  until?: string | null
  /** how long the window is, as text */
  span?: string
  kind: string
  what: string
  projected?: number | null
  days: number | null
  /** saved: the same-work figure when `same_work` (the after tokens priced at `ref_model`, minus actual), else per call */
  classes: { class: string; family: string | null; before: RealizedSide; after: RealizedSide; saved: number | null; saved_per_call?: number | null; same_work?: boolean; ref_model?: string | null; vs_baseline?: number | null; baseline_per_call?: number | null; check: { sample: string; successes: string; verdict: string } | null }[]
  main: { before: RealizedMainSide; after: RealizedMainSide; saved: number | null; saved_per_msg?: number | null; same_work?: boolean; ref?: [string, string] | null; vs_baseline?: number | null; baseline_per_msg?: number | null; rows: { model: string; effort: string; before: { msgs: number; per_msg: number } | null; after: { msgs: number; per_msg: number } | null }[] }
  saved: number
  /** against the baseline before the first change: what all the changes did together */
  vs_baseline?: number
  baseline_since?: string
}

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

/** A prompt that read as a different task in a session already re-reading a lot per turn, and what was done. */
export type Switch = { at: number; ctx: number; why: string; action: 'compacted' | 'kept' | 'asked' }

/** One command the widget is running or last ran, with its output. */
export type Job = { name: string; lines: string[]; isRunning: boolean; exitCode: number | null; startedAt: number }

declare module 'claude-code' {
  interface PluginState {
    'model-router': { status: Shaped<Status | null>; job: Shaped<Job | null>; routed: Shaped<Routed[]>; details: Shaped<boolean>; switches: Shaped<Switch[]> }
  }
}
