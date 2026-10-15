// DATABASE.md §11.2 responses (api_version 1), field for field; file shapes from §5.1, §5.7–§5.11.
export const API_VERSION = 1

export interface Health { status: 'ok'; schema_version: number; api_version: number }

export type ConfigConstants = Record<string, string | number | boolean | null | (string | number)[]> // GET /api/config

export interface ScenarioInfo { name: string; source: string; horizon_days: number; window_mode: string }

export type GeoRecord = Record<string, string | number | null> // §3.9, UI only

export interface RunSummary { run_id: string; scenario: string; policy: string; seed: number; has_ladder: boolean }
export interface RunsList { runs: RunSummary[]; fixture: boolean }

export interface Kpis {
  spoilage_kg: number; spoilage_pct: number
  demand_fulfillment_pct: number; min_dest_fill_pct: number
  net_inr: number; violations: number
}

export interface Metrics { // §5.7
  schema_version: number
  run_id: string; scenario: string; policy: string; seed: number; realization: string
  kpis: Kpis
  spoilage_breakdown_kg: { handling_loss: number; delivered_unsold_expired: number; origin_expired: number }
  economics_inr: {
    gross_revenue_at_list: number; discount_cost: number; revenue: number
    cost_of_goods_sold: number
    transport: number; handling: number; spoilage_cost: number; net: number
  }
  volumes_kg: {
    total_supply: number; shipped: number; unshipped: number; sold: number
    carryover: { destination: number; origin: number; total: number }
  }
  trips: { count: number; avg_utilization_pct: number }
  per_destination: { dest_id: string; fill_pct: number; sold_kg: number; spoiled_kg: number }[]
  per_commodity: { commodity: string; spoilage_kg: number; spoilage_pct: number; sold_kg: number }[]
}

export interface Baseline { policy: string; kpis: Kpis; source: 'ladder' | 'run' }

export interface Validation { // §5.8
  schema_version: number
  violation_total: number
  counts: Record<string, number>
  violations: { code: string; shipment_id: string; detail: string; observed: number; limit: number }[]
  warnings: { code: string; detail: string }[]
}

export interface Manifest { // §5.1
  schema_version: number
  run_id: string; git_sha: string; scenario: string; scenario_sha256: string; policy: string
  flags: Flags; seed: number; realization: string
  package_versions: Record<string, string>
  solver: {
    status: string; mip_gap: number; solve_seconds: number
    fallback_used: boolean; slack_usage: Record<string, number>
  } | null
  timestamp_utc: string
}

export interface RunDetail extends Metrics {
  baseline: Baseline | null
  validation: Validation | null
  manifest: Manifest | null
  fixture?: boolean
}

export type TableName = 'plan' | 'trips' | 'discounts' | 'sim_ledger' | 'sim_lots'
export interface Table { columns: string[]; records: Record<string, string | number | boolean | null>[] }

export type ReasonCode = 'SHELF_LIFE' | 'WINDOW' | 'CAPACITY_BOUND' | 'DEMAND_CAP' | 'LOWER_MARGIN'
export interface ReasonCard { // §5.9, one per plan.csv shipment_id
  shipment_id: string; batch_id: string; commodity: string
  chosen: {
    dest_id: string; vehicle_id: string; mode: string; dispatch_h: number; arrival_h: number
    kg: number; usable_life_at_arrival_h: number; slack_h: number; margin_inr_kg: number
  }
  priority: { rank: number; score: number }
  alternatives: {
    dest_id: string; mode: string; dispatch_day: number; feasible: boolean; reject_reason: string
    usable_life_at_arrival_h: number; slack_h: number; margin_inr_kg: number
    margin_delta_inr_kg: number; slack_delta_h: number; reason_code: ReasonCode
  }[]
  runner_up: {
    dest_id: string; reason_code: ReasonCode
    margin_delta_inr_kg: number; margin_delta_inr: number; slack_delta_h: number
  } | null
  discount: { day: number; risk: number; tier_pct: number; capped_by: 'none' | 'max_discount' | 'salvage_floor' } | null
  text: string
}
export type ReasonCards = ReasonCard[] | null

