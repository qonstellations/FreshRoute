// Robustness tab (ARCHITECTURE §14.1, §16; DATABASE §5.12): stress bands plan vs baseline, the served share of
// futures where the plan beats the baseline, and the sensitivity table. Every number is a served field, only rounded.
// `step` (story mode): 0 hero + futures matrix · 1 + bands · 2 + sensitivity. undefined = everything.
import { Alert, Badge, Button, Code, Group, Paper, SimpleGrid, Skeleton, Slider, Stack, Table, Text, ThemeIcon, Title } from '@mantine/core'
import { IconAlertTriangle, IconChartDots3, IconPlayerPlayFilled, IconShieldCheck } from '@tabler/icons-react'
import { m, useReducedMotion, type Variants } from 'motion/react'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceDot, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import { api, notOnDisk, waitDone } from '../api/client'
import { ExampleBanner } from '../components/Banners'
import { Odometer } from '../components/KpiTile'
import { Reveal } from '../components/score/Reveal'
import { C } from '../components/Waterfall'
import { dotsWon, fmt, fmtShare } from '../lib/delta'
import type { TabProps } from '../lib/story'
import { spring } from '../theme'
import type { Band, SensitivityResponse, SensitivityRow, StressKpi, StressResponse } from '../types'

// ponytail: N of ARCHITECTURE §14.1, sent with POST /api/stress; the CLI owns the real default
const STRESS_N = 200
const scenarioDir = (s: string) => (s.includes('/') || s.includes('\\') ? s : `data/scenarios/${s}`)

/** undefined = loading · null = 404 (not on disk) · value = served. */
type Load<T> = T | null | undefined

function useServed<T>(fetcher: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<Load<T>>(undefined)
  const [error, setError] = useState('')
  const load = useCallback(() => {
    setData(undefined); setError('')
    fetcher().then(setData).catch(e => (notOnDisk(e) ? setData(null) : setError(e instanceof Error ? e.message : String(e))))
  }, deps)
  useEffect(load, [load])
  return { data, error, reload: load }
}

export function Robustness({ run, step }: TabProps) {
  const at = (s: number) => step == null || step >= s
  const stress = useServed(() => api.stress(run.scenario, run.seed), [run.scenario, run.seed])
  const sens = useServed(() => api.sensitivity(run.scenario, run.seed), [run.scenario, run.seed])
  const reduce = useReducedMotion()
  const bandsRef = useRef<HTMLDivElement>(null), sensRef = useRef<HTMLDivElement>(null)
  useEffect(() => { // keep the current beat on the projector
    if (step == null) return
    const behavior = reduce ? 'auto' : 'smooth'
    if (step === 0) { window.scrollTo({ top: 0, behavior }); return } // never return it: Chromium's scrollTo returns a Promise
    const t = setTimeout(() => (step === 1 ? bandsRef : sensRef).current?.scrollIntoView({ block: 'start', behavior }), 250)
    return () => clearTimeout(t)
  }, [step, reduce])

  const s = stress.data
  return (
    <Stack gap="lg">
      <ExampleBanner show={!!(s?.example || sens.data?.example)} what="stress / sensitivity" />
      {stress.error && <Alert color="red" icon={<IconAlertTriangle />} title="Cannot load stress test">{stress.error}</Alert>}
      {s === undefined && !stress.error && <><Skeleton h={220} radius="lg" /><Skeleton h={300} radius="lg" /></>}
      {s === null && <StressEmpty scenario={run.scenario} policy={run.policy} seed={run.seed} onDone={stress.reload} />}
      {s && <>
        <Hero s={s} />
        <div ref={bandsRef} className="story-anchor">
          <Reveal show={at(1)} collapse={step != null}><Bands s={s} /></Reveal>
        </div>
      </>}
      <div ref={sensRef} className="story-anchor">
        <Reveal show={at(2)} collapse={step != null}>
          <Sensitivity load={sens.data} error={sens.error} scenario={run.scenario} seed={run.seed} />
        </Reveal>
      </div>
    </Stack>
  )
}

