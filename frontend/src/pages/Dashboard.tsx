import {
  ActionIcon, Alert, Badge, Button, Drawer, Group, NumberInput, Paper,
  Select, Stack, Switch, Tabs, Text, ThemeIcon, Title, Tooltip
} from '@mantine/core'
import {
  IconAdjustments, IconAlertTriangle, IconCpu, IconRoute, IconShieldCheck, IconTrendingUp, IconTruck
} from '@tabler/icons-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { Explain } from '../components/Explain'
import { RunButton } from '../components/RunButton'
import { RunPicker } from '../components/RunPicker'
import { Plan } from '../tabs/Plan'
import { Replan } from '../tabs/Replan'
import { Robustness } from '../tabs/Robustness'
import { Scoreboard } from '../tabs/Scoreboard'
import { Trust } from '../tabs/Trust'
import { policyName, scenarioName } from '../lib/words'
import type { Progress, RunDetail, RunsList, ScenarioInfo } from '../types'

interface DashboardProps {
  onBackToOverview: () => void
}

const FIXTURE_RUN_ID = 'EXAMPLE-SYNTHETIC'

export function Dashboard({ onBackToOverview }: DashboardProps) {
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
      setError(`Could not load the saved results: ${e instanceof Error ? e.message : e}`)
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
    api
      .run(runId)
      .then((r) => {
        setRun(r)
        setError('')
      })
      .catch((e) => setError(`Could not open this result (${runId}): ${e.message}`))
  }, [runId, reload])

  const onProgress = (id: string, p: Progress) => { setLive(p); loadRuns(id); setReload((n) => n + 1) }
  const onDone = (id: string) => { setLive(null); loadRuns(id); setReload((n) => n + 1) }

  const ready = run && runId

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
                <Explain term="synthetic">SYNTHETIC DATA</Explain>
              </Text>
            </Group>
            <Title order={2} className="anton" style={{ letterSpacing: '0.02em', fontSize: '1.75rem' }}>
              {scenarioName(scenario).toUpperCase()}
            </Title>
            <Text size="sm" c="dimmed" maw={720} mt={4}>
              What you're looking at: a made-up but realistic produce hub near Bengaluru with 200 batches of fresh
              produce, 8 markets and a 3-day plan. Results compares FreshRoute with simple rules. Today's plan shows
              which crate goes on which truck. What if something breaks? lets you close a road and watch it re-plan.
              Proof &amp; audit shows the independent check.
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

            {/* Subtle Advanced Settings Drawer trigger */}
            <Tooltip label="Advanced settings: scenario, plan type, seed, saved results">
              <ActionIcon
                variant="default"
                size="xl"
                radius="xs"
                onClick={() => setSettingsOpen(true)}
                aria-label="Advanced settings"
              >
                <IconAdjustments size={20} stroke={1.8} />
              </ActionIcon>
            </Tooltip>

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

        {live && (
          <Alert color="green" variant="light" mt="sm" title={`Showing the best plan so far (version ${live.version}) · still looking for a better one`}>
            Profit after all costs so far: ₹{Math.round(live.net_inr).toLocaleString('en-IN')} · {live.elapsed_s} s of searching
          </Alert>
        )}

        {error && (
          <Alert color="red" icon={<IconAlertTriangle />} title="Something went wrong" mt="sm">
            {error}
          </Alert>
        )}
      </Paper>

      {/* 2. OPERATIONAL NAVIGATION TABS */}
      <div className="dashboard-nav-strip">
        <Tabs value={activeTab} onChange={(val) => val && setActiveTab(val)} color="green">
          <Tabs.List className="dashboard-tabs-list">
            <Tabs.Tab value="overview" leftSection={<IconTrendingUp size={18} />}>
              1. RESULTS
            </Tabs.Tab>
            <Tabs.Tab value="trucks" leftSection={<IconTruck size={18} />}>
              2. TODAY'S PLAN
            </Tabs.Tab>
            <Tabs.Tab value="disruptions" leftSection={<IconRoute size={18} />}>
              3. WHAT IF SOMETHING BREAKS?
            </Tabs.Tab>
            <Tabs.Tab value="audit" leftSection={<IconShieldCheck size={18} />}>
              4. PROOF &amp; AUDIT
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
            <Title order={3}>NO PLAN YET</Title>
            <Text size="sm" c="dimmed" maw={460} mx="auto" mt={8} mb="xl">
              Click Run the optimiser to make one. FreshRoute decides where each of the 200 batches goes across the 8 markets. A first plan appears in about 1 second.
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
                      <Title order={4}>What if something breaks mid-day?</Title>
                      <Text size="xs" c="dimmed">
                        How to use: close a road on the map, break down a{' '}
                        <Explain term="reefer">cold truck</Explain> or add a demand spike. FreshRoute re-plans the rest of
                        the day in a few seconds and shows what changed.
                      </Text>
                    </div>
                    <Badge color="blue" variant="light">
                      SOLVER LIMIT 2 S PER RE-PLAN
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
        title="Advanced settings"
        position="right"
        size="md"
      >
        <Stack gap="md">
          <Text size="xs" c="dimmed">
            Change what the optimiser plans for. The defaults run FreshRoute on the practice scenario, which is the
            setup every result on this page uses.
          </Text>

          <Select
            label="Scenario"
            value={scenario}
            onChange={(v) => v && setScenario(v)}
            data={scenarios.map((s) => ({ value: s.name, label: `${scenarioName(s.name)} (${s.horizon_days} days)` }))}
            allowDeselect={false}
          />

          <Select
            label="How to plan"
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
            description="Same seed, same result, every time"
            value={seed}
            onChange={(v) => setSeed(Number(v))}
            allowDecimal={false}
          />

          <Switch
            label={<Explain term="newsvendor">Ship more or less than forecast (newsvendor)</Explain>}
            description="Aims a little above or below expected demand, whichever loses less money"
            checked={newsvendor}
            onChange={(e) => setNewsvendor(e.currentTarget.checked)}
          />

          <div style={{ marginTop: 16 }}>
            <Text size="xs" fw={700} mb="xs">
              SAVED RESULTS
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
            Save and close
          </Button>
        </Stack>
      </Drawer>
    </div>
  )
}
