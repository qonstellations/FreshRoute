// Attribution ladder (ARCHITECTURE §16, DATABASE §5.11 ladder.json) + waterfall, from GET /api/ladder.
import { Badge, Code, Paper, Skeleton, Stack, Table, Text, ThemeIcon, Title } from '@mantine/core'
import { IconStairsUp } from '@tabler/icons-react'
import { useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { fmt } from '../lib/delta'
import type { Ladder as LadderData, LadderEntry } from '../types'
import { C, tooltipStyle, Waterfall } from './Waterfall'

const OURS = 'milp_markdown' // highlighted by name, not by comparing numbers

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
        <Text fw={600}>No ladder on disk</Text>
        <Text size="sm" c="dimmed">Run <Code>freshroute ladder --scenario data/scenarios/{scenario} --seed {seed}</Code> ({error})</Text>
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
    ...(ladder.official_baseline ? [{ ...ladder.official_baseline, group: 'official baseline' }] : []),
    ...ladder.ladder.map(e => ({ ...e, group: 'ladder' })),
    ...ladder.extras.map(e => ({ ...e, group: 'extra' })),
  ]
  const chart = rows.map(r => ({ policy: r.policy, net_inr: r.kpis.net_inr }))
  const fill = (c: (typeof chart)[number]) =>
    c.policy === OURS ? C.good : c.net_inr >= 0 ? 'var(--mantine-color-gray-5)' : C.bad
  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={3}>Attribution ladder</Title>
      <Text size="sm" c="dimmed" mb="sm">
        Net ₹ per policy, all scored by the same simulator · scenario {ladder.scenario} · seed {ladder.seed} · realization {ladder.realization}
      </Text>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chart} margin={{ top: 8, right: 16, left: 16, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={C.grid} />
          <XAxis dataKey="policy" tick={{ fontSize: 13, fill: C.axis }} />
          <YAxis tickFormatter={v => `₹${fmt(v)}`} width={100} tick={{ fontSize: 13, fill: C.axis }} />
          <ReferenceLine y={0} stroke={C.axis} />
          <Tooltip {...tooltipStyle} formatter={v => [`₹${fmt(Number(v))}`, 'net']} />
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
              <Table.Th>policy</Table.Th><Table.Th>role</Table.Th><Table.Th ta="right">spoilage kg</Table.Th>
              <Table.Th ta="right">spoilage %</Table.Th><Table.Th ta="right">fill %</Table.Th>
              <Table.Th ta="right">min dest fill %</Table.Th><Table.Th ta="right">net ₹</Table.Th>
              <Table.Th ta="right">violations</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody className="num">
            {rows.map(r => {
              const ours = r.policy === OURS
              return (
                <Table.Tr key={r.policy} bg={ours ? 'var(--mantine-color-green-0)' : undefined} fw={ours ? 700 : undefined}>
                  <Table.Td>{r.policy} {ours && <Badge size="sm" ml={6}>ours</Badge>}</Table.Td>
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