export interface DispatchRow { // §5.10 CSV columns, served in priority_rank order
  vehicle_id: string; trip_id: string; dispatch_h: number; depart_clock: string
  dest_id: string; dest_name: string; batch_id: string; commodity: string; kg: number
  priority_rank: number; slack_h: number; arrive_by_h: number; note: string | null
}
export interface DispatchSheet { csv: DispatchRow[]; text: string } // §5.10

export interface LadderEntry { policy: string; kpis: Kpis }
export interface Ladder { // §5.11
  ladder: {
    scenario: string; seed: number; realization: string
    official_baseline: LadderEntry | null
    ladder: LadderEntry[]; extras: LadderEntry[]
  }
  waterfall: {
    baseline: string; plan: string; tolerance_inr: number
    steps: { label: string; value: number; type: 'total' | 'delta' }[]
  }
}

export interface Flags { markdown: boolean; newsvendor: boolean }
export interface PostRunRequest { scenario: string; policy: string; seed: number; flags: Flags }
export interface PostRunResponse { run_id: string; status: 'running' }

/** Live solve progress (DATABASE §11.3): each version is a complete run directory on disk. */
export interface Progress { version: number; net_inr: number; final: boolean; elapsed_s: number }
export interface StatusResponse {
  state: 'running' | 'done' | 'error'
  progress?: Progress | null
  started_utc: string | null; finished_utc: string | null; error: string | null
}

// ---- Robustness and Replan (DATABASE §5.12, §5.13, §6; endpoints per §11.2 "added later") ----
/** Client-only marker set by the format-example stub in api/client.ts; never sent by the API. */
export type Example = { example?: true }

export interface Band { p10: number; p50: number; p90: number }
export type StressKpi = 'net_inr' | 'spoilage_kg' | 'demand_fulfillment_pct'
export interface StressSummary { // §5.12 stress_summary.json
  n: number; base_seed: number; plan: string; baseline: string
  bands: Record<StressKpi, { plan: Band; baseline: Band }>
  share_plan_beats_baseline: { net_inr: number; spoilage_kg: number } // 0–1, paired
}
export interface StressRow { // §5.12 stress.csv
  scenario_i: number; policy: string; spoilage_kg: number; spoilage_pct: number
  demand_fulfillment_pct: number; min_dest_fill_pct: number; net_inr: number
}
export interface StressResponse extends Example { summary: StressSummary; rows: StressRow[] | null }
export interface PostStressRequest { scenario: string; policy: string; seed: number; n: number }

export interface SensitivityRow { // §5.12 sensitivity.csv
  parameter: string // q10 | elasticity_multiplier | overship_slack | demand_multiplier
  value: number; policy: string; net_inr: number; spoilage_kg: number; demand_fulfillment_pct: number
}
export interface SensitivityResponse extends Example { records: SensitivityRow[] }

export interface FrontierRow { // §5.12 frontier.csv, one row per spoilage weight
  lambda_spoil: number; net_inr: number; spoilage_kg: number; demand_fulfillment_pct: number; min_dest_fill_pct: number
}
export interface FrontierResponse { records: FrontierRow[] }

export type EventType = 'route_delay' | 'capacity_drop' | 'demand_spike' | 'new_order' | 'price_shock'
export interface ReplanEvent { // §6
  event_id: string; type: EventType; target: string; magnitude: number; at_h: number; note?: string
}
export interface PostReplanRequest { run_id: string; event: ReplanEvent }
export interface PostReplanResponse { run_id: string; event_id: string; status: 'running' }

export type ReplanKpis = Partial<Pick<Kpis, 'spoilage_kg' | 'demand_fulfillment_pct' | 'net_inr'>>
export interface Diff { // §5.13 diff.json
  event_id: string; at_h: number; frozen_shipments: number
  moved_batches: { batch_id: string; from: { dest_id: string | null; dispatch_day: number | null }
    to: { dest_id: string | null; dispatch_day: number | null }; kg: number }[]
  discount_changes: { lot_id: string; day: number; from_pct: number; to_pct: number }[]
  kpis_old_plan_under_event: ReplanKpis; kpis_replanned: ReplanKpis; delta_kpis: ReplanKpis
  solve_seconds: number
}
export interface ReplanResult extends Example {
  diff: Diff; narration: string
  trips?: { origin: string; dest_id: string; trip_id: string; dispatch_h: number }[] // replanned trips.csv records
}

/** Props every dashboard tab receives. */
export type TabProps = { run: RunDetail; runId: string }
