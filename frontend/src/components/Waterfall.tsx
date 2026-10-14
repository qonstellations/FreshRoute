// Net reconciling waterfall (ARCHITECTURE §12/§16, DATABASE §5.11 waterfall.json). Steps drawn as given.
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt, fmtSigned, waterfallBars } from '../lib/delta'
import type { Ladder } from '../types'

const colour = (s: { type: string; value: number }) =>
  s.type === 'total' ? 'var(--muted)' : s.value >= 0 ? 'var(--good)' : 'var(--bad)'

export function Waterfall({ waterfall }: { waterfall: Ladder['waterfall'] }) {
  const { bars: data, floor } = waterfallBars(waterfall.steps)
  return (
    <section>
      <h3>Net waterfall: {waterfall.baseline} → {waterfall.plan}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" interval={0} tick={{ fontSize: 11 }} />
          <YAxis domain={[floor, 'auto']} allowDataOverflow tickFormatter={v => `₹${fmt(v)}`} width={90} />
          <ReferenceLine y={0} stroke="var(--border)" />
          <Tooltip formatter={(_, __, item) => {
            const s = item.payload as (typeof data)[number]
            return [s.type === 'total' ? `₹${fmt(s.value)}` : fmtSigned(s.value, 0, ' ₹'), s.label]
          }} />
          <Bar dataKey="range" isAnimationActive={false}>
            {data.map(s => <Cell key={s.label} fill={colour(s)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="caption">
        Step values from waterfall.json (tolerance ₹{waterfall.tolerance_inr}); bar placement only is computed in the UI.
        {floor !== 0 && ` Axis starts at ₹${fmt(floor)}, not 0, so the deltas are visible.`}
      </p>
    </section>
  )
}