function Hint({ icon, title, cmd, children }: { icon: ReactNode; title: string; cmd: string; children?: ReactNode }) {
  return (
    <Paper withBorder radius="lg" p="xl">
      <Stack align="center" gap="xs">
        <ThemeIcon size={48} radius="xl" variant="light" color="gray">{icon}</ThemeIcon>
        <Text fw={600}>{title}</Text>
        <Text size="sm" c="dimmed" ta="center">Run <Code>{cmd}</Code></Text>
        {children}
      </Stack>
    </Paper>
  )
}

function StressEmpty({ scenario, policy, seed, onDone }: { scenario: string; policy: string; seed: number; onDone: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const start = async () => {
    setBusy(true); setError('')
    try {
      const { run_id } = await api.postStress({ scenario: scenarioDir(scenario), policy, seed, n: STRESS_N })
      await waitDone(run_id)
      onDone()
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }
  return (
    <Hint icon={<IconChartDots3 size={28} />} title="No stress test on disk for this scenario and seed"
      cmd={`freshroute stress --scenario ${scenarioDir(scenario)} --policy ${policy} --n ${STRESS_N} --seed ${seed}`}>
      <Button mt="xs" radius="xl" leftSection={<IconPlayerPlayFilled size={16} />} loading={busy} onClick={start}>
        Run stress test</Button>
      {error && <Text c="red" size="sm">{error}</Text>}
    </Hint>
  )
}

// ---------- hero + futures dot matrix ----------
const matrix: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.006 } } }
const dot: Variants = { hidden: { opacity: 0, scale: 0 }, show: { opacity: 1, scale: 1, transition: spring.bouncy } }

function Hero({ s }: { s: StressResponse }) {
  const { n, plan, baseline, base_seed, share_plan_beats_baseline: share } = s.summary
  const won = dotsWon(share.net_inr, n)
  const reduce = useReducedMotion()
  return (
    <Paper radius="lg" p="xl" className="hero">
      <Group gap="lg" wrap="nowrap" align="flex-start">
        <ThemeIcon size={64} radius="xl" variant="white" color="green"><IconShieldCheck size={38} /></ThemeIcon>
        <div>
          <Text fz={40} fw={800} lh={1.1} c="white">
            {plan} beats {baseline} in <Odometer text={fmtShare(share.net_inr)} /> of {fmt(n)} futures
          </Text>
          <Text fz="lg" c="white" opacity={0.85} mt={6}>
            on net ₹ · on spoilage in {fmtShare(share.spoilage_kg)} · paired futures (same sampled demand, travel time
            and shelf life for both), seeds {base_seed}+i
          </Text>
        </div>
      </Group>
      {/* one dot per sampled future; how many are green is the served share, the order is cosmetic */}
      <m.div className="futures" variants={matrix} initial={reduce ? false : 'hidden'} animate="show" aria-hidden>
        {Array.from({ length: n }, (_, i) => <m.span key={i} className="future" data-won={i < won || undefined} variants={dot} />)}
      </m.div>
      <Group gap="lg" mt="xs">
        <Text size="sm" c="white"><span className="future" data-won /> {plan} ahead on net ₹</Text>
        <Text size="sm" c="white"><span className="future" /> {baseline} ahead or tied</Text>
      </Group>
    </Paper>
  )
}

// ---------- P10–P50–P90 bands ----------
const BAND_META: Record<StressKpi, { title: string; unit: (v: number) => string }> = {
  net_inr: { title: 'Net ₹', unit: v => `₹${fmt(v)}` },
  spoilage_kg: { title: 'Spoilage', unit: v => `${fmt(v)} kg` },
  demand_fulfillment_pct: { title: 'Demand fulfilment', unit: v => `${fmt(v, 1)}%` },
}

