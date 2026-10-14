// Attribution ladder (ARCHITECTURE §16, DATABASE §5.11 ladder.json) + waterfall, from GET /api/ladder.
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { fmt } from '../lib/delta'
import type { Ladder as LadderData, LadderEntry } from '../types'
import { Waterfall } from './Waterfall'

export function LadderCharts({ scenario, seed }: { scenario: string; seed: number }) {
  const [data, setData] = useState<LadderData | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setData(null); setError('')
    api.ladder(scenario, seed).then(setData).catch(e => setError(e instanceof Error ? e.message : String(e)))
  }, [scenario, seed])

  if (error) return <p className="placeholder">No ladder on disk — run <code>freshroute ladder --scenario data/scenarios/{scenario} --seed {seed}</code> ({error}).</p>
  if (!data) return <p className="placeholder">Loading ladder…</p>
  return (
    <>
      {data.waterfall && <Waterfall waterfall={data.waterfall} />}
      <Ladder ladder={data.ladder} />
    </>
  )
}

function Ladder({ ladder }: { ladder: LadderData['ladder'] }) {
  const rows: (LadderEntry & { group: string })[] = [
    ...(ladder.official_baseline ? [{ ...ladder.official_baseline, group: 'official baseline' }] : []),
    ...ladder.ladder.map(e => ({ ...e, group: 'ladder' })),
    ...ladder.extras.map(e => ({ ...e, group: 'extra' })),
  ]
  const chart = rows.map(r => ({ policy: r.policy, net_inr: r.kpis.net_inr }))
  return (
    <section>
      <h3>Attribution ladder</h3>
      <p className="caption">scenario {ladder.scenario} · seed {ladder.seed} · realization {ladder.realization}</p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chart} margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="policy" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={v => `₹${fmt(v)}`} width={90} />
          <ReferenceLine y={0} stroke="var(--border)" />
          <Tooltip formatter={v => [`₹${fmt(Number(v))}`, 'net']} />
          <Bar dataKey="net_inr" isAnimationActive={false}>
            {chart.map(c => <Cell key={c.policy} fill={c.net_inr >= 0 ? 'var(--good)' : 'var(--bad)'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <table>
        <thead><tr><th>policy</th><th>role</th><th>spoilage kg</th><th>spoilage %</th><th>fill %</th>
          <th>min dest fill %</th><th>net ₹</th><th>violations</th></tr></thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.policy}>
              <td>{r.policy}</td><td>{r.group}</td><td>{fmt(r.kpis.spoilage_kg)}</td><td>{fmt(r.kpis.spoilage_pct, 1)}</td>
              <td>{fmt(r.kpis.demand_fulfillment_pct, 1)}</td><td>{fmt(r.kpis.min_dest_fill_pct, 1)}</td>
              <td>{fmt(r.kpis.net_inr)}</td><td>{r.kpis.violations}</td>
            </tr>))}
        </tbody>
      </table>
    </section>
  )
}
