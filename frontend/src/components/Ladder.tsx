// Attribution ladder (ARCHITECTURE §16, DATABASE §5.11 ladder.json) + waterfall, from GET /api/ladder.
import { Badge, Code, Paper, Skeleton, Stack, Table, Text, ThemeIcon, Title } from '@mantine/core'
import { IconStairsUp } from '@tabler/icons-react'
import { AnimatePresence, m, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api/client'
import { fmt } from '../lib/delta'
import type { Ladder as LadderData, LadderEntry } from '../types'
import { spring } from '../theme'
import { Reveal } from './score/Reveal'
import { C, tooltipStyle, Waterfall } from './Waterfall'

const OURS = 'milp_markdown' // highlighted by name, not by comparing numbers
// Story order (Scoreboard steps 2..6 reveal one each); captions are static copy, never numbers.
const STORY = ['fifo', 'fefo', 'last_day_50', 'milp', 'milp_markdown']
const CAPTION: Record<string, string> = {
  fifo: 'first in, first out', fefo: 'first expiry first out (baseline)', last_day_50: '50 % off on the last day',
  milp: '+ optimisation (HiGHS MILP)', milp_markdown: '+ markdown pricing',
}
const storyIdx = (p: string) => { const i = STORY.indexOf(p); return i < 0 ? STORY.length : i }

/** Bar that springs up from the zero line; opacity/visibility driven by the story step. */
function StoryBar(p: { x?: number; y?: number; width?: number; height?: number; fill?: string; value?: number
  shown: boolean; opacity: number }) {
  return (
    <m.rect x={p.x} y={p.y} width={p.width} height={Math.max(0, p.height ?? 0)} fill={p.fill} rx={4}
      style={{ originY: (p.value ?? 0) < 0 ? 0 : 1 }} initial={{ scaleY: 0, opacity: 0 }}
      animate={{ scaleY: p.shown ? 1 : 0, opacity: p.shown ? p.opacity : 0 }} transition={spring.bouncy} />
  )
}

export function LadderCharts({ scenario, seed, step }: { scenario: string; seed: number; step?: number }) {
  const [data, setData] = useState<LadderData | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setData(null); setError('')
    api.ladder(scenario, seed).then(setData).catch(e => setError(e instanceof Error ? e.message : String(e)))
  }, [scenario, seed])
  const endRef = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()
  useEffect(() => { // story beat 7: bring the waterfall (and the validator below it) on screen
    if (step != null && step >= 7) endRef.current?.scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' })
  }, [step, reduce, data])

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
  if (step == null) return (
    <>
      {data.waterfall && <Waterfall waterfall={data.waterfall} />}
      <Ladder ladder={data.ladder} />
    </>
  )
  // story mode: ladder first (steps 2..6), waterfall collapsed below it until step 7
  return (
    <>
      <Ladder ladder={data.ladder} step={step} />
      <div ref={endRef} className="story-anchor">
        <Reveal show={step >= 7} collapse>{data.waterfall && <Waterfall waterfall={data.waterfall} />}</Reveal>
      </div>
    </>
  )
}

function Ladder({ ladder, step }: { ladder: LadderData['ladder']; step?: number }) {
  const reduce = useReducedMotion()
  const rows: (LadderEntry & { group: string })[] = [
    ...(ladder.official_baseline ? [{ ...ladder.official_baseline, group: 'official baseline' }] : []),
    ...ladder.ladder.map(e => ({ ...e, group: 'ladder' })),
    ...ladder.extras.map(e => ({ ...e, group: 'extra' })),
  ]
  // story mode: story order left to right; bar i shows once step >= i + 2; policies outside STORY show at step 7
  if (step != null) rows.sort((a, b) => storyIdx(a.policy) - storyIdx(b.policy)) // stable sort
  const newest = step != null && step >= 2 && step <= 6 ? STORY[step - 2] : null
  const shown = (policy: string) => step == null || step >= storyIdx(policy) + 2
  const barOpacity = (policy: string) => newest && policy !== newest ? 0.4 : 1
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
          {step == null
            ? <Bar dataKey="net_inr" radius={[6, 6, 0, 0]} isAnimationActive={!reduce} animationDuration={900}
              animationEasing="ease-out">
              {chart.map(c => <Cell key={c.policy} fill={fill(c)} />)}
            </Bar>
            : <Bar dataKey="net_inr" isAnimationActive={false} shape={(p: { index?: number }) => {
              const c = chart[p.index ?? 0]
              return <StoryBar {...p} value={c.net_inr} shown={shown(c.policy)} opacity={barOpacity(c.policy)} />
            }}>
              {chart.map(c => <Cell key={c.policy} fill={fill(c)} />)}
            </Bar>}
        </BarChart>
      </ResponsiveContainer>
      {step != null && (
        <Text ta="center" fz={22} fw={700} h={34} c="green.8">
          <AnimatePresence mode="wait">
            {newest && <m.span key={newest} style={{ display: 'inline-block' }} initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={spring.snappy}>
              {newest}: {CAPTION[newest]}
            </m.span>}
          </AnimatePresence>
        </Text>
      )}
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
                <Table.Tr key={r.policy} bg={ours ? 'var(--mantine-color-green-0)' : undefined} fw={ours ? 700 : undefined}
                  className={step == null ? undefined : 'story-row'} data-hidden={!shown(r.policy) || undefined}>
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
