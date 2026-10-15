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
import { useLayoutEffect, useRef } from 'react'
import {
  LowPolyBanana, LowPolyCarrot, LowPolyMango, LowPolySpinach, LowPolyTomato
} from '../components/LowPolyProduce'

gsap.registerPlugin(ScrollTrigger, ScrollToPlugin)

interface LandingPageProps {
  onLaunch: () => void
}

export function LandingPage({ onLaunch }: LandingPageProps) {
  const root = useRef<HTMLDivElement>(null)
  const horizontalSectionRef = useRef<HTMLDivElement>(null)
  const horizontalTrackRef = useRef<HTMLDivElement>(null)
  const zoomTextRef = useRef<HTMLHeadingElement>(null)

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
            <span className="sec-tag">[PRODUCE LOGISTICS ENGINE]</span>
            <Badge color="green" variant="light" size="sm">
              SOLVER SPINE · FEASIBILITY FILTER · LIVE PLAN UPDATES
            </Badge>
          </Group>

          <h1 className="display landing-title" aria-label="FreshRoute">
            <span className="hero-mask">
              <span className="landing-hero-line">FRESH PRODUCE.</span>
            </span>
            <span className="hero-mask">
              <span className="landing-hero-line outline">OPTIMAL DISPATCH.</span>
            </span>
          </h1>

          <div className="landing-hero-fade" style={{ maxWidth: 660, marginTop: 18 }}>
            <Text size="xl" lh={1.6} fw={400} c="var(--text)">
              Every morning at 5:00 AM, distributors face hundreds of perishable batches and dozens of mandi routes.
              <strong> FreshRoute</strong> computes temperature decay, route feasibility, and vehicle capacities
              to deliver every crate before its shelf-life expires.
            </Text>
          </div>

          <Group mt={32} className="landing-hero-fade" gap="md">
            <button className="atelier-cta" onClick={onLaunch} data-cursor="LAUNCH">
              <span className="cta-mask">
                <span className="cta-label">LAUNCH OPERATIONS CONSOLE</span>
                <span className="cta-clone">LAUNCH OPERATIONS CONSOLE</span>
              </span>
              <span className="cta-div" aria-hidden />
              <IconArrowRight size={16} />
            </button>
          </Group>

          {/* Quick Metrics Bar */}
          <SimpleGrid cols={{ base: 2, sm: 4 }} mt={48} className="landing-hero-fade landing-quick-stats">
            <div className="landing-stat-cell" data-cursor="+13.3%">
              <Text className="landing-stat-num">+13.3%</Text>
              <Text size="xs" c="var(--muted)" fw={600}>
                NET PROFIT GAIN
              </Text>
            </div>
            <div className="landing-stat-cell" data-cursor="30%">
              <Text className="landing-stat-num">30%+</Text>
              <Text size="xs" c="var(--muted)" fw={600}>
                SPOILAGE REDUCED
              </Text>
            </div>
            <div className="landing-stat-cell" data-cursor="0 VIOL">
              <Text className="landing-stat-num">0</Text>
              <Text size="xs" c="var(--muted)" fw={600}>
                CONSTRAINT VIOLATIONS
              </Text>
            </div>
            <div className="landing-stat-cell" data-cursor="3.2s">
              <Text className="landing-stat-num">&lt; 4 SEC</Text>
              <Text size="xs" c="var(--muted)" fw={600}>
                MID-DAY RE-PLAN TIME
              </Text>
            </div>
          </SimpleGrid>
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
          <Text className="sec-tag">[01 · THE POST-HARVEST REALITY]</Text>
          <h2 className="dup-title">
            <span className="ghost">WHY CONVENTIONAL<br />WAREHOUSE RULES FAIL</span>
            <span className="solid" data-wipe>WHY CONVENTIONAL<br />WAREHOUSE RULES FAIL</span>
          </h2>
          <Text mt={12} maw={620} size="lg" c="var(--muted)">
            Standard warehouse management relies on <em>First-In, First-Out (FIFO)</em>.
            In agricultural supply chains, FIFO directly causes preventable spoilage.
          </Text>
        </div>

        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mt={36}>
          <Paper withBorder p="xl" className="landing-card" data-reveal>
            <div>
              <Group gap="sm" mb="md">
                <ThemeIcon size={38} color="red" variant="light">
                  <IconScale size={20} />
                </ThemeIcon>
                <Title order={3} fz="1.4rem">The FIFO Blindspot</Title>
              </Group>
              <Stack gap="xs" mb="sm">
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>The Flaw:</strong> Blindly dispatches by arrival order, ignoring 32°C ambient heat.
                </Text>
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>The Decay:</strong> High-heat crates decay 3× faster, rotting mid-transit on long highway hauls.
                </Text>
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>The Fallout:</strong> Near-expiry batches dumped at mandi gates or rejected by buyers.
                </Text>
              </Stack>
            </div>
            <div className="landing-highlight bad" style={{ marginTop: 16 }}>
              <strong>Result:</strong> 37 physical violations, dumped truckloads, and heavy revenue loss.
            </div>
          </Paper>

          <Paper withBorder p="xl" className="landing-card" data-reveal>
            <div>
              <Group gap="sm" mb="md">
                <ThemeIcon size={38} color="green" variant="light">
                  <IconLeaf size={20} />
                </ThemeIcon>
                <Title order={3} fz="1.4rem">FreshRoute Kinetic Filter</Title>
              </Group>
              <Stack gap="xs" mb="sm">
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>Kinetic Sensing:</strong> Models $Q_{10}$ temperature decay during holding and transit.
                </Text>
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>Feasibility Gate:</strong> Prunes doomed dispatches before a single truck is loaded.
                </Text>
                <Text fz="1.05rem" lh={1.5} c="var(--text)">
                  • <strong>Optimal Delivery:</strong> Matches fragile crates strictly to nearby, guaranteed-sale mandis.
                </Text>
              </Stack>
            </div>
            <div className="landing-highlight good" style={{ marginTop: 16 }}>
              <strong>Result:</strong> 0 shelf-life violations, +₹168,000 net margin gain per cycle.
            </div>
          </Paper>
        </SimpleGrid>

        {/* Scroll Zoom Statement */}
        <div className="zoom-statement-wrap">
          <h2 ref={zoomTextRef} className="zoom-statement">
            SENSE SHELF-LIFE.<br />SOLVE DISPATCH.<br />STOP SPOILAGE.
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
            <Text className="sec-tag">[02 · HOW IT WORKS IN BACKEND]</Text>
            <Title order={2} className="anton" style={{ fontSize: 'clamp(2rem, 4vw, 3.2rem)' }}>
              THE 4-STEP DISPATCH PIPELINE
            </Title>
            <Text size="md" c="var(--muted)">
              Scroll down to inspect each stage of the FreshRoute optimization engine.
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
                <Title order={3} mb="xs" fz="1.35rem">Shelf-Life Feasibility Gate</Title>
                <Text size="xs" fw={700} c="var(--muted)" mb="md" className="mono">
                  feasibility.py · shelflife.py
                </Text>
                <Stack gap="xs" mb="md">
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Kinetic Decay:</strong> Computes temperature ($Q_{10}$) loss for ambient vs reefer lanes.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Sale Windows:</strong> Prunes routes where arrival shelf-life fails mandi minimums.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>By Construction:</strong> Eliminates infeasible candidate arcs before mathematical solving.
                  </Text>
                </Stack>
              </div>
              <Group gap="xs" mt="lg" c="var(--ink)">
                <IconCheck size={20} stroke={2.5} />
                <Text size="sm" fw={700}>Infeasible arcs dropped upfront</Text>
              </Group>
            </div>

            {/* Panel 2 */}
            <div className="horizontal-panel" data-cursor="STEP 2">
              <div>
                <Group justify="space-between" mb="sm">
                  <Badge color="green" size="lg">STAGE 02</Badge>
                  <IconRoute size={24} color="var(--ink)" />
                </Group>
                <Title order={3} mb="xs" fz="1.35rem">HiGHS Allocation Solver</Title>
                <Text size="xs" fw={700} c="var(--muted)" mb="md" className="mono">
                  policies/milp.py · PuLP
                </Text>
                <Stack gap="xs" mb="md">
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>MILP Optimization:</strong> Solves for maximum net profit under strict 30s limit.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Physical Constraints:</strong> Adheres to truck payload caps and dock receiving limits.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Market Equity:</strong> Prevents starving secondary mandis while prioritizing margins.
                  </Text>
                </Stack>
              </div>
              <Group gap="xs" mt="lg" c="var(--ink)">
                <IconCheck size={20} stroke={2.5} />
                <Text size="sm" fw={700}>Best plan found within the 30s limit</Text>
              </Group>
            </div>

            {/* Panel 3 */}
            <div className="horizontal-panel" data-cursor="STEP 3">
              <div>
                <Group justify="space-between" mb="sm">
                  <Badge color="green" size="lg">STAGE 03</Badge>
                  <IconTag size={24} color="var(--ink)" />
                </Group>
                <Title order={3} mb="xs" fz="1.35rem">Live Plan Updates</Title>
                <Text size="xs" fw={700} c="var(--muted)" mb="md" className="mono">
                  runs/progress.py · Rounded-LP Start
                </Text>
                <Stack gap="xs" mb="md">
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Fast First Plan:</strong> A rounded-LP start puts a feasible plan on screen in about a second.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Keeps Improving:</strong> Each better plan HiGHS finds replaces it, once the simulator confirms the gain.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Final Result:</strong> The last version is the solver's own plan, scored and validated like every other.
                  </Text>
                </Stack>
              </div>
              <Group gap="xs" mt="lg" c="var(--ink)">
                <IconCheck size={20} stroke={2.5} />
                <Text size="sm" fw={700}>Best plan so far, always simulated</Text>
              </Group>
            </div>

            {/* Panel 4 */}
            <div className="horizontal-panel" data-cursor="STEP 4">
              <div>
                <Group justify="space-between" mb="sm">
                  <Badge color="green" size="lg">STAGE 04</Badge>
                  <IconBolt size={24} color="var(--ink)" />
                </Group>
                <Title order={3} mb="xs" fz="1.35rem">3-Second Mid-Day Replan</Title>
                <Text size="xs" fw={700} c="var(--muted)" mb="md" className="mono">
                  replan.py · Frozen Rows
                </Text>
                <Stack gap="xs" mb="md">
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Dynamic Disruptions:</strong> Responds instantly to road jams or reefer breakdowns.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Transit Freezing:</strong> Freezes trucks en route; re-allocates remaining stock.
                  </Text>
                  <Text fz="1.05rem" lh={1.5} c="var(--text)">
                    • <strong>Sub-4s Replan:</strong> Generates repaired schedule with 0 new violations in &lt;4s.
                  </Text>
                </Stack>
              </div>
              <Group gap="xs" mt="lg" c="var(--ink)">
                <IconCheck size={20} stroke={2.5} />
                <Text size="sm" fw={700}>Interactive flight board & diff narration</Text>
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
          <Text className="sec-tag">[03 · MEASURED PERFORMANCE]</Text>
          <h2 className="dup-title">
            <span className="ghost">PROVEN OUTCOMES<br />MEASURED ON DISK</span>
            <span className="solid" data-wipe>PROVEN OUTCOMES<br />MEASURED ON DISK</span>
          </h2>
          <Text mt={12} maw={600} size="lg" c="var(--muted)">
            Scored identically across every policy using a shared economic simulator.
          </Text>
        </div>

        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md" mt={36}>
          <Card withBorder p="xl" className="landing-card" data-reveal data-cursor="+₹168K">
            <Text className="sec-tag">[NET PROFIT]</Text>
            <Text className="landing-stat-num" mt={6}>₹1,431,591</Text>
            <Text fz="1.02rem" c="var(--muted)" mt={8} lh={1.5}>
              <strong>+₹168,340 (+13.3%)</strong> net gain over FEFO-greedy and naive FIFO baselines.
            </Text>
          </Card>

          <Card withBorder p="xl" className="landing-card" data-reveal data-cursor="1.82%">
            <Text className="sec-tag">[SPOILAGE CONTROL]</Text>
            <Text className="landing-stat-num" mt={6}>1.82%</Text>
            <Text fz="1.02rem" c="var(--muted)" mt={8} lh={1.5}>
              <strong>30%+ spoilage reduction</strong> while fulfilling 62.5% of total mandi demand.
            </Text>
          </Card>

          <Card withBorder p="xl" className="landing-card" data-reveal data-cursor="0 VIOL">
            <Text className="sec-tag">[PHYSICAL INTEGRITY]</Text>
            <Text className="landing-stat-num" mt={6}>0 VIOLATIONS</Text>
            <Text fz="1.02rem" c="var(--muted)" mt={8} lh={1.5}>
              <strong>100% compliant</strong> on all 13 rules (FIFO caused 37 physical violations).
            </Text>
          </Card>

          <Card withBorder p="xl" className="landing-card" data-reveal data-cursor="1-CLICK">
            <Text className="sec-tag">[DISPATCH SHEETS]</Text>
            <Text className="landing-stat-num" mt={6}>1-CLICK</Text>
            <Text fz="1.02rem" c="var(--muted)" mt={8} lh={1.5}>
              <strong>WhatsApp driver texts & CSVs</strong> ready for 5:00 AM warehouse dispatch.
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
          <Text className="sec-tag">[04 · VERIFICATION & TRUST]</Text>
          <h2 className="dup-title">
            <span className="ghost">INDEPENDENT AUDIT<br />ZERO CHEATING</span>
            <span className="solid" data-wipe>INDEPENDENT AUDIT<br />ZERO CHEATING</span>
          </h2>
          <Text mt={12} maw={600} size="md" className="sec-sub">
            The optimization engine does not grade itself. An independent validation package re-implements the physics
            and audits every plan.
          </Text>

          <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg" mt={36}>
            <Paper p="xl" radius="xs" style={{ background: '#12251a', border: '1px solid #4fbf7f40' }}>
              <Group gap="sm" mb="xs">
                <IconShieldCheck size={26} color="#4fbf7f" />
                <Title order={4} c="#fef0d5" fz="1.25rem">Independent Validator</Title>
              </Group>
              <Text fz="1.02rem" c="#d2e5d7" lh={1.5}>
                Separate Python package (`validator/`). Audits 13 physical constraints without importing optimizer code.
              </Text>
            </Paper>

            <Paper p="xl" radius="xs" style={{ background: '#12251a', border: '1px solid #4fbf7f40' }}>
              <Group gap="sm" mb="xs">
                <IconFileCheck size={26} color="#4fbf7f" />
                <Title order={4} c="#fef0d5" fz="1.25rem">200 Stress Futures</Title>
              </Group>
              <Text fz="1.02rem" c="#d2e5d7" lh={1.5}>
                Monte Carlo simulation across 200 random market futures proves resilience to delays & demand spikes.
              </Text>
            </Paper>

            <Paper p="xl" radius="xs" style={{ background: '#12251a', border: '1px solid #4fbf7f40' }}>
              <Group gap="sm" mb="xs">
                <IconCertificate size={26} color="#4fbf7f" />
                <Title order={4} c="#fef0d5" fz="1.25rem">Explainable Reasons</Title>
              </Group>
              <Text fz="1.02rem" c="#d2e5d7" lh={1.5}>
                Transparent reason cards justify every vehicle allocation against runner-up destinations.
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
          <Text className="sec-tag">[READY TO SIMULATE?]</Text>
          <Title order={1} className="anton" style={{ fontSize: 'clamp(2.4rem, 6vw, 4.8rem)', margin: '14px 0' }}>
            OPERATE THE 5:00 AM HUB CONSOLE
          </Title>
          <Text maw={580} mx="auto" size="lg" c="var(--muted)" mb={32}>
            Execute real MILP optimization on the calibrated Bangalore hub scenario with 1 click.
          </Text>
          <button
            className="atelier-cta cta-hero-large"
            onClick={onLaunch}
            style={{ margin: '0 auto' }}
            data-cursor="SIMULATE"
          >
            <span className="cta-mask">
              <span className="cta-label">LAUNCH OPERATIONS CONSOLE</span>
              <span className="cta-clone">LAUNCH OPERATIONS CONSOLE</span>
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
              Shelf-life sensing, integer programming dispatch, and plans that improve while you watch for perishable produce distribution.
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
            <Text size="xs" c="var(--muted)">OPERATES 100% OFFLINE · NO EXTERNAL API CALLS</Text>
          </Stack>
        </Group>
      </footer>
    </div>
  )
}
