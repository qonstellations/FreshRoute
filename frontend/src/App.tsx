// Atelier-style scroll experience (ARCHITECTURE §16, D-27): one page, Anton display,
// Kode Mono labels, GSAP ScrollTrigger choreography. Renders API JSON verbatim;
// the engine decides, this page only shows.
//
// GSAP patterns per skills (gsap-react, gsap-scrolltrigger): single
// gsap.context() scoped to this root with ctx.revert() cleanup; gsap.matchMedia()
// for reduced-motion; ScrollTrigger.batch() for reveals with top-to-bottom
// refreshPriority; scrub and toggleActions never mixed on one trigger.
import {
  Accordion, AppShell, Badge, Card, Group, NumberInput, Paper, Select, SimpleGrid, Stack, Switch, Text,
} from '@mantine/core'
import { IconArrowDown, IconArrowUp, IconArrowUpRight, IconLeaf, IconTruck } from '@tabler/icons-react'
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
  gsap.to(window, { duration: 1.1, ease: 'power3.inOut', scrollTo: { y: `#${id}`, offsetY: 64 } })
}

function DupTitle({ ghost, solid }: { ghost: [string, string]; solid: [string, string] }) {
  return (
    <h2 className="dup-title" aria-label={`${solid[0]} ${solid[1]}`}>
      <span className="ghost">{ghost[0]}<br />{ghost[1]}</span>
      <span className="solid" data-wipe>{solid[0]}<br />{solid[1]}</span>
    </h2>
  )
}

function SectionHead({ n, tag, ghost, solid, sub, dark }: {
  n: string; tag: string; ghost: [string, string]; solid: [string, string]; sub: string; dark?: boolean
}) {
  return (
    <div data-reveal>
      <Text className="sec-tag">[{tag}]</Text>
      <Text className="sec-n">{n}</Text>
      <DupTitle ghost={ghost} solid={solid} />
      <Text mt={12} maw={560} size="sm" className={dark ? 'sec-sub' : undefined} c={dark ? undefined : 'dimmed'}>{sub}</Text>
    </div>
  )
}

