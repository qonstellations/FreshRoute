import {
  Badge, Card, Group, Paper, SimpleGrid, Stack, Text, ThemeIcon, Title
} from '@mantine/core'
import {
  IconArrowRight, IconBolt, IconCertificate,
  IconCheck, IconFileCheck, IconLeaf, IconRoute, IconScale, IconShieldCheck,
  IconTag, IconThermometer
} from '@tabler/icons-react'
import { gsap } from 'gsap'
import { ScrollToPlugin } from 'gsap/ScrollToPlugin'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { Explain } from '../components/Explain'
import {
  LowPolyBanana, LowPolyCarrot, LowPolyMango, LowPolySpinach, LowPolyTomato
} from '../components/LowPolyProduce'
import { delta, fmt, fmtShare } from '../lib/delta'
import { policyName } from '../lib/words'
import type { Kpis, Ladder, StressResponse } from '../types'

gsap.registerPlugin(ScrollTrigger, ScrollToPlugin)

// The landing page quotes the demo run (practice, seed 42) from the served ladder/stress files, never literals.
const DEMO = { scenario: 'practice', seed: 42 }
const show = <T,>(v: T | null | undefined, f: (x: T) => string) => (v == null ? '—' : f(v))

interface LandingPageProps {
  onLaunch: () => void
}

