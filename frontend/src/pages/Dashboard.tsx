import {
  ActionIcon, Alert, Badge, Button, Drawer, Group, NumberInput, Paper,
  Select, Stack, Switch, Tabs, Text, ThemeIcon, Title, Tooltip
} from '@mantine/core'
import {
  IconAdjustments, IconAlertTriangle, IconCpu, IconRoute, IconShieldCheck, IconTrendingUp, IconTruck
} from '@tabler/icons-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { RunButton } from '../components/RunButton'
import { RunPicker } from '../components/RunPicker'
import { Plan } from '../tabs/Plan'
import { Replan } from '../tabs/Replan'
import { Robustness } from '../tabs/Robustness'
import { Scoreboard } from '../tabs/Scoreboard'
import { Trust } from '../tabs/Trust'
import type { Progress, RunDetail, RunsList, ScenarioInfo } from '../types'

interface DashboardProps {
  onBackToStory: () => void
}

const FIXTURE_RUN_ID = 'EXAMPLE-SYNTHETIC'

export function Dashboard({ onBackToStory }: DashboardProps) {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [runs, setRuns] = useState<RunsList>({ runs: [], fixture: false })
  const [runId, setRunId] = useState<string | null>(null)
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState('')
  const [live, setLive] = useState<Progress | null>(null) // solver still improving the shown plan
  const [reload, setReload] = useState(0) // bumped per published plan: re-fetch the same run id
  const [activeTab, setActiveTab] = useState<string>('overview')

  // Developer settings (tucked in drawer)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [scenario, setScenario] = useState('practice')
  const [policy, setPolicy] = useState('milp')
  const [seed, setSeed] = useState(42)
  const [newsvendor, setNewsvendor] = useState(false)

  const loadRuns = useCallback(async (select?: string) => {
    try {
      const r = await api.runs()
      setRuns(r)
      // prefer the demo run (practice / milp), else the newest listing
      const demo = r.runs.find(
        (x) => x.scenario.split('/').pop() === 'practice' && x.policy === 'milp'
      )
      setRunId(select ?? demo?.run_id ?? r.runs[0]?.run_id ?? (r.fixture ? FIXTURE_RUN_ID : null))
    } catch (e) {
      setError(`Cannot list runs: ${e instanceof Error ? e.message : e}`)
    }
  }, [])

  useEffect(() => {
    api
      .scenarios()
      .then((s) => {
        setScenarios(s)
        setScenario((v) => v || s.find((x) => x.name === 'practice')?.name || s[0]?.name || 'practice')
      })
      .catch((e) => setError(`Cannot list scenarios: ${e.message}`))
    loadRuns()
  }, [loadRuns])

  useEffect(() => {
    if (!runId) return setRun(null)
    api
      .run(runId)
      .then((r) => {
        setRun(r)
        setError('')
      })
      .catch((e) => setError(`Cannot load run ${runId}: ${e.message}`))
  }, [runId, reload])

  const onProgress = (id: string, p: Progress) => { setLive(p); loadRuns(id); setReload((n) => n + 1) }
  const onDone = (id: string) => { setLive(null); loadRuns(id); setReload((n) => n + 1) }

  const ready = run && runId
  const scenarioDisplayName = scenario === 'practice' ? 'Bangalore Central Hub (200 Batches · 8 Mandis)' : scenario

  return (
    <div className="dashboard-container">
      {/* 1. TOP OPERATIONS CONTROL BAR */}
      <Paper withBorder p="md" className="dashboard-header-bar" radius={0}>
        <Group justify="space-between" wrap="wrap" gap="md">
          <div>
            <Group gap="xs" mb={4}>
              <Badge color="green" variant="filled" size="sm">
                OPERATIONS CONSOLE
              </Badge>
              <Text size="xs" c="dimmed">
                DECISION SUPPORT SYSTEM
              </Text>
            </Group>
            <Title order={2} className="anton" style={{ letterSpacing: '0.02em', fontSize: '1.75rem' }}>
              {scenarioDisplayName.toUpperCase()}
            </Title>
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

            {/* Subtle Advanced Settings Drawer trigger */}
            <Tooltip label="Scenario & Advanced Settings">
              <ActionIcon
                variant="default"
                size="xl"
                radius="xs"
                onClick={() => setSettingsOpen(true)}
                aria-label="Simulation settings"
              >
                <IconAdjustments size={20} stroke={1.8} />
              </ActionIcon>
            </Tooltip>

            {/* Return to Product Story */}
            <Tooltip label="Return to Product Story">
              <Button
                variant="subtle"
                color="gray"
                size="sm"
                onClick={onBackToStory}
                visibleFrom="md"
              >
                Tour
              </Button>
            </Tooltip>
          </Group>
        </Group>

        {live && (
          <Alert color="green" variant="light" mt="sm" title="Showing the best plan found so far">
            Still searching for a better one. Plan v{live.version} · net ₹{Math.round(live.net_inr).toLocaleString('en-IN')} · {live.elapsed_s} s
          </Alert>
        )}

        {error && (
          <Alert color="red" icon={<IconAlertTriangle />} title="System Alert" mt="sm">
            {error}
          </Alert>
        )}
      </Paper>

      {/* 2. OPERATIONAL NAVIGATION TABS */}
      <div className="dashboard-nav-strip">
        <Tabs value={activeTab} onChange={(val) => val && setActiveTab(val)} color="green">
          <Tabs.List className="dashboard-tabs-list">
            <Tabs.Tab value="overview" leftSection={<IconTrendingUp size={18} />}>
              1. OVERVIEW & FINANCIALS
            </Tabs.Tab>
            <Tabs.Tab value="trucks" leftSection={<IconTruck size={18} />}>
              2. FLEET & DISPATCHES
            </Tabs.Tab>
            <Tabs.Tab value="disruptions" leftSection={<IconRoute size={18} />}>
              3. WHAT-IF & DISRUPTIONS
            </Tabs.Tab>
            <Tabs.Tab value="audit" leftSection={<IconShieldCheck size={18} />}>
              4. INDEPENDENT AUDIT
            </Tabs.Tab>
          </Tabs.List>
        </Tabs>
      </div>

      {/* 3. MAIN WORKSPACE VIEWPORT */}
      <div className="dashboard-workspace">
        {!ready ? (
          <Paper withBorder p="xl" ta="center" radius="xs" my="xl">
            <ThemeIcon size={64} radius="xl" color="green" variant="light" mx="auto" mb="md">
              <IconCpu size={36} />
            </ThemeIcon>
            <Title order={3}>NO DISPATCH PLAN GENERATED YET</Title>
            <Text size="sm" c="dimmed" maw={460} mx="auto" mt={8} mb="xl">
              Click the button above to run the optimization engine. In seconds, FreshRoute will allocate 200 batches across 8 markets.
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
          <div style={{ marginTop: 24 }}>
            {activeTab === 'overview' && (
              <Stack gap="xl">
                <Scoreboard run={run} />
              </Stack>
            )}

            {activeTab === 'trucks' && (
              <Stack gap="xl">
                <Plan run={run} runId={runId} />
              </Stack>
            )}

            {activeTab === 'disruptions' && (
              <Stack gap="xl">
                <Paper withBorder p="md" radius="xs" style={{ background: 'var(--panel)' }}>
                  <Group justify="space-between" mb="xs">
                    <div>
                      <Title order={4}>Mid-Day Route & Fleet Disruption Simulator</Title>
                      <Text size="xs" c="dimmed">
                        Test system resilience: simulate an unexpected highway closure, reefer breakdown, or demand spike.
                      </Text>
                    </div>
                    <Badge color="blue" variant="light">
                      HiGHS RE-SOLVE · 2 S CAP
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
          </div>
        )}
      </div>

      {/* 4. SETTINGS DRAWER (TUCKED AWAY FOR ADVANCED CONTROL) */}
      <Drawer
        opened={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title="Simulation Settings"
        position="right"
        size="md"
      >
        <Stack gap="md">
          <Text size="xs" c="dimmed">
            Configure scenario inputs and solver parameters. The default configuration executes the recommended
            A+ solver spine on the calibrated practice scenario.
          </Text>

          <Select
            label="Scenario Dataset"
            value={scenario}
            onChange={(v) => v && setScenario(v)}
            data={scenarios.map((s) => ({ value: s.name, label: `${s.name} (${s.horizon_days}d)` }))}
            allowDeselect={false}
          />

          <Select
            label="Dispatch Algorithm"
            value={policy}
            onChange={(v) => v && setPolicy(v)}
            data={[
              { value: 'milp', label: 'FreshRoute MILP (Recommended)' },
              { value: 'fefo', label: 'FEFO-Greedy Baseline (Warehouse Rule)' },
              { value: 'fifo', label: 'Naive FIFO Baseline' },
              { value: 'last_day_50', label: 'Naive FIFO + Flat 50% Cut' },
            ]}
            allowDeselect={false}
          />

          <NumberInput
            label="Simulation Random Seed"
            description="Fixes common random numbers for determinism"
            value={seed}
            onChange={(v) => setSeed(Number(v))}
            allowDecimal={false}
          />

          <Switch
            label="Newsvendor Demand Quantiles"
            description="Adjusts target delivery quantiles based on underage/overage cost"
            checked={newsvendor}
            onChange={(e) => setNewsvendor(e.currentTarget.checked)}
          />

          <div style={{ marginTop: 16 }}>
            <Text size="xs" fw={700} mb="xs">
              SAVED RUN ARCHIVE
            </Text>
            <RunPicker runs={runs.runs} value={runId} onChange={setRunId} />
          </div>

          <Button
            mt="lg"
            variant="light"
            color="green"
            onClick={() => {
              setSettingsOpen(false)
            }}
          >
            Apply & Close
          </Button>
        </Stack>
      </Drawer>
    </div>
  )
}
