// Atelier-style scroll experience (ARCHITECTURE §16, D-27): one page, giant type,
// numbered sections, GSAP ScrollTrigger reveals. Renders API JSON verbatim;
// the engine decides, this page only shows.
import {
  Accordion, ActionIcon, AppShell, Badge, Card, Group, NumberInput, Paper, Select, SimpleGrid, Stack, Switch, Text,
  Title, Tooltip, useMantineColorScheme,
} from '@mantine/core'
import { IconArrowDown, IconLeaf, IconMoon, IconSun, IconTruck } from '@tabler/icons-react'
import { gsap } from 'gsap'
import { ScrollToPlugin } from 'gsap/ScrollToPlugin'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { api } from './api/client'
import { StatusBanner, SyntheticBanner } from './components/Banners'
import { RunButton } from './components/RunButton'
import { RunPicker } from './components/RunPicker'
import { Plan } from './tabs/Plan'
import { Replan } from './tabs/Replan'
import { Robustness } from './tabs/Robustness'
import { Scoreboard } from './tabs/Scoreboard'
import { Trust } from './tabs/Trust'
import type { RunDetail, RunsList, ScenarioInfo } from './types'

gsap.registerPlugin(ScrollTrigger, ScrollToPlugin)

// ponytail: run_id of backend/tests/fixtures/metrics_example.json, used when /api/runs is empty + fixture
const FIXTURE_RUN_ID = 'EXAMPLE-SYNTHETIC'
const POLICIES = [
  { value: 'milp_markdown', label: 'Smart plan (recommended)' },
  { value: 'milp', label: 'Smart plan, no discounts' },
  { value: 'fefo', label: 'Use oldest first (simple rule)' },
  { value: 'fifo', label: 'Use newest first (simple rule)' },
  { value: 'last_day_50', label: 'Simple rule + big last-day sale' },
]
const NAV = [
  { id: 'plan', n: '01', label: 'Plan' },
  { id: 'score', n: '02', label: 'Score' },
  { id: 'trucks', n: '03', label: 'Trucks' },
  { id: 'whatif', n: '04', label: 'What if' },
  { id: 'trust', n: '05', label: 'Trust' },
]

export const scrollTo = (id: string) => {
  gsap.to(window, { duration: 1.1, ease: 'power3.inOut', scrollTo: { y: `#${id}`, offsetY: 70 } })
}

function SectionHead({ n, tag, title, sub }: { n: string; tag: string; title: string; sub: string }) {
  return (
    <div data-reveal>
      <Text className="sec-tag">[{tag}]</Text>
      <Title order={2} className="sec-title"><span className="sec-n">{n}</span> {title}</Title>
      <Text c="dimmed" mt={4} maw={640}>{sub}</Text>
    </div>
  )
}