export function LandingPage({ onLaunch }: LandingPageProps) {
  const root = useRef<HTMLDivElement>(null)
  const horizontalSectionRef = useRef<HTMLDivElement>(null)
  const horizontalTrackRef = useRef<HTMLDivElement>(null)
  const zoomTextRef = useRef<HTMLHeadingElement>(null)
  const [ladder, setLadder] = useState<Ladder | null>(null)
  const [stress, setStress] = useState<StressResponse | null>(null)
  useEffect(() => {
    api.ladder(DEMO.scenario, DEMO.seed).then(setLadder).catch(() => setLadder(null)) // no run on disk → dashes
    api.stress(DEMO.scenario, DEMO.seed).then(setStress).catch(() => setStress(null))
  }, [])
  const kpis = (p: string): Kpis | undefined => ladder
    ? [ladder.ladder.official_baseline, ...ladder.ladder.ladder, ...ladder.ladder.extras].find(e => e?.policy === p)?.kpis
    : undefined
  const ours = kpis('milp'), fefo = kpis('fefo'), fifo = kpis('fifo')
  const dNet = ours ? delta(ours.net_inr, fefo?.net_inr) : null
  const dSpoil = ours ? delta(ours.spoilage_kg, fefo?.spoilage_kg) : null
  const won = stress?.summary.share_plan_beats_baseline.net_inr

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const mm = gsap.matchMedia()

      mm.add('(prefers-reduced-motion: no-preference)', () => {
        // Hero text entrance
        gsap.from('.landing-hero-line', {
          scaleY: 0,
          duration: 1.1,
          ease: 'power4.out',
          stagger: 0.12,
        })

        gsap.from('.landing-hero-fade', {
          opacity: 0,
          y: 24,
          duration: 0.8,
          ease: 'power3.out',
          stagger: 0.08,
          delay: 0.35,
        })

        // Low-poly veggies floating ambient animation
        gsap.to('.floating-veggie-1', {
          y: -16,
          rotation: 8,
          duration: 4.2,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
        })
        gsap.to('.floating-veggie-2', {
          y: 14,
          rotation: -8,
          duration: 4.8,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          delay: 0.4,
        })
        gsap.to('.floating-veggie-3', {
          y: -12,
          rotation: 6,
          duration: 4.5,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          delay: 0.8,
        })
        gsap.to('.floating-veggie-4', {
          y: 16,
          rotation: -7,
          duration: 5.2,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut',
          delay: 0.6,
        })

        // Scroll reveals for cards
        ScrollTrigger.batch('[data-reveal]', {
          start: 'top 88%',
          once: true,
          onEnter: (batch) =>
            gsap.fromTo(
              batch,
              { opacity: 0, y: 32 },
              { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out', stagger: 0.08, overwrite: true }
            ),
        })

        // Doubled title wipes
        gsap.utils.toArray<HTMLElement>('[data-wipe]').forEach((el) => {
          gsap.fromTo(
            el,
            { clipPath: 'polygon(0 0, 0 0, 0 100%, 0 100%)' },
            {
              clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%)',
              ease: 'none',
              scrollTrigger: {
                trigger: el,
                start: 'top 85%',
                end: 'top 45%',
                scrub: 0.6,
              },
            }
          )
        })

        // Text Zoom-In on Scroll
        if (zoomTextRef.current) {
          gsap.fromTo(
            zoomTextRef.current,
            { scale: 0.75, opacity: 0.3 },
            {
              scale: 1.12,
              opacity: 1,
              ease: 'power2.out',
              scrollTrigger: {
                trigger: zoomTextRef.current,
                start: 'top 85%',
                end: 'center 50%',
                scrub: 1,
              },
            }
          )
        }

        // Horizontal Pinned Scroll for Section 02 (Workflow)
        if (horizontalSectionRef.current && horizontalTrackRef.current) {
          const track = horizontalTrackRef.current
          const totalWidth = track.scrollWidth - window.innerWidth + 120

          gsap.to(track, {
            x: () => -totalWidth,
            ease: 'none',
            scrollTrigger: {
              trigger: horizontalSectionRef.current,
              pin: true,
              scrub: 1,
              start: 'top top',
              end: () => `+=${totalWidth}`,
              invalidateOnRefresh: true,
            },
          })
        }

        // Marquee continuous loop
        gsap.to('.marquee-track', { xPercent: -50, duration: 25, ease: 'none', repeat: -1 })
      })

      return () => mm.revert()
    }, root)

    return () => ctx.revert()
  }, [])

  return (
    <div ref={root} className="landing-page">
      {/* 1. HERO SECTION */}
      <section className="landing-hero">
        {/* Ambient floating low-poly background produce (organic scatter across grid) */}
        <LowPolyTomato
          className="floating-veggie-1 veggie-glow"
          style={{ top: '14%', right: '16%', width: '120px', height: '120px', transform: 'rotate(-12deg)' }}
        />
        <LowPolyBanana
          className="floating-veggie-2 veggie-mid"
          style={{ top: '30%', left: '10%', width: '135px', height: '105px', transform: 'rotate(24deg)' }}
        />
        <LowPolyMango
          className="floating-veggie-3 veggie-dim"
          style={{ top: '8%', left: '55%', width: '85px', height: '105px', transform: 'rotate(15deg)' }}
        />
        <LowPolySpinach
          className="floating-veggie-4 veggie-mid"
          style={{ bottom: '26%', right: '28%', width: '115px', height: '140px', transform: 'rotate(-22deg)' }}
        />
        <LowPolyCarrot
          className="floating-veggie-1 veggie-dim"
          style={{ bottom: '18%', left: '32%', width: '80px', height: '105px', transform: 'rotate(35deg)' }}
        />
        <LowPolyTomato
          className="floating-veggie-3 veggie-glow"
          style={{ bottom: '28%', right: '6%', width: '68px', height: '68px', transform: 'rotate(8deg)' }}
        />

        <div className="landing-hero-inner">
          <Group gap="xs" className="landing-hero-fade">
            <span className="sec-tag">[DAILY DISPATCH PLANNER FOR FRESH PRODUCE]</span>
            <Badge color="green" variant="light" size="sm">
              SHELF-LIFE CHECK · BEST-PROFIT PLAN · RE-PLANS IN SECONDS
            </Badge>
          </Group>

          <h1 className="display landing-title" aria-label="FreshRoute">
            <span className="hero-mask">
              <span className="landing-hero-line">FRESH PRODUCE.</span>
            </span>
            <span className="hero-mask">
              <span className="landing-hero-line outline">SMARTER DISPATCH.</span>
            </span>
          </h1>

          <div className="landing-hero-fade" style={{ maxWidth: 660, marginTop: 18 }}>
            <Text size="xl" lh={1.6} fw={400} c="var(--text)">
              Every morning, a produce warehouse decides which crates go on which truck to which{' '}
              <Explain term="mandi">mandi</Explain> (wholesale market). Choose badly and tomatoes rot on the road.
              <strong> FreshRoute</strong> checks how long each batch will stay fresh, then picks the plan that earns
              the most without breaking a single delivery rule.
            </Text>
          </div>

          <Group mt={32} className="landing-hero-fade" gap="md">
            <button className="atelier-cta" onClick={onLaunch} data-cursor="OPEN">
              <span className="cta-mask">
                <span className="cta-label">OPEN THE LIVE DEMO</span>
                <span className="cta-clone">OPEN THE LIVE DEMO</span>
              </span>
              <span className="cta-div" aria-hidden />
              <IconArrowRight size={16} />
            </button>
          </Group>

          {/* Quick Metrics Bar: served demo numbers (practice, seed 42) */}
          <SimpleGrid cols={{ base: 2, sm: 4 }} mt={48} className="landing-hero-fade landing-quick-stats">
            <div className="landing-stat-cell" data-cursor="PROFIT">
              <Text className="landing-stat-num">{show(dNet, d => `+₹${fmt(d)}`)}</Text>
              <Text size="xs" c="var(--muted)" fw={600}>
                MORE PROFIT THAN THE <Explain term="fefo">EXPIRY-FIRST RULE</Explain>
              </Text>
            </div>
            <div className="landing-stat-cell" data-cursor="SPOILAGE">
              <Text className="landing-stat-num">{show(dSpoil, d => `${fmt(-d)} KG`)}</Text>
              <Text size="xs" c="var(--muted)" fw={600}>
                LESS FOOD SPOILED
              </Text>
            </div>
            <div className="landing-stat-cell" data-cursor="RULES">
              <Text className="landing-stat-num">{show(ours?.violations, String)}</Text>
              <Text size="xs" c="var(--muted)" fw={600}>
                <Explain term="violations">RULES BROKEN</Explain>
              </Text>
            </div>
            <div className="landing-stat-cell" data-cursor="RE-PLAN">
              <Text className="landing-stat-num">~3 SEC</Text>
              <Text size="xs" c="var(--muted)" fw={600}>
                TO RE-PLAN THE REST OF THE DAY (2 SEC SOLVER CAP)
              </Text>
            </div>
          </SimpleGrid>
          <Text size="xs" c="var(--muted)" mt={10} className="landing-hero-fade">
            Measured on our <Explain term="synthetic">synthetic</Explain> practice scenario (200 batches, 8 markets,
            3 days, seed 42), loaded from the latest saved run.
          </Text>
        </div>
      </section>

      {/* MARQUEE */}
      <div className="marquee" aria-hidden>
        <div className="marquee-track">
          {[0, 1].map((k) => (
            <span key={k} className="marquee-chunk">
              TOMATOES · MANGOES · SPINACH · BANANAS · ONIONS · POTATOES ·&nbsp;
            </span>
          ))}
        </div>
      </div>

      {/* 2. THE CRISIS SECTION */}
      <section id="crisis" className="atelier-sec" style={{ paddingBottom: 0, position: 'relative' }}>
        <LowPolyMango
          className="floating-veggie-2 veggie-mid"
          style={{ top: '8%', right: '22%', width: '105px', height: '130px', transform: 'rotate(-16deg)' }}
        />
        <LowPolyCarrot
          className="floating-veggie-4 veggie-dim"
          style={{ top: '35%', left: '12%', width: '75px', height: '100px', transform: 'rotate(28deg)' }}
        />
        <LowPolyTomato
          className="floating-veggie-1 veggie-glow"
          style={{ bottom: '18%', right: '35%', width: '90px', height: '90px', transform: 'rotate(14deg)' }}
        />
        <LowPolyBanana
          className="floating-veggie-3 veggie-mid"
          style={{ bottom: '8%', left: '26%', width: '120px', height: '95px', transform: 'rotate(-32deg)' }}
        />

        <div data-reveal>
          <Text className="sec-tag">[01 · THE PROBLEM]</Text>
          <h2 className="dup-title">
            <span className="ghost">WHY SIMPLE WAREHOUSE<br />RULES WASTE FOOD</span>
            <span className="solid" data-wipe>WHY SIMPLE WAREHOUSE<br />RULES WASTE FOOD</span>
          </h2>
          <Text mt={12} maw={620} size="lg" c="var(--muted)">
            Most warehouses ship stock in the order it arrived:{' '}
            <Explain term="fifo"><em>first in, first out (FIFO)</em></Explain>. That works for screws, not
            for tomatoes. Produce that sits in the heat or travels too far rots before anyone can buy it.
          </Text>
        </div>

        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mt={36}>
          <Paper withBorder p="xl" className="landing-card" data-reveal>
            <div>
              <Group gap="sm" mb="md">
                <ThemeIcon size={38} color="red" variant="light">
                  <IconScale size={20} />
                </ThemeIcon>
                <Title order={3} fz="1.4rem">The old way: ship by arrival order</Title>
              </Group>
              <Stack gap="xs" mb="sm">
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>Blind to freshness:</strong> It ships whatever came in first, even if a newer batch is about to go bad.
                </Text>
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>Blind to heat:</strong> Warm, un-cooled trucks make produce{' '}
                  <Explain term="q10">spoil much faster</Explain>, so long trips are risky.
                </Text>
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>The cost:</strong> Crates arrive too old to sell and get thrown away or turned down by buyers.
                </Text>
              </Stack>
            </div>
            <div className="landing-highlight bad" style={{ marginTop: 16 }}>
              <strong>In our test:</strong> {show(fifo?.violations, String)} broken delivery rules and{' '}
              {show(fifo?.spoilage_kg, v => `${fmt(v)} kg`)} of food spoiled.
            </div>
          </Paper>

          <Paper withBorder p="xl" className="landing-card" data-reveal>
            <div>
              <Group gap="sm" mb="md">
                <ThemeIcon size={38} color="green" variant="light">
                  <IconLeaf size={20} />
                </ThemeIcon>
                <Title order={3} fz="1.4rem">The FreshRoute way: plan around freshness</Title>
              </Group>
              <Stack gap="xs" mb="sm">
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>Tracks freshness:</strong> Works out how many hours each batch has left, counting
                  warehouse waiting time and the temperature of the truck.
                </Text>
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>Rules out bad trips:</strong> Drops any trip where the produce would arrive too old to
                  sell, before planning starts.
                </Text>
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>Picks the best plan:</strong> Weighs every truck, market and batch together for the
                  highest profit, within truck and market limits.
                </Text>
              </Stack>
            </div>
            <div className="landing-highlight good" style={{ marginTop: 16 }}>
              <strong>In our test:</strong> {show(ours?.violations, String)} broken rules and{' '}
              {show(dNet, d => `₹${fmt(d)}`)} more profit than the expiry-first rule.
            </div>
          </Paper>
        </SimpleGrid>

        {/* Scroll Zoom Statement */}
        <div className="zoom-statement-wrap">
          <h2 ref={zoomTextRef} className="zoom-statement">
            KNOW THE SHELF LIFE.<br />PLAN THE TRUCKS.<br />STOP THE WASTE.
          </h2>
        </div>
      </section>

      {/* 3. THE 4-STEP OPERATIONAL FLOW (GSAP HORIZONTAL PINNED SCROLL) */}
      <section id="workflow" ref={horizontalSectionRef} className="horizontal-scroll-section">
        <div className="horizontal-pin-wrap" style={{ position: 'relative' }}>
          <LowPolySpinach
            className="floating-veggie-3 veggie-dim"
            style={{ top: '8%', left: '34%', width: '90px', height: '115px', transform: 'rotate(20deg)' }}
          />
          <LowPolyBanana
            className="floating-veggie-1 veggie-glow"
            style={{ top: '16%', right: '18%', width: '120px', height: '95px', transform: 'rotate(-15deg)' }}
          />
          <LowPolyTomato
            className="floating-veggie-2 veggie-mid"
            style={{ bottom: '8%', left: '44%', width: '75px', height: '75px', transform: 'rotate(-8deg)' }}
          />

          <div style={{ padding: '0 clamp(16px, 4vw, 64px) 24px' }}>
            <Text className="sec-tag">[02 · HOW IT WORKS]</Text>
            <Title order={2} className="anton" style={{ fontSize: 'clamp(2rem, 4vw, 3.2rem)' }}>
              HOW FRESHROUTE BUILDS A PLAN, IN 4 STEPS
            </Title>
            <Text size="md" c="var(--muted)">
              Keep scrolling: the four steps slide past one by one.
            </Text>
          </div>

          <div ref={horizontalTrackRef} className="horizontal-track">
            {/* Panel 1 */}
            <div className="horizontal-panel" data-cursor="STEP 1">
              <div>
                <Group justify="space-between" mb="sm">
                  <Badge color="green" size="lg">STAGE 01</Badge>
                  <IconThermometer size={24} color="var(--ink)" />
                </Group>
                <Title order={3} mb="xs" fz="1.35rem">Check freshness first</Title>
                <Text size="xs" fw={700} c="var(--muted)" mb="md" className="mono">
                  <Explain note="Code: feasibility.py · shelflife.py">Drop every trip that would arrive too old to sell</Explain>
                </Text>
                <Stack gap="xs" mb="md">
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Heat matters:</strong> Works out how much life a batch loses in a normal truck
                    vs a <Explain term="reefer">refrigerated one</Explain> (<Explain term="q10">why heat matters</Explain>).
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Time to sell:</strong> Each market needs produce to arrive with some hours left to sell it.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Safe by design:</strong> Trips that fail are removed before planning, so the plan can never pick them.
                  </Text>
                </Stack>
              </div>
              <Group gap="xs" mt="lg" c="var(--ink)">
                <IconCheck size={20} stroke={2.5} />
                <Text size="sm" fw={700}>Doomed trips ruled out up front</Text>
              </Group>
            </div>

            {/* Panel 2 */}
            <div className="horizontal-panel" data-cursor="STEP 2">
              <div>
                <Group justify="space-between" mb="sm">
                  <Badge color="green" size="lg">STAGE 02</Badge>
                  <IconRoute size={24} color="var(--ink)" />
                </Group>
                <Title order={3} mb="xs" fz="1.35rem">Find the most profitable plan</Title>
                <Text size="xs" fw={700} c="var(--muted)" mb="md" className="mono">
                  <Explain note="Code: policies/milp.py · solved by HiGHS">Mathematical optimisation, not rules of thumb</Explain>
                </Text>
                <Stack gap="xs" mb="md">
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>All at once:</strong> A{' '}
                    <Explain term="milp">mathematical optimiser</Explain> weighs every batch, truck and market
                    together to maximise profit after all costs.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Real limits:</strong> Respects truck loads, trips per day, and how much each market can unload.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Never stuck:</strong> Stops after 30 seconds with the best plan so far, and falls back
                    to a <Explain term="fallback">safe plan</Explain> if anything fails.
                  </Text>
                </Stack>
              </div>
              <Group gap="xs" mt="lg" c="var(--ink)">
                <IconCheck size={20} stroke={2.5} />
                <Text size="sm" fw={700}>Best plan found within 30 seconds</Text>
              </Group>
            </div>

            {/* Panel 3 */}
            <div className="horizontal-panel" data-cursor="STEP 3">
              <div>
                <Group justify="space-between" mb="sm">
                  <Badge color="green" size="lg">STAGE 03</Badge>
                  <IconTag size={24} color="var(--ink)" />
                </Group>
                <Title order={3} mb="xs" fz="1.35rem">Watch the plan improve</Title>
                <Text size="xs" fw={700} c="var(--muted)" mb="md" className="mono">
                  <Explain note="Code: runs/progress.py · first plan from a rounded LP relaxation">A usable plan in about a second, better ones after</Explain>
                </Text>
                <Stack gap="xs" mb="md">
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Fast first plan:</strong> A quick first plan appears on screen in about a second.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Keeps improving:</strong> Each time the{' '}
                    <Explain term="highs">solver</Explain> finds a better plan, it replaces the one on screen,
                    but only after the <Explain term="simulator">simulator</Explain> confirms it really earns more.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Same checks:</strong> The final plan is scored and checked exactly like every other plan.
                  </Text>
                </Stack>
              </div>
              <Group gap="xs" mt="lg" c="var(--ink)">
                <IconCheck size={20} stroke={2.5} />
                <Text size="sm" fw={700}>Every plan on screen is scored</Text>
              </Group>
            </div>

            {/* Panel 4 */}
            <div className="horizontal-panel" data-cursor="STEP 4">
              <div>
                <Group justify="space-between" mb="sm">
                  <Badge color="green" size="lg">STAGE 04</Badge>
                  <IconBolt size={24} color="var(--ink)" />
                </Group>
                <Title order={3} mb="xs" fz="1.35rem">Re-plan when something breaks</Title>
                <Text size="xs" fw={700} c="var(--muted)" mb="md" className="mono">
                  <Explain note="Code: replan.py · trips already on the road are frozen">A road closes at noon? Fix the rest of the day in seconds</Explain>
                </Text>
                <Stack gap="xs" mb="md">
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Real-world surprises:</strong> A traffic jam, a broken{' '}
                    <Explain term="reefer">refrigerated truck</Explain>, a sudden rush of orders.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Keeps what's moving:</strong> Trucks already on the road stay{' '}
                    <Explain term="frozen">as they are</Explain>; only the rest of the day is re-planned.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Fast and safe:</strong> The solver gets 2 seconds, starting from the old plan,
                    and the result is checked like any other.
                  </Text>
                </Stack>
              </div>
              <Group gap="xs" mt="lg" c="var(--ink)">
                <IconCheck size={20} stroke={2.5} />
                <Text size="sm" fw={700}>Try it yourself: close a road on the live map</Text>
              </Group>
            </div>
          </div>
        </div>
      </section>

      {/* 4. MEASURED BENCHMARK IMPACT */}
      <section id="results" className="atelier-sec" style={{ position: 'relative' }}>
        <LowPolyCarrot
          className="floating-veggie-3 veggie-mid"
          style={{ top: '6%', right: '18%', width: '105px', height: '140px', transform: 'rotate(-20deg)' }}
        />
        <LowPolyTomato
          className="floating-veggie-1 veggie-dim"
          style={{ top: '22%', left: '14%', width: '75px', height: '75px', transform: 'rotate(15deg)' }}
        />
        <LowPolyMango
          className="floating-veggie-4 veggie-glow"
          style={{ bottom: '14%', right: '36%', width: '95px', height: '120px', transform: 'rotate(35deg)' }}
        />
        <LowPolyBanana
          className="floating-veggie-2 veggie-mid"
          style={{ bottom: '8%', left: '38%', width: '120px', height: '95px', transform: 'rotate(-12deg)' }}
        />

        <div data-reveal>
          <Text className="sec-tag">[03 · RESULTS]</Text>
          <h2 className="dup-title">
            <span className="ghost">MEASURED RESULTS,<br />NOT PROMISES</span>
            <span className="solid" data-wipe>MEASURED RESULTS,<br />NOT PROMISES</span>
          </h2>
          <Text mt={12} maw={600} size="lg" c="var(--muted)">
            We ran FreshRoute and the usual warehouse rules on the same 3 days of{' '}
            <Explain term="synthetic">synthetic</Explain> data. One shared{' '}
            <Explain term="simulator">simulator</Explain> scored every plan, so the comparison is fair.
          </Text>
        </div>

        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md" mt={36}>
          <Card withBorder p="xl" className="landing-card" data-reveal data-cursor="PROFIT">
            <Text className="sec-tag">[<Explain term="net">PROFIT</Explain>]</Text>
            <Text className="landing-stat-num" mt={6}>{show(ours?.net_inr, v => `₹${fmt(v)}`)}</Text>
            <Text fz="1.02rem" c="var(--muted)" mt={8} lh={1.5}>
              <strong>{show(dNet, d => `₹${fmt(d)} more`)}</strong> than the expiry-first rule
              ({show(fefo?.net_inr, v => `₹${fmt(v)}`)}) on the same data.
            </Text>
          </Card>

          <Card withBorder p="xl" className="landing-card" data-reveal data-cursor="SPOILAGE">
            <Text className="sec-tag">[FOOD SPOILED]</Text>
            <Text className="landing-stat-num" mt={6}>{show(ours?.spoilage_kg, v => `${fmt(v)} KG`)}</Text>
            <Text fz="1.02rem" c="var(--muted)" mt={8} lh={1.5}>
              <strong>vs {show(fefo?.spoilage_kg, v => `${fmt(v)} kg`)}</strong> with the expiry-first rule,
              while delivering {show(ours?.demand_fulfillment_pct, v => `${fmt(v, 1)}%`)} of what markets ordered.
            </Text>
          </Card>

          <Card withBorder p="xl" className="landing-card" data-reveal data-cursor="RULES">
            <Text className="sec-tag">[RULES BROKEN]</Text>
            <Text className="landing-stat-num" mt={6}>{show(ours?.violations, String)}</Text>
            <Text fz="1.02rem" c="var(--muted)" mt={8} lh={1.5}>
              <strong>Checked by a separate program</strong> against every hard rule. The arrival-order rule
              broke {show(fifo?.violations, String)}.
            </Text>
          </Card>

          <Card withBorder p="xl" className="landing-card" data-reveal data-cursor="READY">
            <Text className="sec-tag">[READY TO USE]</Text>
            <Text className="landing-stat-num" mt={6}>1-CLICK</Text>
            <Text fz="1.02rem" c="var(--muted)" mt={8} lh={1.5}>
              <strong>A truck loading list and a driver message</strong>, ready to download or paste into WhatsApp.
            </Text>
          </Card>
        </SimpleGrid>
      </section>

      {/* 5. AUDIT & TRUST SECTION */}
      <section id="audit" className="atelier-sec sec-dark" style={{ position: 'relative' }}>
        <LowPolySpinach
          className="floating-veggie-2 veggie-glow"
          style={{ top: '12%', left: '22%', width: '110px', height: '135px', transform: 'rotate(-14deg)' }}
        />
        <LowPolyTomato
          className="floating-veggie-4 veggie-mid"
          style={{ top: '16%', right: '24%', width: '85px', height: '85px', transform: 'rotate(18deg)' }}
        />
        <LowPolyCarrot
          className="floating-veggie-3 veggie-dim"
          style={{ bottom: '12%', left: '48%', width: '90px', height: '120px', transform: 'rotate(-35deg)' }}
        />

        <div data-reveal>
          <Text className="sec-tag">[04 · WHY YOU CAN TRUST IT]</Text>
          <h2 className="dup-title">
            <span className="ghost">CHECKED, STRESS-TESTED<br />AND EXPLAINED</span>
            <span className="solid" data-wipe>CHECKED, STRESS-TESTED<br />AND EXPLAINED</span>
          </h2>
          <Text mt={12} maw={600} size="md" className="sec-sub">
            FreshRoute doesn't mark its own homework. A separate program re-does the maths from scratch and checks
            every plan, and every number on this site comes from a saved, reproducible run.
          </Text>

          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg" mt={36}>
            <Paper p="xl" radius="xs" style={{ background: '#12251a', border: '1px solid #4fbf7f40' }}>
              <Group gap="sm" mb="xs">
                <IconShieldCheck size={26} color="#4fbf7f" />
                <Title order={4} c="#fef0d5" fz="1.25rem">Independent checker</Title>
              </Group>
              <Text fz="1.02rem" c="#d2e5d7" lh={1.5}>
                A separate program that shares no code with the planner. It checks 16 hard rules, such as no
                overloaded trucks and no produce arriving too old to sell.
              </Text>
            </Paper>

            <Paper p="xl" radius="xs" style={{ background: '#12251a', border: '1px solid #4fbf7f40' }}>
              <Group gap="sm" mb="xs">
                <IconFileCheck size={26} color="#4fbf7f" />
                <Title order={4} c="#fef0d5" fz="1.25rem">Tested on 200 possible futures</Title>
              </Group>
              <Text fz="1.02rem" c="#d2e5d7" lh={1.5}>
                Demand, travel times and shelf life never go exactly to plan. We replay both plans through 200 random
                versions of the next days
                {won != null && stress
                  ? <>: FreshRoute beats {policyName(stress.summary.baseline).toLowerCase()} on profit in {fmtShare(won)} of them.</>
                  : '.'}
              </Text>
            </Paper>

            <Paper p="xl" radius="xs" style={{ background: '#12251a', border: '1px solid #4fbf7f40' }}>
              <Group gap="sm" mb="xs">
                <IconCertificate size={26} color="#4fbf7f" />
                <Title order={4} c="#fef0d5" fz="1.25rem">A reason for every shipment</Title>
              </Group>
              <Text fz="1.02rem" c="#d2e5d7" lh={1.5}>
                Click any line of the plan to see why that batch goes to that market, and why the next-best
                option lost.
              </Text>
            </Paper>
          </SimpleGrid>
        </div>
      </section>

      {/* 6. CALL TO ACTION SECTION */}
      <section className="atelier-sec ta-center" style={{ textAlign: 'center', padding: '10vh 16px', position: 'relative' }}>
        <LowPolyBanana
          className="floating-veggie-1 veggie-mid"
          style={{ top: '16%', left: '18%', width: '125px', height: '95px', transform: 'rotate(26deg)' }}
        />
        <LowPolyMango
          className="floating-veggie-2 veggie-glow"
          style={{ top: '22%', right: '16%', width: '105px', height: '130px', transform: 'rotate(-18deg)' }}
        />
        <LowPolyTomato
          className="floating-veggie-3 veggie-dim"
          style={{ bottom: '16%', left: '46%', width: '70px', height: '70px', transform: 'rotate(12deg)' }}
        />

        <div data-reveal>
          <Text className="sec-tag">[TRY IT YOURSELF]</Text>
          <Title order={1} className="anton" style={{ fontSize: 'clamp(2.4rem, 6vw, 4.8rem)', margin: '14px 0' }}>
            PLAN TODAY'S DELIVERIES
          </Title>
          <Text maw={580} mx="auto" size="lg" c="var(--muted)" mb={32}>
            Open the live demo, press one button, and watch FreshRoute plan 200 batches across 8 markets. Then
            close a road and see it re-plan.
          </Text>
          <button
            className="atelier-cta cta-hero-large"
            onClick={onLaunch}
            style={{ margin: '0 auto' }}
            data-cursor="OPEN"
          >
            <span className="cta-mask">
              <span className="cta-label">OPEN THE LIVE DEMO</span>
              <span className="cta-clone">OPEN THE LIVE DEMO</span>
            </span>
            <span className="cta-div" aria-hidden />
            <IconArrowRight size={22} />
          </button>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="atelier-foot">
        <Group justify="space-between" align="flex-start" wrap="wrap" gap="xl">
          <div>
            <Group gap={8} mb="xs">
              <IconLeaf size={24} color="var(--ink)" />
              <Text className="wordmark-sm" fz={24}>FRESHROUTE</Text>
            </Group>
            <Text size="sm" c="var(--muted)" maw={420}>
              Plans which truck takes which produce to which market, so more food is sold fresh and less is
              thrown away. All data shown is synthetic.
            </Text>
          </div>
          <Stack gap={6} align="flex-end">
            <button
              className="top-link"
              onClick={() => gsap.to(window, { duration: 1, scrollTo: 0 })}
              data-cursor="TOP"
            >
              BACK TO TOP [↑]
            </button>
            <Text size="xs" c="var(--muted)">RUNS FULLY OFFLINE · NO OUTSIDE SERVICES</Text>
          </Stack>
        </Group>
      </footer>
    </div>
  )
}
