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

export interface StatusResponse {
  state: 'running' | 'done' | 'error'
  started_utc: string | null; finished_utc: string | null; error: string | null
}
