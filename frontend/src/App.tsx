// Dashboard shell (ARCHITECTURE §16): sidebar (run picker, run form) + five tabs. Renders API JSON verbatim.
import { AppShell, Badge, Divider, Group, NumberInput, Select, Stack, Switch, Tabs, Text, Title } from '@mantine/core'
import {
  IconArrowsShuffle, IconChartBar, IconFlask, IconLeaf, IconRoute, IconShieldCheck, IconTimeline,
} from '@tabler/icons-react'
import { AnimatePresence, m } from 'motion/react'
import { memo, useCallback, useEffect, useRef, useState, type ComponentType, type ReactNode } from 'react'
import { api } from './api/client'
import { StatusBanner, SyntheticBanner } from './components/Banners'
import { RunButton } from './components/RunButton'
import { RunPicker } from './components/RunPicker'
import { Plan } from './tabs/Plan'
import { Replan } from './tabs/Replan'
import { Robustness } from './tabs/Robustness'
import { Scoreboard } from './tabs/Scoreboard'
import { Trust } from './tabs/Trust'
import { spring } from './theme'
import type { RunDetail, RunsList, ScenarioInfo } from './types'

type TabProps = { run: RunDetail; runId: string }
const TAB_NAMES = ['Scoreboard', 'Plan', 'Robustness', 'Replan', 'Trust'] as const
type TabName = (typeof TAB_NAMES)[number]
// memo: a kept-mounted tab only re-renders when its own props change (tab files stay untouched)
const TABS: Record<TabName, ComponentType<TabProps>> = {
  Scoreboard: memo(Scoreboard), Plan: memo(Plan), Robustness: memo(Robustness), Replan: memo(Replan), Trust: memo(Trust),
}
const TAB_ICONS: Record<TabName, ReactNode> = {
  Scoreboard: <IconChartBar size={18} />, Plan: <IconRoute size={18} />, Robustness: <IconTimeline size={18} />,
  Replan: <IconArrowsShuffle size={18} />, Trust: <IconShieldCheck size={18} />,
}
const POLICIES = ['fifo', 'fefo', 'last_day_50', 'milp', 'milp_markdown']
// ponytail: run_id of backend/tests/fixtures/metrics_example.json, used when /api/runs is empty + fixture
const FIXTURE_RUN_ID = 'EXAMPLE-SYNTHETIC'

// Opening reveal: header, sidebar, content arrive in sequence on progressively softer springs.
// ponytail: stagger via spring stiffness, not `delay` (delayed starts stall in headless screenshot runs)
const reveal = (t: (typeof spring)[keyof typeof spring], from: { x?: number; y?: number }) => ({
  initial: { opacity: 0, ...from },
  animate: { opacity: 1, x: 0, y: 0 },
  transition: t,
})

