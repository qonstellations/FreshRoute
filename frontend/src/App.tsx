// Friendly 3-step flow (ARCHITECTURE §16): 1 Make a plan → 2 See results → 3 What if?
// Renders API JSON verbatim; the engine decides, this page only shows.
import {
  Accordion, ActionIcon, AppShell, Badge, Card, Container, Group, NumberInput, Paper, Select, SimpleGrid, Stack, Stepper,
  Switch, Text, Title, Tooltip, useMantineColorScheme,
} from '@mantine/core'
import {
  IconChartBar, IconFlask, IconLeaf, IconMoon, IconSparkles, IconSun, IconTruck,
} from '@tabler/icons-react'
import { AnimatePresence, m } from 'motion/react'
import { useCallback, useEffect, useState } from 'react'
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

// ponytail: run_id of backend/tests/fixtures/metrics_example.json, used when /api/runs is empty + fixture
const FIXTURE_RUN_ID = 'EXAMPLE-SYNTHETIC'
const POLICIES = [
  { value: 'milp_markdown', label: 'Smart plan (recommended)' },
  { value: 'milp', label: 'Smart plan, no discounts' },
  { value: 'fefo', label: 'Use oldest first (simple rule)' },
  { value: 'fifo', label: 'Use newest first (simple rule)' },
  { value: 'last_day_50', label: 'Simple rule + big last-day sale' },
]
const STEPS = [
  { label: 'Make a plan', icon: <IconSparkles size={18} /> },
  { label: 'See results', icon: <IconChartBar size={18} /> },
  { label: 'What if?', icon: <IconFlask size={18} /> },
]

function SectionTitle({ icon, title, sub }: { icon: React.ReactNode; title: string; sub: string }) {
  return (
    <Group gap="sm" mt="xl" mb="xs">
      <m.span initial={{ scale: 0, rotate: -30 }} animate={{ scale: 1, rotate: 0 }} transition={spring.bouncy}>
        {icon}
      </m.span>
      <div>
        <Title order={3}>{title}</Title>
        <Text size="sm" c="dimmed">{sub}</Text>
      </div>
    </Group>
  )
}

