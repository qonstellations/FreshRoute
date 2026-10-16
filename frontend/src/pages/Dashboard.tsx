import {
  Alert, Badge, Button, Group, NumberInput, Paper,
  Select, Skeleton, Stack, Switch, Tabs, Text, ThemeIcon, Title, Tooltip
} from '@mantine/core'
import {
  IconAlertTriangle, IconCpu, IconRoute, IconShieldCheck, IconTrendingUp, IconTruck
} from '@tabler/icons-react'
import { AnimatePresence, m } from 'motion/react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { Explain } from '../components/Explain'
import { Odometer } from '../components/KpiTile'
import { RunButton } from '../components/RunButton'
import { RunPicker } from '../components/RunPicker'
import { Plan } from '../tabs/Plan'
import { Replan } from '../tabs/Replan'
import { Robustness } from '../tabs/Robustness'
import { Scoreboard } from '../tabs/Scoreboard'
import { Trust } from '../tabs/Trust'
import { DEMO_RUN } from '../lib/demo'
import { policyName, scenarioName } from '../lib/words'
import { spring } from '../theme'
import type { Progress, RunDetail, RunsList, ScenarioInfo } from '../types'

const TABS = ['overview', 'trucks', 'disruptions', 'audit']

interface DashboardProps {
  onBackToOverview: () => void
  initialTab?: string
}