// Tabs stay mounted after first visit (no remount/refetch); the inactive ones are display:none.
// Only an enter animation, no exit: a rapid switch interrupts instantly instead of queueing.
function TabPane({ active, children }: { active: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const willChange = (v: string) => { if (ref.current) ref.current.style.willChange = v }
  return (
    <m.div ref={ref} hidden={!active} initial={{ opacity: 0, y: 6 }}
      animate={active ? { opacity: 1, y: 0 } : { opacity: 0, y: 6 }}
      transition={active ? spring.snappy : { duration: 0 }}
      onAnimationStart={() => active && willChange('transform, opacity')} onAnimationComplete={() => willChange('auto')}>
      {children}
    </m.div>
  )
}

export default function App() {
  // ?tab=plan opens a tab directly (screenshots, demo links)
  const [tab, setTab] = useState<TabName>(() => TAB_NAMES.find(
    t => t.toLowerCase() === new URLSearchParams(location.search).get('tab')?.toLowerCase()) ?? 'Scoreboard')
  const [visited, setVisited] = useState<TabName[]>([tab])
  if (!visited.includes(tab)) setVisited([...visited, tab]) // render-phase update: mounts in the same commit
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [runs, setRuns] = useState<RunsList>({ runs: [], fixture: false })
  const [runId, setRunId] = useState<string | null>(null)
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState('')
  const [scenario, setScenario] = useState('')
  const [policy, setPolicy] = useState('milp_markdown')
  const [seed, setSeed] = useState(42)
  const [markdown, setMarkdown] = useState(true)
  const [newsvendor, setNewsvendor] = useState(false)

  const loadRuns = useCallback(async (select?: string) => {
    try {
      const r = await api.runs()
      setRuns(r)
      setRunId(select ?? r.runs[0]?.run_id ?? (r.fixture ? FIXTURE_RUN_ID : null))
    } catch (e) { setError(`Cannot list runs: ${e instanceof Error ? e.message : e}`) }
  }, [])

  useEffect(() => {
    api.scenarios().then(s => { setScenarios(s); setScenario(v => v || s[0]?.name || '') })
      .catch(e => setError(`Cannot list scenarios: ${e.message}`))
    loadRuns()
  }, [loadRuns])

  useEffect(() => {
    if (!runId) return setRun(null)
    api.run(runId).then(setRun).catch(e => setError(`Cannot load run ${runId}: ${e.message}`))
  }, [runId])

  const fixture = runs.fixture || !!run?.fixture
  const info = run && scenarios.find(s => s.name === run.scenario || run.scenario.endsWith(`/${s.name}`))
  // shown unless the run's scenario is a listed one with a non-synthetic source (§16.1)
  const synthetic = fixture || (!!run && (!info || info.source === 'synthetic'))
  // runId = the outputs/ dir key (§11.2); it can differ from metrics.run_id

  return (
    <AppShell header={{ height: 64 }} navbar={{ width: 290, breakpoint: 'sm' }} padding="lg">
      <AppShell.Header className="shell-header">
        <m.div {...reveal(spring.snappy, { y: -12 })} style={{ height: '100%' }}>
          <Group h="100%" px="lg" justify="space-between" style={{ position: 'relative' }}>
            <Group gap={10}>
              <IconLeaf size={28} color="var(--mantine-color-green-7)" stroke={2.2} />
              <Title order={2} className="wordmark">FreshRoute</Title>
            </Group>
            <AnimatePresence>
              {synthetic && (
                <m.div key="syn" initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }} transition={spring.bouncy}>
                  <Badge color="yellow" variant="filled" size="lg" leftSection={<IconFlask size={14} />}
                    styles={{ root: { color: 'var(--mantine-color-dark-7)' } }}>synthetic data</Badge>
                </m.div>
              )}
            </AnimatePresence>
          </Group>
        </m.div>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <m.div {...reveal(spring.bouncy, { x: -24 })}>
          <Stack gap="sm">
            <RunPicker runs={runs.runs} value={runId} onChange={setRunId} />
            <Divider label="New plan" labelPosition="left" my={4} />
            <Select label="Scenario" value={scenario || null} onChange={v => setScenario(v ?? '')} allowDeselect={false}
              data={scenarios.map(s => ({ value: s.name, label: `${s.name} (${s.source})` }))} />
            <Select label="Policy" value={policy} onChange={v => v && setPolicy(v)} allowDeselect={false} data={POLICIES} />
            <NumberInput label="Seed" value={seed} onChange={v => setSeed(Number(v))} allowDecimal={false} />
            <Switch label="markdown" checked={markdown} onChange={e => setMarkdown(e.currentTarget.checked)} mt={4} />
            <Switch label="newsvendor" checked={newsvendor} onChange={e => setNewsvendor(e.currentTarget.checked)} />
            <div style={{ marginTop: 8 }}>
              <RunButton
                request={{ scenario: scenario && `data/scenarios/${scenario}`, policy, seed, flags: { markdown, newsvendor } }}
                onDone={id => loadRuns(id)} onError={setError} />
            </div>
          </Stack>
        </m.div>
      </AppShell.Navbar>

      <AppShell.Main>
        <m.div {...reveal(spring.soft, { y: 24 })}>
          <Stack gap="xs" mb="sm">
            <SyntheticBanner show={synthetic} />
            <StatusBanner fixture={fixture} manifest={run?.manifest ?? null} error={error} />
          </Stack>
          <Tabs value={tab} onChange={v => v && setTab(v as TabName)} variant="pills" radius="xl" mb="md"
            classNames={{ tab: 'shell-tab' }}>
            <Tabs.List className="shell-tabs">
              {TAB_NAMES.map(t => (
                <Tabs.Tab key={t} value={t}>
                  {t === tab && (
                    // layoutDependency: only re-measure on tab change; otherwise banners mounting above
                    // the tabs leave the pill projected at a stale y (stuck there under reduced motion)
                    <m.span layoutId="tab-pill" layoutDependency={tab} className="tab-pill" transition={spring.snappy}>
                      {/* squash on arrival, then spring back */}
                      <m.span className="tab-pill-fill" initial={{ scaleX: 1.12, scaleY: 0.8 }}
                        animate={{ scaleX: 1, scaleY: 1 }} transition={spring.bouncy} />
                    </m.span>
                  )}
                  <Group gap={6} wrap="nowrap" style={{ position: 'relative' }}>{TAB_ICONS[t]}<Text inherit>{t}</Text></Group>
                </Tabs.Tab>
              ))}
            </Tabs.List>
          </Tabs>
          {run && runId
            ? TAB_NAMES.filter(t => visited.includes(t)).map(t => {
              const T = TABS[t]
              return <TabPane key={t} active={t === tab}><T run={run} runId={runId} /></TabPane>
            })
            : <p className="placeholder">No run loaded.</p>}
        </m.div>
      </AppShell.Main>
    </AppShell>
  )
}
