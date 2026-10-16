// Robustness tab (ARCHITECTURE §14.1, §16; DATABASE §5.12): stress bands plan vs baseline, the served share of
// futures where the plan beats the baseline, and the sensitivity table. Every number is a served field, only rounded.
import { Alert, Badge, Button, Code, Group, Paper, SimpleGrid, Skeleton, Slider, Stack, Table, Text, ThemeIcon, Title } from '@mantine/core'
import { IconAlertTriangle, IconChartDots3, IconPlayerPlayFilled, IconShieldCheck } from '@tabler/icons-react'
import { m, useReducedMotion, type Variants } from 'motion/react'
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceDot, ResponsiveContainer, Scatter, ScatterChart, XAxis, YAxis, ZAxis } from 'recharts'
import { api, notOnDisk, waitDone } from '../api/client'
import { NO_SOLVES_HINT, useLiveSolves } from '../api/useLiveSolves'
import { ExampleBanner } from '../components/Banners'
import { Explain } from '../components/Explain'
import { Odometer } from '../components/KpiTile'
import { C } from '../components/Waterfall'
import { dotsWon, fmt, fmtShare } from '../lib/delta'
import { policyName, type Term } from '../lib/words'
import { spring } from '../theme'
import type { Band, FrontierResponse, SensitivityResponse, SensitivityRow, StressKpi, StressResponse, TabProps } from '../types'

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

export function Robustness({ run }: TabProps) {
  const stress = useServed(() => api.stress(run.scenario, run.seed), [run.scenario, run.seed])
  const sens = useServed(() => api.sensitivity(run.scenario, run.seed), [run.scenario, run.seed])

  const front = useServed(() => api.frontier(run.scenario, run.seed), [run.scenario, run.seed])

  const s = stress.data
  return (
    <Stack gap="lg">
      <ExampleBanner show={!!(s?.example || sens.data?.example)} what="stress / sensitivity" />
      {stress.error && <Alert color="red" icon={<IconAlertTriangle />} title="Couldn’t load the stress test">{stress.error}</Alert>}
      {s === undefined && !stress.error && <><Skeleton h={220} radius="lg" /><Skeleton h={300} radius="lg" /></>}
      {s === null && <StressEmpty scenario={run.scenario} policy={run.policy} seed={run.seed} onDone={stress.reload} />}
      {s && <>
        <Hero s={s} />
        <Bands s={s} />
      </>}
      <Frontier load={front.data} />
          <Sensitivity load={sens.data} error={sens.error} scenario={run.scenario} seed={run.seed} />
    </Stack>
  )
}

function Hint({ icon, title, cmd, children }: { icon: ReactNode; title: string; cmd: string; children?: ReactNode }) {
  return (
    <Paper withBorder radius="lg" p="xl">
      <Stack align="center" gap="xs">
        <ThemeIcon size={48} radius="xl" variant="light" color="gray">{icon}</ThemeIcon>
        <Text fw={600}>{title}</Text>
        <Text size="xs" c="dimmed" ta="center">For developers, the same from the command line: <Code fz="xs">{cmd}</Code></Text>
        {children}
      </Stack>
    </Paper>
  )
}

function StressEmpty({ scenario, policy, seed, onDone }: { scenario: string; policy: string; seed: number; onDone: () => void }) {
  const live = useLiveSolves()
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
    <Hint icon={<IconChartDots3 size={28} />} title="The stress test hasn’t been run for this plan yet"
      cmd={`freshroute stress --scenario ${scenarioDir(scenario)} --policy ${policy} --n ${STRESS_N} --seed ${seed}`}>
      <Button mt="xs" radius="xl" leftSection={<IconPlayerPlayFilled size={16} />} loading={busy} onClick={start} disabled={!live} title={live ? undefined : NO_SOLVES_HINT}>
        Run the stress test ({STRESS_N} futures, ~1 min)</Button>
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
    <Paper radius="lg" p="xl" className="band">
      <Group gap="lg" wrap="nowrap" align="flex-start">
        <ThemeIcon size={64} radius="xl" variant="white" color="green"><IconShieldCheck size={38} /></ThemeIcon>
        <div>
          <Text fz={40} fw={800} lh={1.1} c="white">
            {policyName(plan)} beats {policyName(baseline)} on profit in <Odometer text={fmtShare(share.net_inr)} /> of{' '}
            {fmt(n)} simulated <Explain term="future">futures</Explain>
          </Text>
          <Text fz="lg" c="white" opacity={0.85} mt={6}>
            Food spoiled is lower in {fmtShare(share.spoilage_kg)} of them. Both plans face{' '}
            <Explain note={`Same random demand, travel time and shelf life for both plans in each future (random seeds ${base_seed}+i).`}>
              the exact same random futures</Explain>.
          </Text>
        </div>
      </Group>
      {/* one dot per sampled future; how many are green is the served share, the order is cosmetic */}
      <m.div className="futures" variants={matrix} initial={reduce ? false : 'hidden'} animate="show" aria-hidden>
        {Array.from({ length: n }, (_, i) => <m.span key={i} className="future" data-won={i < won || undefined} variants={dot} />)}
      </m.div>
      <Group gap="lg" mt="xs">
        <Text size="sm" c="white"><span className="future" data-won /> {policyName(plan)} earns more</Text>
        <Text size="sm" c="white"><span className="future" /> {policyName(baseline)} earns more or ties</Text>
      </Group>
    </Paper>
  )
}