export default function App() {
  const [step, setStep] = useState(() => {
    const q = Number(new URLSearchParams(location.search).get('step'))
    return q >= 1 && q <= 3 ? q - 1 : 0
  })
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('fr-stage') === '1' } catch { return false }
  })
  const { setColorScheme } = useMantineColorScheme()
  useEffect(() => {
    document.documentElement.toggleAttribute('data-stage', dark)
    setColorScheme(dark ? 'dark' : 'light')
    try { localStorage.setItem('fr-stage', dark ? '1' : '0') } catch { /* private window */ }
  }, [dark, setColorScheme])
  useEffect(() => {
    const q = new URLSearchParams(location.search)
    q.set('step', String(step + 1))
    history.replaceState(null, '', `?${q}`)
  }, [step])

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
    api.scenarios().then(s => { setScenarios(s); setScenario(v => v || s.find(x => x.name === 'practice')?.name || s[0]?.name || '') })
      .catch(e => setError(`Cannot list scenarios: ${e.message}`))
    loadRuns()
  }, [loadRuns])

  useEffect(() => {
    if (!runId) return setRun(null)
    api.run(runId).then(r => { setRun(r); setError('') })
      .catch(e => setError(`Cannot load run ${runId}: ${e.message}`))
  }, [runId])

  const fixture = runs.fixture || !!run?.fixture
  const info = run && scenarios.find(s => s.name === run.scenario || run.scenario.endsWith(`/${s.name}`))
  const synthetic = fixture || (!!run && (!info || info.source === 'synthetic'))

  const pickRun = (id: string) => { setRunId(id); setStep(1) }

  return (
    <AppShell header={{ height: 64 }} padding="lg">
      <AppShell.Header className="shell-header">
        <m.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={spring.snappy} style={{ height: '100%' }}>
          <Group h="100%" px="lg" justify="space-between" style={{ position: 'relative' }}>
            <Group gap={10}>
              <IconLeaf size={28} color="var(--mantine-color-green-7)" stroke={2.2} />
              <Title order={2} className="wordmark">FreshRoute</Title>
              <Text size="sm" c="dimmed" visibleFrom="sm">fresh produce, planned in one click</Text>
            </Group>
            <Group gap="xs">
              <AnimatePresence>
                {synthetic && (
                  <m.div key="syn" initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }} transition={spring.bouncy}>
                    <Badge color="yellow" variant="filled" size="lg"
                      styles={{ root: { color: 'var(--mantine-color-dark-7)' } }}>demo data</Badge>
                  </m.div>
                )}
              </AnimatePresence>
              <Tooltip label={dark ? 'Light mode' : 'Dark mode for the projector'}>
                <ActionIcon variant="subtle" size="lg" radius="xl" aria-label="Toggle dark mode"
                  onClick={() => setDark(v => !v)}>{dark ? <IconSun size={20} /> : <IconMoon size={20} />}</ActionIcon>
              </Tooltip>
            </Group>
          </Group>
        </m.div>
      </AppShell.Header>

      <AppShell.Main>
        <Container size="lg">
          <Stack gap="xs" mb="md">
            <SyntheticBanner show={synthetic} />
            <StatusBanner fixture={fixture} manifest={run?.manifest ?? null} error={error} />
          </Stack>

          <Stepper active={step} onStepClick={setStep} mb="xl" allowNextStepsSelect={!!run}>
            {STEPS.map((s, i) => (
              <Stepper.Step key={s.label} label={s.label} icon={s.icon}
                allowStepSelect={i === 0 || !!run} />
            ))}
          </Stepper>

          <AnimatePresence mode="wait" initial={false}>
            <m.div key={step} initial={{ opacity: 0, x: 32 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -32 }} transition={spring.snappy}>
              {step === 0 && (
                <Stack gap="lg">
                  <Paper radius="lg" p="xl" className="hero">
                    <m.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={spring.soft}>
                      <Title order={2} c="white">Where should today's fresh stock go?</Title>
                      <Text c="white" opacity={0.9} mt={4}>
                        Pick a place below, press the big button, and watch the plan appear.
                      </Text>
                    </m.div>
                  </Paper>

                  <div>
                    <Title order={4} mb="xs">1 · Pick a place</Title>
                    <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="sm">
                      {scenarios.map(s => {
                        const on = s.name === scenario
                        return (
                          <m.div key={s.name} whileHover={{ y: -3 }} whileTap={{ scale: 0.97 }} transition={spring.snappy}>
                            <Card withBorder radius="lg" p="md" onClick={() => setScenario(s.name)}
                              className="pick-card" data-on={on} style={{ cursor: 'pointer' }}>
                              <Group gap="xs">
                                <IconTruck size={22} color={on ? 'var(--mantine-color-green-7)' : 'var(--mantine-color-dimmed)'} />
                                <div>
                                  <Text fw={700}>{s.name}</Text>
                                  <Text size="xs" c="dimmed">{s.source} · {s.horizon_days}-day plan</Text>
                                </div>
                              </Group>
                            </Card>
                          </m.div>
                        )
                      })}
                    </SimpleGrid>
                  </div>

                  <div>
                    <Title order={4} mb="xs">2 · Press the button</Title>
                    <m.div whileTap={{ scale: 0.98 }} transition={spring.snappy} style={{ maxWidth: 420 }}>
                      <RunButton
                        request={{ scenario: scenario && `data/scenarios/${scenario}`, policy, seed, flags: { markdown, newsvendor } }}
                        onDone={id => { loadRuns(id); setStep(1) }} onError={setError} />
                    </m.div>
                    <Text size="sm" c="dimmed" mt="xs">Takes about half a minute. We jump to the results by themselves.</Text>
                  </div>

                  <Accordion variant="separated" radius="md">
                    <Accordion.Item value="advanced">
                      <Accordion.Control>Advanced settings (you can ignore these)</Accordion.Control>
                      <Accordion.Panel>
                        <Stack gap="sm" maw={420}>
                          <Select label="Planning method" value={policy} onChange={v => v && setPolicy(v)}
                            allowDeselect={false} data={POLICIES} />
                          <NumberInput label="Seed (same seed = same plan)" value={seed}
                            onChange={v => setSeed(Number(v))} allowDecimal={false} />
                          <Switch label="Discount items about to expire" checked={markdown}
                            onChange={e => setMarkdown(e.currentTarget.checked)} />
                          <Switch label="Order cautiously (newsvendor)" checked={newsvendor}
                            onChange={e => setNewsvendor(e.currentTarget.checked)} />
                        </Stack>
                      </Accordion.Panel>
                    </Accordion.Item>
                    <Accordion.Item value="recent">
                      <Accordion.Control>Look at an older plan</Accordion.Control>
                      <Accordion.Panel>
                        <RunPicker runs={runs.runs} value={runId} onChange={pickRun} />
                      </Accordion.Panel>
                    </Accordion.Item>
                  </Accordion>
                </Stack>
              )}

              {step === 1 && (run && runId ? (
                <Stack gap="md">
                  <SectionTitle icon={<IconChartBar size={26} color="var(--mantine-color-green-7)" />}
                    title="Your score" sub="Profit, waste and deliveries — compared with the simple rule." />
                  <Scoreboard run={run} />
                  <SectionTitle icon={<IconTruck size={26} color="var(--mantine-color-green-7)" />}
                    title="Where every truck goes" sub="Tap any row to see why it was chosen." />
                  <Plan run={run} runId={runId} />
                </Stack>
              ) : (
                <Paper withBorder radius="lg" p="xl" ta="center">
                  <Text fw={600}>No plan yet.</Text>
                  <Text size="sm" c="dimmed" mb="md">Go back one step and press the big button.</Text>
                </Paper>
              ))}

              {step === 2 && (run && runId ? (
                <Stack gap="md">
                  <SectionTitle icon={<IconFlask size={26} color="var(--mantine-color-green-7)" />}
                    title="Try a problem" sub="A road closes, a truck breaks — see the new plan in seconds." />
                  <Replan run={run} runId={runId} />
                  <SectionTitle icon={<IconChartBar size={26} color="var(--mantine-color-green-7)" />}
                    title="How sturdy is it?" sub="The same plan, tested against 200 possible tomorrows." />
                  <Robustness run={run} runId={runId} />
                  <Accordion variant="separated" radius="md">
                    <Accordion.Item value="trust">
                      <Accordion.Control>Can I trust this plan?</Accordion.Control>
                      <Accordion.Panel><Trust run={run} /></Accordion.Panel>
                    </Accordion.Item>
                  </Accordion>
                </Stack>
              ) : (
                <Paper withBorder radius="lg" p="xl" ta="center">
                  <Text fw={600}>No plan yet.</Text>
                  <Text size="sm" c="dimmed" mb="md">Make a plan first, then come back and break it.</Text>
                </Paper>
              ))}
            </m.div>
          </AnimatePresence>

          <Text size="xs" c="dimmed" ta="center" mt="xl">
            Every number comes from the planning engine. Demo data is not real.
          </Text>
        </Container>
      </AppShell.Main>
    </AppShell>
  )
}