export function Dashboard({ onBackToOverview, initialTab = 'overview' }: DashboardProps) {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [runs, setRuns] = useState<RunsList>({ runs: [], fixture: false })
  const [runId, setRunId] = useState<string | null>(null)
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState('')
  const [runsLoaded, setRunsLoaded] = useState(false) // first run list answered (ok or not)
  const [live, setLive] = useState<Progress | null>(null) // solver still improving the shown plan
  const [reload, setReload] = useState(0) // bumped per published plan: re-fetch the same run id
  // dir: +1 moving right through the numbered tabs, -1 back; the content slides in from that side
  const [tab, setTab] = useState({ id: initialTab, dir: 0 })
  const activeTab = tab.id
  const pickTab = (id: string) => setTab(t => ({ id, dir: Math.sign(TABS.indexOf(id) - TABS.indexOf(t.id)) }))

  const [scenario, setScenario] = useState('practice')
  const [policy, setPolicy] = useState('milp')
  const [seed, setSeed] = useState(42)
  const [newsvendor, setNewsvendor] = useState(false)

  const loadRuns = useCallback(async (select?: string) => {
    try {
      const r = await api.runs()
      setRuns(r)
      // open on the saved demo run (practice, MILP, seed 42) until the user runs or picks another
      if (select) setRunId(select)
      else setRunId((v) => v ?? r.runs.find((x) => x.run_id === DEMO_RUN)?.run_id ?? null)
    } catch (e) {
      setError(`Could not load the saved results: ${e instanceof Error ? e.message : e}`)
    } finally {
      setRunsLoaded(true)
    }
  }, [])

  useEffect(() => {
    api
      .scenarios()
      .then((s) => {
        setScenarios(s)
        setScenario((v) => v || s.find((x) => x.name === 'practice')?.name || s[0]?.name || 'practice')
      })
      .catch((e) => setError(`Could not load the list of scenarios: ${e.message}`))
    loadRuns()
  }, [loadRuns])

  useEffect(() => {
    if (!runId) return setRun(null)
    let stale = false // a slow response must not overwrite a newer run's data
    api
      .run(runId)
      .then((r) => {
        if (stale) return
        setRun(r)
        setError('')
      })
      .catch((e) => !stale && setError(`Could not open this result (${runId}): ${e.message}`))
    return () => { stale = true }
  }, [runId, reload])

  const onProgress = (id: string, p: Progress) => { setLive(p); loadRuns(id); setReload((n) => n + 1) }
  const onDone = (id: string) => { setLive(null); loadRuns(id); setReload((n) => n + 1) }

  const ready = run && runId
  const loading = !ready && !error && (!runsLoaded || !!runId) // first fetch still in flight

  return (
    <div className="dashboard-container">
      {/* 1. TOP OPERATIONS CONTROL BAR */}
      <Paper withBorder p="md" className="dashboard-header-bar" radius={0} style={{ viewTransitionName: 'launch' }}>
        <Group justify="space-between" wrap="wrap" gap="md">
          <div>
            <Group gap="xs" mb={4}>
              <Badge color="green" variant="filled" size="sm">
                OPERATIONS CONSOLE
              </Badge>
              <Text size="xs" c="dimmed">
                <Explain term="synthetic">SYNTHETIC DATA</Explain>
              </Text>
            </Group>
            <Title order={2} className="anton" style={{ letterSpacing: '0.02em', fontSize: '1.75rem' }}>
              {scenarioName(scenario).toUpperCase()}
            </Title>
            <Text size="sm" c="dimmed" maw={720} mt={4}>
              A made-up but realistic produce hub near Bengaluru: 200 batches of fresh produce, 8 markets, a 3-day
              plan. Use the tabs below to see results, today's loading list, a re-plan after a disruption, and the independent check.
            </Text>
          </div>

          <Group gap="sm" wrap="nowrap">
            {/* Primary 1-Click Run Optimization Action */}
            <RunButton
              request={{
                scenario: scenario && `data/scenarios/${scenario}`,
                policy,
                seed,
                flags: { markdown: false, newsvendor },
              }}
              onProgress={onProgress}
              onDone={onDone}
              onError={setError}
            />

            {/* Back to the overview page */}
            <Tooltip label="Back to the overview page">
              <Button
                variant="subtle"
                color="gray"
                size="sm"
                onClick={onBackToOverview}
                visibleFrom="md"
              >
                Back to overview
              </Button>
            </Tooltip>
          </Group>
        </Group>

        {/* Run settings, always visible: what the optimiser plans for. Defaults reproduce the demo run. */}
        <Group gap="md" mt="md" align="flex-end" wrap="wrap">
          <Select
            label="Scenario"
            size="xs"
            w="100%"
            maw={300}
            value={scenario}
            onChange={(v) => v && setScenario(v)}
            data={scenarios.map((s) => ({ value: s.name, label: `${scenarioName(s.name)} (${s.horizon_days} days)` }))}
            allowDeselect={false}
          />
          <Select
            label="How to plan"
            size="xs"
            w="100%"
            maw={240}
            value={policy}
            onChange={(v) => v && setPolicy(v)}
            data={[
              { value: 'milp', label: `${policyName('milp')} (recommended)` },
              { value: 'fefo', label: policyName('fefo') },
              { value: 'fifo', label: policyName('fifo') },
              { value: 'last_day_50', label: policyName('last_day_50') },
            ]}
            allowDeselect={false}
          />
          <NumberInput
            label={<Explain term="seed">Random seed</Explain>}
            size="xs"
            w={100}
            value={seed}
            onChange={(v) => setSeed(Number(v))}
            allowDecimal={false}
          />
          <Switch
            size="xs"
            mb={6}
            label={<Explain term="newsvendor">Ship more or less than forecast</Explain>}
            checked={newsvendor}
            onChange={(e) => setNewsvendor(e.currentTarget.checked)}
          />
          {runs.runs.length > 0 && <RunPicker runs={runs.runs} value={runId} onChange={setRunId} />}
        </Group>

        {/* Live solve: each better plan rolls the served profit forward; the tabs below refresh under it. */}
        <AnimatePresence initial={false}>
          {live && (
            <m.div className="live-strip" role="status" initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={spring.soft}>
              <m.span key={live.version} className="live-flash" initial={{ opacity: 0.55 }} animate={{ opacity: 0 }}
                transition={{ duration: 0.9 }} aria-hidden />
              <div className="live-inner">
                <span className="live-dot" aria-hidden />
                <span>Best plan so far, version <Odometer text={String(live.version)} />. Still looking for a better one.</span>
                <span className="live-net">Profit after all costs ₹<Odometer text={Math.round(live.net_inr).toLocaleString('en-IN')} /></span>
                <Text span size="xs" c="dimmed">{live.elapsed_s} s of searching</Text>
              </div>
            </m.div>
          )}
        </AnimatePresence>

        {error && (
          <Alert color="red" icon={<IconAlertTriangle />} title="Something went wrong" mt="sm">
            {error}
          </Alert>
        )}
      </Paper>

      {/* 2. OPERATIONAL NAVIGATION TABS */}
      <div className="dashboard-nav-strip">
        <Tabs value={activeTab} onChange={(val) => val && pickTab(val)} color="green">
          <Tabs.List className="dashboard-tabs-list">
            {([
              ['overview', IconTrendingUp, '1. RESULTS'],
              ['trucks', IconTruck, "2. TODAY'S PLAN"],
              ['disruptions', IconRoute, '3. WHAT IF SOMETHING BREAKS?'],
              ['audit', IconShieldCheck, '4. PROOF & AUDIT'],
            ] as const).map(([v, Icon, label]) => (
              <Tabs.Tab key={v} value={v} leftSection={<Icon size={18} />}>
                {label}
                {activeTab === v && <m.span layoutId="tab-ink" className="tab-ink" transition={spring.bouncy} aria-hidden />}
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs>
      </div>

      {/* 3. MAIN WORKSPACE VIEWPORT */}
      <div className="dashboard-workspace">
        {loading ? (
          <Stack gap="md" my="xl" aria-busy="true">
            <Skeleton height={120} />
            <Skeleton height={260} />
          </Stack>
        ) : !ready ? (
          <Paper withBorder p="xl" ta="center" radius="xs" my="xl">
            <ThemeIcon size={64} radius="xl" color="green" variant="light" mx="auto" mb="md">
              <IconCpu size={36} />
            </ThemeIcon>
            <Title order={3}>NO PLAN YET</Title>
            <Text size="sm" c="dimmed" maw={460} mx="auto" mt={8} mb="xl">
              Click Run the optimiser to make one. FreshRoute decides where each of the 200 batches goes across the 8 markets. A first plan appears in about 1 to 2 seconds.
            </Text>
            <RunButton
              request={{
                scenario: scenario && `data/scenarios/${scenario}`,
                policy,
                seed,
                flags: { markdown: false, newsvendor },
              }}
              onProgress={onProgress}
              onDone={onDone}
              onError={setError}
            />
          </Paper>
        ) : (
          <AnimatePresence mode="wait" initial={false} custom={tab.dir}>
          <m.div key={activeTab} style={{ marginTop: 24 }} custom={tab.dir}
            variants={{
              enter: (d: number) => ({ opacity: 0, x: d * 48 }),
              show: { opacity: 1, x: 0, transition: spring.snappy },
              leave: (d: number) => ({ opacity: 0, x: d * -48, transition: { duration: 0.12 } }),
            }}
            initial="enter" animate="show" exit="leave">
            {activeTab === 'overview' && (
              <Stack gap="xl">
                <Scoreboard run={run} />
              </Stack>
            )}

            {activeTab === 'trucks' && (
              <Stack gap="xl">
                <Plan run={run} runId={runId} rev={reload} />
              </Stack>
            )}

            {activeTab === 'disruptions' && (
              <Stack gap="xl">
                <Paper withBorder p="md" radius="xs" style={{ background: 'var(--panel)' }}>
                  <Group justify="space-between" mb="xs">
                    <div>
                      <Title order={4}>What if something breaks mid-day?</Title>
                      <Text size="xs" c="dimmed">
                        How to use: close a road on the map, break down a{' '}
                        <Explain term="reefer">cold truck</Explain> or add a demand spike. FreshRoute re-plans the rest of
                        the day in a few seconds and shows what changed.
                      </Text>
                    </div>
                    <Badge color="blue" variant="light">
                      EACH RE-PLAN TAKES A FEW SECONDS
                    </Badge>
                  </Group>
                </Paper>
                <Replan run={run} runId={runId} />
                <Robustness run={run} runId={runId} />
              </Stack>
            )}

            {activeTab === 'audit' && (
              <Stack gap="xl">
                <Trust run={run} />
              </Stack>
            )}
          </m.div>
          </AnimatePresence>
        )}
      </div>

    </div>
  )
}
