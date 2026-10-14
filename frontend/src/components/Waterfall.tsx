// Net reconciling waterfall (ARCHITECTURE §12/§16, DATABASE §5.11 waterfall.json). Steps drawn as given.
import { Paper, Text, Title } from '@mantine/core'
import { m, useReducedMotion } from 'motion/react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmt, fmtSigned, waterfallBars } from '../lib/delta'
import { spring } from '../theme'
import type { Ladder } from '../types'

export const C = {
  good: 'var(--mantine-color-green-6)', bad: 'var(--mantine-color-red-6)', total: 'var(--mantine-color-blue-7)',
  grid: 'var(--mantine-color-gray-3)', axis: 'var(--mantine-color-gray-7)',
}
export const tooltipStyle = {
  contentStyle: { borderRadius: 10, border: '1px solid var(--mantine-color-gray-3)', boxShadow: '0 8px 24px rgb(0 0 0 / .12)', fontSize: 15 },
  labelStyle: { fontWeight: 700, marginBottom: 4 },
  cursor: { fill: 'var(--mantine-color-gray-1)' },
}

const colour = (s: { type: string; value: number }) => s.type === 'total' ? C.total : s.value >= 0 ? C.good : C.bad

// Each bar drops in after the previous one, like crates being stacked (transform + opacity only).
function Crate(p: { x?: number; y?: number; width?: number; height?: number; fill?: string; index?: number }) {
  const reduce = useReducedMotion()
  return (
    <m.rect x={p.x} y={p.y} width={p.width} height={Math.max(0, p.height ?? 0)} fill={p.fill} rx={4}
      initial={reduce ? false : { opacity: 0, y: -40 }} animate={{ opacity: 1, y: 0 }}
      transition={{ ...spring.bouncy, delay: 0.15 + 0.14 * (p.index ?? 0) }} />
  )
}

export function Waterfall({ waterfall }: { waterfall: Ladder['waterfall'] }) {
  const { bars: data, floor } = waterfallBars(waterfall.steps)
  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={3}>Net waterfall: {waterfall.baseline} → {waterfall.plan}</Title>
      <Text size="sm" c="dimmed" mb="sm">Where the extra net comes from, step by step (waterfall.json).</Text>
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={data} margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={C.grid} />
          <XAxis dataKey="label" interval={0} height={58} tick={{ fontSize: 13, fill: C.axis, width: 100 }} />
          <YAxis domain={[floor, 'auto']} allowDataOverflow tickFormatter={v => `₹${fmt(v)}`} width={100}
            tick={{ fontSize: 13, fill: C.axis }} />
          <ReferenceLine y={0} stroke={C.axis} />
          <Tooltip {...tooltipStyle} formatter={(_, __, item) => {
            const s = item.payload as (typeof data)[number]
            return [s.type === 'total' ? `₹${fmt(s.value)}` : fmtSigned(s.value, 0, ' ₹'), s.label]
          }} />
          <Bar dataKey="range" isAnimationActive={false} shape={(p: object) => <Crate {...p} />}>
            {data.map(s => <Cell key={s.label} fill={colour(s)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <Text size="sm" c="dimmed">
        Step values from waterfall.json (tolerance ₹{waterfall.tolerance_inr}); bar placement only is computed in the UI.
        {floor !== 0 && ` Axis starts at ₹${fmt(floor)}, not 0, so the deltas are visible.`}
      </Text>
    </Paper>
  )
}