export default function App() {
  const root = useRef<HTMLDivElement>(null)
  const [dark, setDark] = useState(() => {
    try { return localStorage.getItem('fr-stage') === '1' } catch { return false }
  })
  const { setColorScheme } = useMantineColorScheme()
  useEffect(() => {
    document.documentElement.toggleAttribute('data-stage', dark)
    setColorScheme(dark ? 'dark' : 'light')
    try { localStorage.setItem('fr-stage', dark ? '1' : '0') } catch { /* private window */ }
  }, [dark, setColorScheme])

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
      // prefer the demo run (practice / milp_markdown), else the newest listing
      const demo = r.runs.find(x => x.scenario.split('/').pop() === 'practice' && x.policy === 'milp_markdown')
      setRunId(select ?? demo?.run_id ?? r.runs[0]?.run_id ?? (r.fixture ? FIXTURE_RUN_ID : null))
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
  useEffect(() => { ScrollTrigger.refresh() }, [runId])

  // GSAP world: hero intro, parallax, reveals, marquee. Reduced motion = static page.
  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
      gsap.from('.hero-line', { yPercent: 110, duration: 1.2, ease: 'power4.out', stagger: 0.12 })
      gsap.from('.hero-fade', { opacity: 0, y: 24, duration: 1, ease: 'power3.out', stagger: 0.1, delay: 0.5 })
      gsap.to('.hero-inner', {
        yPercent: -12, opacity: 0.25, ease: 'none',
        scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true },
      })
      gsap.utils.toArray<HTMLElement>('[data-reveal]').forEach(el => {
        gsap.from(el, {
          opacity: 0, y: 48, duration: 1, ease: 'power3.out',
          scrollTrigger: { trigger: el, start: 'top 88%', once: true },
        })
      })
      gsap.to('.marquee-track', { xPercent: -50, duration: 22, ease: 'none', repeat: -1 })
    }, root)
    return () => ctx.revert()
  }, [])

  const fixture = runs.fixture || !!run?.fixture
  const info = run && scenarios.find(s => s.name === run.scenario || run.scenario.endsWith(`/${s.name}`))
  const synthetic = fixture || (!!run && (!info || info.source === 'synthetic'))
  const ready = run && runId

  return (
    <div ref={root}>
      <AppShell header={{ height: 60 }} padding={0}>
        <AppShell.Header className="atelier-header">
          <Group h="100%" px="lg" justify="space-between">
            <Group gap={8} style={{ cursor: 'pointer' }} onClick={() => gsap.to(window, { duration: 1, scrollTo: 0 })}>
              <IconLeaf size={22} color="var(--mantine-color-green-7)" stroke={2.2} />
              <Text fw={800} className="wordmark-sm">FreshRoute</Text>
            </Group>
            <Group gap={4} visibleFrom="sm">
              {NAV.map(n => (
                <button key={n.id} className="atelier-nav" onClick={() => scrollTo(n.id)}>
                  <span className="atelier-nav-n">{n.n}</span> {n.label}
                </button>
              ))}
            </Group>
            <Group gap="xs">
              {synthetic && <Badge color="yellow" variant="filled" size="md"
                styles={{ root: { color: 'var(--mantine-color-dark-7)' } }}>demo data</Badge>}
              <Tooltip label={dark ? 'Light mode' : 'Dark mode for the projector'}>
                <ActionIcon variant="subtle" size="lg" radius="xl" aria-label="Toggle dark mode"
                  onClick={() => setDark(v => !v)}>{dark ? <IconSun size={20} /> : <IconMoon size={20} />}</ActionIcon>
              </Tooltip>
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Main>
          {/* HERO */}
          <section className="hero">
            <div className="hero-inner">
              <Text className="hero-kicker hero-fade">[ fresh produce · planned in one click ]</Text>
              <h1 className="display" aria-label="FreshRoute">
                <span className="hero-mask"><span className="hero-line">FRESH</span></span>
                <span className="hero-mask"><span className="hero-line outline">ROUTE</span></span>
              </h1>
              <Text className="hero-sub hero-fade" maw={620}>
                Which batch goes where, when, and at what markdown — decided by
                an optimizer, explained in plain words, re-planned in seconds
                when the day goes wrong.
              </Text>
              <Group mt="xl" className="hero-fade">
                <button className="atelier-cta" onClick={() => scrollTo('plan')}>
                  Make a plan <IconArrowDown size={18} />
                </button>
                <button className="atelier-ghost" onClick={() => scrollTo('score')}>See what it says</button>
              </Group>
              <Stack gap={4} mt={48} mb={16} className="hero-fade">
                <SyntheticBanner show={synthetic} />
                <StatusBanner fixture={fixture} manifest={run?.manifest ?? null} error={error} />
              </Stack>
            </div>
          </section>

          {/* MARQUEE */}
          <div className="marquee" aria-hidden>
            <div className="marquee-track">
              {[0, 1].map(k => (
                <span key={k} className="marquee-chunk">PLAN · SCORE · TRUCKS · WHAT IF · TRUST ·&nbsp;</span>
              ))}
            </div>
          </div>

          {/* 01 PLAN */}
          <section id="plan" className="atelier-sec">
            <SectionHead n="01" tag="PLAN" title="Where should today's stock go?"
              sub="Pick a place, press the button, and the plan appears below. About half a minute." />
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="sm" mt="lg" data-reveal>
              {scenarios.map(s => {
                const on = s.name === scenario
                return (
                  <Card key={s.name} withBorder radius="lg" p="md" onClick={() => setScenario(s.name)}
                    className="pick-card" data-on={on} style={{ cursor: 'pointer' }}>
                    <Group gap="xs">
                      <IconTruck size={22} color={on ? 'var(--mantine-color-green-7)' : 'var(--mantine-color-dimmed)'} />
                      <div>
                        <Text fw={700}>{s.name}</Text>
                        <Text size="xs" c="dimmed">{s.source} · {s.horizon_days}-day plan</Text>
                      </div>
                    </Group>
                  </Card>
                )
              })}
            </SimpleGrid>
            <div data-reveal style={{ maxWidth: 640 }} className="plan-cta">
              <RunButton
                request={{ scenario: scenario && `data/scenarios/${scenario}`, policy, seed, flags: { markdown, newsvendor } }}
                onDone={id => { loadRuns(id); setTimeout(() => scrollTo('score'), 600) }} onError={setError} />
            </div>
            <Accordion variant="separated" radius="md" mt="md" maw={560} data-reveal>
              <Accordion.Item value="advanced">
                <Accordion.Control>Advanced settings (you can ignore these)</Accordion.Control>
                <Accordion.Panel>
                  <Stack gap="sm">
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
                <Accordion.Panel><RunPicker runs={runs.runs} value={runId} onChange={setRunId} /></Accordion.Panel>
              </Accordion.Item>
            </Accordion>
          </section>

          {/* 02 SCORE */}
          <section id="score" className="atelier-sec">
            <SectionHead n="02" tag="SCORE" title="Your score"
              sub="Profit, waste and deliveries — measured against the simple rule." />
            <div data-reveal className="sec-body">
              {ready ? <Scoreboard run={run} /> : <PlanGate onPlan={() => scrollTo('plan')} />}
            </div>
          </section>

          {/* 03 TRUCKS */}
          <section id="trucks" className="atelier-sec">
            <SectionHead n="03" tag="TRUCKS" title="Where every truck goes"
              sub="Tap any row to see why it was chosen over the alternatives." />
            <div data-reveal className="sec-body">
              {ready ? <Plan run={run} runId={runId} /> : <PlanGate onPlan={() => scrollTo('plan')} />}
            </div>
          </section>

          {/* 04 WHAT IF */}
          <section id="whatif" className="atelier-sec">
            <SectionHead n="04" tag="WHAT IF" title="When the day goes wrong"
              sub="A road closes, a truck breaks — a new plan in seconds, tested against 200 possible tomorrows." />
            <div data-reveal className="sec-body">
              {ready ? (
                <Stack gap="xl">
                  <Replan run={run} runId={runId} />
                  <Robustness run={run} runId={runId} />
                </Stack>
              ) : <PlanGate onPlan={() => scrollTo('plan')} />}
            </div>
          </section>

          {/* 05 TRUST */}
          <section id="trust" className="atelier-sec">
            <SectionHead n="05" tag="TRUST" title="Can you trust it?"
              sub="An independent checker re-does the maths. Every number traces to the engine." />
            <div data-reveal className="sec-body">
              {ready ? <Trust run={run} /> : <PlanGate onPlan={() => scrollTo('plan')} />}
            </div>
          </section>

          <footer className="atelier-foot">
            <Text fw={800} className="foot-word">FRESHROUTE</Text>
            <Text size="sm" c="dimmed">Every number comes from the planning engine. Demo data is not real.</Text>
          </footer>
        </AppShell.Main>
      </AppShell>
    </div>
  )
}

function PlanGate({ onPlan }: { onPlan: () => void }) {
  return (
    <Paper withBorder radius="lg" p="xl" ta="center">
      <Text fw={600}>No plan yet.</Text>
      <Text size="sm" c="dimmed" mb="md">Make one first — it takes about half a minute.</Text>
      <button className="atelier-cta" onClick={onPlan}>Make a plan</button>
    </Paper>
  )
}