function MedianTick(p: { cx?: number; cy?: number; fill?: string }) {
  return <rect x={(p.cx ?? 0) - 2.5} y={(p.cy ?? 0) - 20} width={5} height={40} rx={2.5} fill={p.fill} />
}

function BandChart({ kpi, s, height }: { kpi: StressKpi; s: StressResponse; height: number }) {
  const reduce = useReducedMotion()
  const { plan, baseline, bands } = s.summary
  const meta = BAND_META[kpi]
  const rows: { name: string; band: Band; colour: string }[] = [
    { name: baseline, band: bands[kpi].baseline, colour: 'var(--mantine-color-gray-6)' },
    { name: plan, band: bands[kpi].plan, colour: C.good },
  ]
  const data = rows.map(r => ({ name: r.name, range: [r.band.p10, r.band.p90] }))
  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={4}>{meta.title}</Title>
      <Text size="sm" c="dimmed">P10 to P90 band, bar = P50, over {fmt(s.summary.n)} paired futures</Text>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--mantine-color-default-border)" />
          <XAxis type="number" domain={['auto', 'auto']} padding={{ left: 16, right: 16 }} tickFormatter={meta.unit}
            tick={{ fontSize: 12, fill: 'var(--mantine-color-dimmed)' }} />
          <YAxis type="category" dataKey="name" width={112} tick={{ fontSize: 13, fill: 'var(--mantine-color-text)', fontWeight: 600 }} />
          <Bar dataKey="range" barSize={30} radius={15} isAnimationActive={!reduce} animationDuration={900}>
            {rows.map(r => <Cell key={r.name} fill={r.colour} fillOpacity={0.35} stroke={r.colour} />)}
          </Bar>
          {rows.map(r => <ReferenceDot key={r.name} x={r.band.p50} y={r.name} r={0} fill={r.colour}
            shape={MedianTick} ifOverflow="extendDomain" />)}
        </BarChart>
      </ResponsiveContainer>
      <Table fz="sm" verticalSpacing={4} mt={4} className="num">
        <Table.Thead><Table.Tr><Table.Th /><Table.Th ta="right">P10</Table.Th><Table.Th ta="right">P50</Table.Th>
          <Table.Th ta="right">P90</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>
          {[...rows].reverse().map(r => (
            <Table.Tr key={r.name} fw={r.name === plan ? 700 : undefined}>
              <Table.Td>{r.name}</Table.Td><Table.Td ta="right">{meta.unit(r.band.p10)}</Table.Td>
              <Table.Td ta="right">{meta.unit(r.band.p50)}</Table.Td><Table.Td ta="right">{meta.unit(r.band.p90)}</Table.Td>
            </Table.Tr>))}
        </Table.Tbody>
      </Table>
    </Paper>
  )
}

function Bands({ s }: { s: StressResponse }) {
  return (
    <Stack gap="md">
      <BandChart kpi="net_inr" s={s} height={170} />
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <BandChart kpi="spoilage_kg" s={s} height={150} />
        <BandChart kpi="demand_fulfillment_pct" s={s} height={150} />
      </SimpleGrid>
    </Stack>
  )
}

// ---------- sensitivity ----------
const PARAM_LABEL: Record<string, string> = {
  q10: 'Q10 (spoilage vs temperature)', elasticity_multiplier: 'ε multiplier (price elasticity)',
  overship_slack: 'overship slack', demand_multiplier: 'demand multiplier',
}
const SLIDERS = ['q10', 'elasticity_multiplier'] // the two the pitch moves; the table shows every served row

