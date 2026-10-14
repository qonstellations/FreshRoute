// Presenter story mode (ARCHITECTURE §16, D-24): the ordered beats of the 3-minute pitch.
// A beat only picks a tab and a `step`; each tab decides what `step` reveals. No KPI logic here.
import type { RunDetail } from '../types'

export type StoryTab = 'Scoreboard' | 'Plan' | 'Robustness' | 'Replan' | 'Trust'
export type Beat = { tab: StoryTab; step: number; title: string }

/** Props every tab receives. `step` undefined = normal mode (show everything). */
export type TabProps = { run: RunDetail; runId: string; step?: number }

export const BEATS: Beat[] = [
  { tab: 'Scoreboard', step: 0, title: 'KPIs roll' },
  { tab: 'Scoreboard', step: 1, title: 'Net vs baseline + spoilage melts' },
  { tab: 'Scoreboard', step: 2, title: 'Ladder: fifo' },
  { tab: 'Scoreboard', step: 3, title: 'Ladder: fefo' },
  { tab: 'Scoreboard', step: 4, title: 'Ladder: last_day_50' },
  { tab: 'Scoreboard', step: 5, title: 'Ladder: milp' },
  { tab: 'Scoreboard', step: 6, title: 'Ladder: milp_markdown' },
  { tab: 'Scoreboard', step: 7, title: 'Independent validator' },
  { tab: 'Plan', step: 0, title: 'Routes draw on the map' },
  { tab: 'Plan', step: 1, title: 'Dispatch sheet' },
  { tab: 'Plan', step: 2, title: 'Why this shipment? (reason card)' },
  { tab: 'Robustness', step: 0, title: 'Plan beats baseline across sampled futures' },
  { tab: 'Robustness', step: 1, title: 'P10–P90 bands: net, spoilage, fulfilment' },
  { tab: 'Robustness', step: 2, title: 'Sensitivity: Q10 and ε' },
  { tab: 'Replan', step: 0, title: 'Event: NH-48 jam' },
  { tab: 'Replan', step: 1, title: 'Replan: batches re-routed, dispatched ones frozen' },
  { tab: 'Replan', step: 2, title: 'ΔKPIs vs doing nothing + narration' },
  { tab: 'Trust', step: 0, title: 'Reproducible: manifest + seed' },
]

export const HOTKEYS: [string, string][] = [
  ['P', 'Toggle story mode'],
  ['→ / Space / PgDn', 'Next beat'],
  ['← / PgUp', 'Previous beat'],
  ['Esc', 'Exit story mode'],
  ['S', 'Toggle stage (dark, large)'],
  ['1 – 5', 'Jump to tab'],
  ['?', 'This help'],
]