// ---------- P10–P50–P90 bands ----------
const BAND_META: Record<StressKpi, { title: string; unit: (v: number) => string }> = {
  net_inr: { title: 'Profit', unit: v => `₹${fmt(v)}` },
  spoilage_kg: { title: 'Food spoiled', unit: v => `${fmt(v)} kg` },
  demand_fulfillment_pct: { title: 'Orders filled', unit: v => `${fmt(v, 1)}%` },
}

function MedianTick(p: { cx?: number; cy?: number; fill?: string }) {
  return <rect x={(p.cx ?? 0) - 2.5} y={(p.cy ?? 0) - 20} width={5} height={40} rx={2.5} fill={p.fill} />
}

function BandChart({ kpi, s, height }: { kpi: StressKpi; s: StressResponse; height: number }) {
  const reduce = useReducedMotion()
  const { plan, baseline, bands } = s.summary
  const meta = BAND_META[kpi]
  const rows: { name: string; band: Band; colour: string }[] = [
    { name: policyName(baseline), band: bands[kpi].baseline, colour: 'var(--mantine-color-gray-6)' },
    { name: policyName(plan), band: bands[kpi].plan, colour: C.good },
  ]
  const data = rows.map(r => ({ name: r.name, range: [r.band.p10, r.band.p90] }))
  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={4}>{meta.title}</Title>
      <Text size="sm" c="dimmed"><Explain term="bands">Bar = range in 8 of 10 futures (P10–P90), tick = middle result (P50)</Explain>,
        over {fmt(s.summary.n)} futures</Text>
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
        <Table.Thead><Table.Tr><Table.Th /><Table.Th ta="right">Low (P10)</Table.Th><Table.Th ta="right">Middle (P50)</Table.Th>
          <Table.Th ta="right">High (P90)</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>
          {[...rows].reverse().map(r => (
            <Table.Tr key={r.name} fw={r.name === policyName(plan) ? 700 : undefined}>
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
  q10: 'How fast heat speeds up spoilage', elasticity_multiplier: 'How much discounts boost sales (elasticity ×)',
  overship_slack: 'Allowed overshipping', demand_multiplier: 'Demand level (×)',
}
const PARAM_TERM: Record<string, Term> = { q10: 'q10', elasticity_multiplier: 'elasticity' }
const paramLabel = (p: string) => (PARAM_TERM[p]
  ? <Explain term={PARAM_TERM[p]}>{PARAM_LABEL[p] ?? p}</Explain> : PARAM_LABEL[p] ?? p)
const SLIDERS = ['q10', 'elasticity_multiplier'] // the two the pitch moves; the table shows every served row

function Sensitivity({ load, error, scenario, seed }: { load: Load<SensitivityResponse>; error: string; scenario: string; seed: number }) {
  const [pick, setPick] = useState<Record<string, number>>({}) // parameter -> row index within that parameter
  if (error) return <Alert color="red" icon={<IconAlertTriangle />} title="Couldn’t load the assumption test">{error}</Alert>
  if (load === undefined) return <Skeleton h={320} radius="lg" />
  if (load === null) return <Hint icon={<IconChartDots3 size={28} />} title="The assumption test hasn’t been run for this plan yet"
    cmd={`freshroute sensitivity --scenario ${scenarioDir(scenario)} --seed ${seed}`} />
  const recs = load.records
  const params = [...new Set(recs.map(r => r.parameter))]
  const rowsOf = (p: string) => recs.filter(r => r.parameter === p)
  const picked = (p: string): SensitivityRow | undefined => rowsOf(p)[pick[p] ?? 0]

  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={3}>What if our assumptions are wrong?</Title>
      <Text size="sm" c="dimmed" mb="md">
        We change <Explain term="sensitivity">one assumption at a time</Explain> and re-run the plan for each value.
        Move a slider to pick one of the tested values; nothing in between is guessed.
      </Text>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mb="lg">
        {SLIDERS.map(p => {
          const rs = rowsOf(p), r = picked(p)
          if (!rs.length) return <Text key={p} c="dimmed" size="sm">{PARAM_LABEL[p]}: not tested yet.</Text>
          return (
            <Paper key={p} radius="md" p="md" className="sens-card">
              <Text fw={700} mb={4}>{paramLabel(p)}</Text>
              <Slider min={0} max={rs.length - 1} step={1} value={pick[p] ?? 0} restrictToMarks
                onChange={i => setPick(v => ({ ...v, [p]: i }))} label={i => String(rs[i]?.value)} mb="xl" mx="xs"
                marks={rs.map((x, i) => ({ value: i, label: String(x.value) }))} aria-label={PARAM_LABEL[p]} />
              {r && <Group gap="lg" mt="lg" className="num">
                <div><Text size="xs" c="dimmed" tt="uppercase" fw={600}>profit</Text>
                  <Text fz={22} fw={800}>{`₹${fmt(r.net_inr)}`}</Text></div>
                <div><Text size="xs" c="dimmed" tt="uppercase" fw={600}>food spoiled</Text>
                  <Text fz={22} fw={800}>{`${fmt(r.spoilage_kg)} kg`}</Text></div>
                <div><Text size="xs" c="dimmed" tt="uppercase" fw={600}>orders filled</Text>
                  <Text fz={22} fw={800}>{`${fmt(r.demand_fulfillment_pct, 1)}%`}</Text></div>
              </Group>}
            </Paper>
          )
        })}
      </SimpleGrid>
      <Table.ScrollContainer minWidth={620}>
        <Table striped highlightOnHover verticalSpacing="xs" fz="md">
          <Table.Thead><Table.Tr>
            <Table.Th>Assumption</Table.Th><Table.Th ta="right">Tested value</Table.Th><Table.Th ta="right">Profit (₹)</Table.Th>
            <Table.Th ta="right">Food spoiled (kg)</Table.Th><Table.Th ta="right">Orders filled (%)</Table.Th>
          </Table.Tr></Table.Thead>
          <Table.Tbody className="num">
            {params.flatMap(p => rowsOf(p).map((r, i) => {
              const on = SLIDERS.includes(p) && (pick[p] ?? 0) === i
              return (
                <Table.Tr key={`${p}-${i}`} bg={on ? 'var(--mantine-primary-color-light)' : undefined} fw={on ? 700 : undefined}>
                  <Table.Td>{i === 0 ? paramLabel(p) : ''}</Table.Td>
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

// ---------- spoilage / profit frontier ----------
const SHIPPED_LAMBDA = 1 // config.LAMBDA_SPOIL: the weight of the plan we ship

function Frontier({ load }: { load: Load<FrontierResponse> }) {
  if (!load) return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={3}>Profit versus spoilage</Title>
      <Text size="sm" c="dimmed">{load === undefined ? 'Loading…' : '— (not run for this plan yet)'}</Text>
    </Paper>
  )
  // weights that landed on the same plan share one marker and one label ("λ=0/1/10"),
  // so labels never overprint and the shipped weight's colour is not hidden underneath
  const groups = new Map<string, FrontierResponse['records']>()
  for (const r of load.records) {
    const key = `${r.net_inr}|${r.spoilage_kg}`
    groups.set(key, [...(groups.get(key) ?? []), r])
  }
  const pts = [...groups.values()].map(g => ({
    ...g[0], label: `λ=${g.map(r => r.lambda_spoil).join('/')}`, // no spaces: recharts wraps labels on spaces
    lambda_spoil: g.some(r => r.lambda_spoil === SHIPPED_LAMBDA) ? SHIPPED_LAMBDA : g[0].lambda_spoil,
  }))
  // the trade-off line joins only the points the engine did not flag as dominated
  const curve = pts.filter(p => !p.dominated).sort((a, b) => a.spoilage_kg - b.spoilage_kg)
  const anyDominated = pts.some(p => p.dominated)
  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={3}>Profit versus spoilage</Title>
      <Text size="sm" c="dimmed" mb="md">
        We re-plan with a different penalty (λ) on each kg that spoils. Higher λ saves more food but gives up some profit.
        The highlighted point (λ={SHIPPED_LAMBDA}) uses the weight of the plan we ship; each point is its own time-limited solve. λ prices spoilage in rupees, so kilograms do not always move the same way.
        {anyDominated && ' Hollow grey points lose to another point on both profit and spoilage: the planner ran out of time there, so they are not a real trade-off and the line skips them.'}
      </Text>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 28, right: 32, bottom: 24, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" dataKey="spoilage_kg" name="Food spoiled" unit=" kg" domain={['auto', 'auto']}
            label={{ value: 'Food spoiled (kg)', position: 'insideBottom', offset: -12 }} />
          <YAxis type="number" dataKey="net_inr" name="Profit" width={80} domain={['auto', 'auto']}
            tickFormatter={v => `₹${fmt(v)}`} />
          <ZAxis range={[90, 90]} />
          <Scatter data={curve} line={{ stroke: '#adb5bd', strokeDasharray: '4 4' }} shape={() => <g />} legendType="none" isAnimationActive={false} />
          <Scatter data={pts} fill="#868e96">
            {pts.map(p => <Cell key={p.lambda_spoil}
              fill={p.dominated ? 'transparent' : p.lambda_spoil === SHIPPED_LAMBDA ? '#e8590c' : '#868e96'}
              stroke={p.dominated ? '#adb5bd' : undefined} strokeWidth={p.dominated ? 2 : 0} />)}
            <LabelList dataKey="label" position="top" />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </Paper>
  )
}