function Sensitivity({ load, error, scenario, seed }: { load: Load<SensitivityResponse>; error: string; scenario: string; seed: number }) {
  const [pick, setPick] = useState<Record<string, number>>({}) // parameter -> row index within that parameter
  if (error) return <Alert color="red" icon={<IconAlertTriangle />} title="Cannot load sensitivity">{error}</Alert>
  if (load === undefined) return <Skeleton h={320} radius="lg" />
  if (load === null) return <Hint icon={<IconChartDots3 size={28} />} title="No sensitivity.csv for this scenario and seed"
    cmd={`freshroute sensitivity --scenario ${scenarioDir(scenario)} --seed ${seed}`} />
  const recs = load.records
  const params = [...new Set(recs.map(r => r.parameter))]
  const rowsOf = (p: string) => recs.filter(r => r.parameter === p)
  const picked = (p: string): SensitivityRow | undefined => rowsOf(p)[pick[p] ?? 0]

  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={3}>Sensitivity</Title>
      <Text size="sm" c="dimmed" mb="md">
        One parameter moved at a time, {recs[0]?.policy ?? 'plan'} re-run for each value (sensitivity.csv). The sliders
        only pick among the served rows; they never interpolate.
      </Text>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mb="lg">
        {SLIDERS.map(p => {
          const rs = rowsOf(p), r = picked(p)
          if (!rs.length) return <Text key={p} c="dimmed" size="sm">{PARAM_LABEL[p]}: not in sensitivity.csv.</Text>
          return (
            <Paper key={p} radius="md" p="md" className="sens-card">
              <Text fw={700} mb={4}>{PARAM_LABEL[p]}</Text>
              <Slider min={0} max={rs.length - 1} step={1} value={pick[p] ?? 0} restrictToMarks
                onChange={i => setPick(v => ({ ...v, [p]: i }))} label={i => String(rs[i]?.value)} mb="xl" mx="xs"
                marks={rs.map((x, i) => ({ value: i, label: String(x.value) }))} aria-label={PARAM_LABEL[p]} />
              {r && <Group gap="lg" mt="lg" className="num">
                <div><Text size="xs" c="dimmed" tt="uppercase" fw={600}>net</Text>
                  <Text fz={22} fw={800}>{`₹${fmt(r.net_inr)}`}</Text></div>
                <div><Text size="xs" c="dimmed" tt="uppercase" fw={600}>spoilage</Text>
                  <Text fz={22} fw={800}>{`${fmt(r.spoilage_kg)} kg`}</Text></div>
                <div><Text size="xs" c="dimmed" tt="uppercase" fw={600}>fulfilment</Text>
                  <Text fz={22} fw={800}>{`${fmt(r.demand_fulfillment_pct, 1)}%`}</Text></div>
              </Group>}
            </Paper>
          )
        })}
      </SimpleGrid>
      <Table.ScrollContainer minWidth={620}>
        <Table striped highlightOnHover verticalSpacing="xs" fz="md">
          <Table.Thead><Table.Tr>
            <Table.Th>parameter</Table.Th><Table.Th ta="right">value</Table.Th><Table.Th ta="right">net ₹</Table.Th>
            <Table.Th ta="right">spoilage kg</Table.Th><Table.Th ta="right">fulfilment %</Table.Th>
          </Table.Tr></Table.Thead>
          <Table.Tbody className="num">
            {params.flatMap(p => rowsOf(p).map((r, i) => {
              const on = SLIDERS.includes(p) && (pick[p] ?? 0) === i
              return (
                <Table.Tr key={`${p}-${i}`} bg={on ? 'var(--mantine-primary-color-light)' : undefined} fw={on ? 700 : undefined}>
                  <Table.Td>{i === 0 ? PARAM_LABEL[p] ?? p : ''}</Table.Td>
                  <Table.Td ta="right">{r.value} {on && <Badge size="xs" ml={4}>selected</Badge>}</Table.Td>
                  <Table.Td ta="right">{fmt(r.net_inr)}</Table.Td><Table.Td ta="right">{fmt(r.spoilage_kg)}</Table.Td>
                  <Table.Td ta="right">{fmt(r.demand_fulfillment_pct, 1)}</Table.Td>
                </Table.Tr>)
            }))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Paper>
  )
}