export default function App() {
  const root = useRef<HTMLDivElement>(null)

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

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const mm = gsap.matchMedia()
      // full motion, incl. pin-free scrub wipes; reduced motion gets the static page
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        // hero lines grow down from nothing, like the reference fv title
        gsap.from('.hero-line', { scaleY: 0, duration: 1.3, ease: 'power4.out', stagger: 0.12 })
        gsap.from('.hero-fade', { opacity: 0, y: 24, duration: 0.9, ease: 'power3.out', stagger: 0.09, delay: 0.55 })
        gsap.to('.hero-inner', {
          yPercent: -10, ease: 'none',
          scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true, refreshPriority: 1 },
        })
        // one coordinated reveal batch for everything entering the viewport
        ScrollTrigger.batch('[data-reveal]', {
          start: 'top 90%', once: true,
          onEnter: batch => gsap.fromTo(batch, { opacity: 0, y: 44 },
            { opacity: 1, y: 0, duration: 0.9, ease: 'power3.out', stagger: 0.08, overwrite: true }),
        })
        // doubled titles: the solid copy wipes in with the scroll
        gsap.utils.toArray<HTMLElement>('[data-wipe]').forEach(el => {
          gsap.fromTo(el, { clipPath: 'polygon(0 0, 0 0, 0 100%, 0 100%)' },
            {
              clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%)', ease: 'none',
              scrollTrigger: { trigger: el, start: 'top 85%', end: 'top 35%', scrub: 0.6, refreshPriority: 2 },
            })
        })
        gsap.to('.marquee-track', { xPercent: -50, duration: 26, ease: 'none', repeat: -1 })
      })
      return () => mm.revert()
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
              <IconLeaf size={22} color="var(--ink)" stroke={2.2} />
              <Text className="wordmark-sm">FRESHROUTE</Text>
            </Group>
            <Group gap={8} visibleFrom="sm">
              {NAV.map(n => (
                <button key={n.id} className="atelier-nav" onClick={() => scrollTo(n.id)}>
                  <span className="fill" aria-hidden />
                  <span><span className="atelier-nav-n">{n.n}</span>{n.label.toUpperCase()}</span>
                </button>
              ))}
            </Group>
            <Group gap="xs">
              {synthetic && <Badge color="yellow" variant="filled" size="md"
                styles={{ root: { color: '#222' } }}>DEMO DATA</Badge>}
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Main>
          {/* HERO — fv style: kicker, giant title, vision, email-block CTA, labels + index */}
          <section className="hero">
            <div className="hero-inner">
              <Text className="hero-kicker hero-fade">[FRESH PRODUCE — PLANNED IN ONE CLICK]</Text>
              <h1 className="display" aria-label="FreshRoute">
                <span className="hero-mask"><span className="hero-line">FRESH</span></span>
                <span className="hero-mask"><span className="hero-line outline">ROUTE</span></span>
              </h1>
              <div className="hero-vision hero-fade">
                <Text size="sm">[VISION]</Text>
                <Text className="hero-sub">Which batch goes where, when, and at what markdown.
                  Decided by an optimizer, explained in plain words, re-planned in
                  seconds when the day goes wrong.</Text>
              </div>
              <Group mt="lg" className="hero-fade">
                <button className="atelier-cta" onClick={() => scrollTo('plan')}>
                  <span className="cta-mask"><span className="cta-label">MAKE A PLAN</span><span className="cta-clone">MAKE A PLAN</span></span>
                  <span className="cta-div" aria-hidden />
                  <IconArrowDown size={14} />
                </button>
              </Group>
              <Stack gap={4} mt="lg" className="hero-fade">
                <SyntheticBanner show={synthetic} />
                <StatusBanner fixture={fixture} manifest={run?.manifest ?? null} error={error} />
              </Stack>
              <div className="hero-fade">
                <div className="hero-labels">
                  <span>SCROLL<span>[↓]</span></span>
                  <span>INDEX<span>[+]</span></span>
                  <span>SCROLL<span>[↓]</span></span>
                </div>
                <div className="hero-index">
                  {[
                    { id: 'plan', tag: '[01]', label: 'MAKE A PLAN' },
                    { id: 'score', tag: '[02]', label: 'SEE THE SCORE' },
                    { id: 'whatif', tag: '[03]', label: 'BREAK IT' },
                    { id: 'trust', tag: '[04]', label: 'TRUST IT' },
                  ].map(c => (
                    <button key={c.id} className="hero-cell" onClick={() => scrollTo(c.id)}>
                      <small>{c.tag}</small><big>{c.label}</big>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* MARQUEE */}
          <div className="marquee" aria-hidden>
            <div className="marquee-track">
              {[0, 1].map(k => (
                <span key={k} className="marquee-chunk">FRESH · PLANNED · EXPLAINED · RE-PLANNED ·&nbsp;</span>
              ))}
            </div>
          </div>

          {/* 01 PLAN */}
          <section id="plan" className="atelier-sec">
            <SectionHead n="01" tag="PLAN" ghost={['WHERE SHOULD', "TODAY'S GO?"]} solid={['WHERE SHOULD', "TODAY'S GO?"]}
              sub="Pick a place, press the button, and the plan appears below. About half a minute." />
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="sm" mt="lg" data-reveal>
              {scenarios.map((s, i) => {
                const on = s.name === scenario
                return (
                  <Card key={s.name} withBorder p="md" onClick={() => setScenario(s.name)}
                    className="pick-card" data-on={on} style={{ cursor: 'pointer' }}>
                    <Text className="pick-num">({String(i + 1).padStart(2, '0')})</Text>
                    <Group gap="xs" mt={6}>
                      <IconTruck size={22} color={on ? 'var(--cream)' : 'var(--ink)'} />
                      <div>
                        <Text fw={700}>{s.name}</Text>
                        <Text size="xs" className={on ? 'dim' : undefined} c={on ? undefined : 'dimmed'}>{s.source} · {s.horizon_days}-day plan</Text>
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
            <Accordion variant="separated" mt="md" maw={560} data-reveal>
              <Accordion.Item value="advanced">
                <Accordion.Control>ADVANCED SETTINGS (YOU CAN IGNORE THESE)</Accordion.Control>
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
                <Accordion.Control>LOOK AT AN OLDER PLAN</Accordion.Control>
                <Accordion.Panel><RunPicker runs={runs.runs} value={runId} onChange={setRunId} /></Accordion.Panel>
              </Accordion.Item>
            </Accordion>
          </section>

          {/* 02 SCORE */}
          <section id="score" className="atelier-sec">
            <SectionHead n="02" tag="SCORE" ghost={['YOUR', 'SCORE']} solid={['YOUR', 'SCORE']}
              sub="Profit, waste and deliveries — measured against the simple rule." />
            <div data-reveal className="sec-body">
              {ready ? <Scoreboard run={run} /> : <PlanGate onPlan={() => scrollTo('plan')} />}
            </div>
          </section>

          {/* 03 TRUCKS */}
          <section id="trucks" className="atelier-sec">
            <SectionHead n="03" tag="TRUCKS" ghost={['EVERY', 'TRUCK']} solid={['EVERY', 'TRUCK']}
              sub="Tap any row to see why it was chosen over the alternatives." />
            <div data-reveal className="sec-body">
              {ready ? <Plan run={run} runId={runId} /> : <PlanGate onPlan={() => scrollTo('plan')} />}
            </div>
          </section>

          {/* 04 WHAT IF */}
          <section id="whatif" className="atelier-sec">
            <SectionHead n="04" tag="WHAT IF" ghost={['WHEN THE', 'DAY BREAKS']} solid={['WHEN THE', 'DAY BREAKS']}
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

          {/* 05 TRUST — dark, like the reference members section */}
          <section id="trust" className="atelier-sec sec-dark">
            <SectionHead n="05" tag="TRUST" ghost={['CAN YOU', 'TRUST IT?']} solid={['CAN YOU', 'TRUST IT?']}
              sub="An independent checker re-does the maths. Every number traces to the engine." dark />
            <div data-reveal className="sec-body">
              {ready ? <Trust run={run} /> : <PlanGate onPlan={() => scrollTo('plan')} />}
            </div>
          </section>

          <footer className="atelier-foot">
            <Text size="sm">[DEMO]</Text>
            <Text size="sm" maw={480}>Thank you for looking at our planner. Every number comes from
              the planning engine — demo data is not real. One click makes a plan.</Text>
            <button className="atelier-cta" onClick={() => scrollTo('plan')} style={{ margin: '24px 0 40px' }}>
              <span className="cta-mask"><span className="cta-label">MAKE A PLAN</span><span className="cta-clone">MAKE A PLAN</span></span>
              <span className="cta-div" aria-hidden />
              <IconArrowUpRight size={14} />
            </button>
            <Text size="sm">OUR HUB</Text>
            <Text size="sm">practice · seed 42 · runs offline</Text>
            <h2 className="foot-word">FRESHROUTE</h2>
            <div className="foot-meta">
              <div><Text size="xs">SYNTHETIC DATA, CALIBRATED FOR PLAUSIBILITY. POST-HARVEST STATISTICS ARE CONTEXT, NOT INPUTS.</Text></div>
              <div><Text size="xs">ENGINE: HiGHS MILP · ONE SEEDED COMMAND · INDEPENDENT VALIDATOR</Text></div>
              <div><Text size="xs">© 2026 FRESHROUTE</Text></div>
              <div style={{ textAlign: 'right' }}>
                <button className="top-link" onClick={() => gsap.to(window, { duration: 1.2, scrollTo: 0 })}>
                  BACK TO TOP<span>[↑]</span>
                </button>
              </div>
            </div>
          </footer>
        </AppShell.Main>
      </AppShell>
    </div>
  )
}

function PlanGate({ onPlan }: { onPlan: () => void }) {
  return (
    <Paper withBorder p="xl" ta="center">
      <Text fw={600}>NO PLAN YET.</Text>
      <Text size="sm" c="dimmed" mb="md">Make one first — it takes about half a minute.</Text>
      <button className="atelier-cta" onClick={onPlan}>
        <span className="cta-mask"><span className="cta-label">MAKE A PLAN</span><span className="cta-clone">MAKE A PLAN</span></span>
        <span className="cta-div" aria-hidden />
        <IconArrowUp size={14} />
      </button>
    </Paper>
  )
}
