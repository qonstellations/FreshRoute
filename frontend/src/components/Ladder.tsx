// Attribution ladder (ARCHITECTURE §16, DATABASE §5.11 ladder.json) + waterfall, from GET /api/ladder.
import { Badge, Paper, Skeleton, Stack, Table, Text, ThemeIcon, Title } from '@mantine/core'
import { IconStairsUp } from '@tabler/icons-react'
import { useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { fmt } from '../lib/delta'
import { policyName } from '../lib/words'
import type { Ladder as LadderData, LadderEntry } from '../types'
import { Explain } from './Explain'
import { C, tooltipStyle, Waterfall } from './Waterfall'

const OURS = 'milp' // highlighted by name, not by comparing numbers

export function LadderCharts({ scenario, seed }: { scenario: string; seed: number }) {
  const [data, setData] = useState<LadderData | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setData(null); setError('')
    api.ladder(scenario, seed).then(setData).catch(e => setError(e instanceof Error ? e.message : String(e)))
  }, [scenario, seed])

  if (error) return (
    <Paper withBorder radius="lg" p="xl">
      <Stack align="center" gap="xs">
        <ThemeIcon size={48} radius="xl" variant="light" color="gray"><IconStairsUp size={28} /></ThemeIcon>
        <Text fw={600}>No comparison saved yet</Text>
        <Text size="sm" c="dimmed">
          The rule-by-rule comparison has not been run for this scenario.{' '}
          <Explain note={`For developers: freshroute ladder --scenario data/scenarios/${scenario} --seed ${seed} (${error})`}>
            How to create it</Explain>
        </Text>
      </Stack>
    </Paper>
  )
  if (!data) return <Stack><Skeleton h={400} radius="lg" /><Skeleton h={300} radius="lg" /></Stack>
  return (
    <>
      {data.waterfall && <Waterfall waterfall={data.waterfall} />}
      <Ladder ladder={data.ladder} />
    </>
  )
}

function Ladder({ ladder }: { ladder: LadderData['ladder'] }) {
  const reduce = useReducedMotion()
  const rows: (LadderEntry & { group: string })[] = [
    ...(ladder.official_baseline ? [{ ...ladder.official_baseline, group: 'baseline' }] : []),
    ...ladder.ladder.map(e => ({ ...e, group: 'compared' })),
    ...ladder.extras.map(e => ({ ...e, group: 'extra' })),
  ]
  const chart = rows.map(r => ({ policy: r.policy, net_inr: r.kpis.net_inr }))
  const fill = (c: (typeof chart)[number]) =>
    c.policy === OURS ? C.good : c.net_inr >= 0 ? 'var(--mantine-color-gray-5)' : C.bad
  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={3}>Every rule vs FreshRoute, scored the same way</Title>
      <Text size="sm" c="dimmed" mb="sm">
        How to read this: each bar is one way of planning, and taller means more profit after all costs. Green is
        FreshRoute; red bars lose money. Every plan faces the same days and is scored by{' '}
        <Explain term="simulator">the same simulator</Explain>.{' '}
        <Explain note={`scenario ${ladder.scenario} · seed ${ladder.seed} · realization ${ladder.realization}`}>Details</Explain>
      </Text>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chart} margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={C.grid} />
          <XAxis dataKey="policy" tickFormatter={policyName} tick={{ fontSize: 13, fill: C.axis }} />
          <YAxis tickFormatter={v => `₹${fmt(v)}`} width={100} tick={{ fontSize: 13, fill: C.axis }} />
          <ReferenceLine y={0} stroke={C.axis} />
          <Tooltip {...tooltipStyle} formatter={v => [`₹${fmt(Number(v))}`, 'profit']} labelFormatter={l => policyName(String(l))} />
          <Bar dataKey="net_inr" radius={[6, 6, 0, 0]} isAnimationActive={!reduce} animationDuration={900}
            animationEasing="ease-out">
            {chart.map(c => <Cell key={c.policy} fill={fill(c)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <Table.ScrollContainer minWidth={760} mt="md">
        <Table striped highlightOnHover verticalSpacing="sm" fz="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Plan</Table.Th><Table.Th>Type</Table.Th><Table.Th ta="right">Spoiled kg</Table.Th>
              <Table.Th ta="right">Spoiled %</Table.Th><Table.Th ta="right">Orders filled %</Table.Th>
              <Table.Th ta="right">Worst market filled %</Table.Th><Table.Th ta="right">Profit ₹</Table.Th>
              <Table.Th ta="right">Rule breaks</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody className="num">
            {rows.map(r => {
              const ours = r.policy === OURS
              return (
                <Table.Tr key={r.policy} bg={ours ? 'var(--mantine-color-green-0)' : undefined} fw={ours ? 700 : undefined}>
                  <Table.Td>{policyName(r.policy)} {ours && <Badge size="sm" ml={6}>ours</Badge>}</Table.Td>
                  <Table.Td c="dimmed">{r.group}</Table.Td>
                  <Table.Td ta="right">{fmt(r.kpis.spoilage_kg)}</Table.Td>
                  <Table.Td ta="right">{fmt(r.kpis.spoilage_pct, 1)}</Table.Td>
                  <Table.Td ta="right">{fmt(r.kpis.demand_fulfillment_pct, 1)}</Table.Td>
                  <Table.Td ta="right">{fmt(r.kpis.min_dest_fill_pct, 1)}</Table.Td>
                  <Table.Td ta="right">{fmt(r.kpis.net_inr)}</Table.Td>
                  <Table.Td ta="right">{r.kpis.violations}</Table.Td>
                </Table.Tr>)
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Paper>
  )
}
