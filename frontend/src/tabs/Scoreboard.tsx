// Scoreboard tab (ARCHITECTURE §16; port of C-12). Shows stored KPIs; deltas via lib/delta.ts only.
import { KpiTile, toneOf } from '../components/KpiTile'
import { LadderCharts } from '../components/Ladder'
import { ValidatorPanel } from '../components/ValidatorPanel'
import { delta, fmt, fmtSigned } from '../lib/delta'
import type { Kpis, RunDetail } from '../types'

export function Scoreboard({ run }: { run: RunDetail }) {
  const k = run.kpis
  const base = run.fixture ? null : run.baseline
  const bk = base?.kpis
  const tile = (key: keyof Kpis, digits: number, unit: string, lowerIsBetter = false) => {
    const d = delta(k[key], bk?.[key])
    return { delta: d == null ? null : fmtSigned(d, digits, unit), tone: toneOf(d, lowerIsBetter) }
  }

  return (
    <>
      <div className="tiles">
        <KpiTile label="Spoilage" value={`${fmt(k.spoilage_kg)} kg (${fmt(k.spoilage_pct, 1)}%)`}
          {...tile('spoilage_kg', 0, ' kg', true)} />
        <KpiTile label="Demand fulfillment" value={`${fmt(k.demand_fulfillment_pct, 1)}%`}
          {...tile('demand_fulfillment_pct', 1, ' pp')} />
        <KpiTile label="Net" value={`₹${fmt(k.net_inr)}`} {...tile('net_inr', 0, ' ₹')} />
        <KpiTile label="Violations"
          value={bk ? `baseline ${bk.violations} vs ours ${k.violations}` : String(k.violations)} />
      </div>
      <p className="caption">
        run {run.run_id} · scenario {run.scenario} · policy {run.policy} · seed {run.seed}
        {base ? ` · deltas vs ${base.policy} (${base.source})` : ' · no baseline on disk'}
      </p>
      <div className="tiles">
        <KpiTile label="Min destination fill" value={`${fmt(k.min_dest_fill_pct, 1)}%`}
          {...tile('min_dest_fill_pct', 1, ' pp')} />
      </div>
      <LadderCharts scenario={run.scenario} seed={run.seed} />
      <ValidatorPanel validation={run.validation} />
    </>
  )
}
