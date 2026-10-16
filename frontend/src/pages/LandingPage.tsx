// Landing: a plain-words hero beside low-poly produce, the marquee, the crate's-journey usage guide, and a minimal
// footer. No KPI maths here: the guide's crate shows served dispatch fields as-is.
import { Group, Stack, Text, Title } from '@mantine/core'
import { IconArrowRight, IconBook2, IconLeaf } from '@tabler/icons-react'
import { gsap } from 'gsap'
import { ScrollToPlugin } from 'gsap/ScrollToPlugin'
import { useLayoutEffect, useRef } from 'react'
import { CrateJourney } from '../components/CrateJourney'
import { ProducePile } from '../components/LowPolyProduce'
import { useDemoDay } from '../lib/demo'

gsap.registerPlugin(ScrollToPlugin)

interface LandingPageProps {
  /** `from` is the clicked control; it morphs into the dashboard header (App.tsx view transition). */
  onLaunch: (from?: HTMLElement) => void
}

export function LandingPage({ onLaunch }: LandingPageProps) {
  const root = useRef<HTMLDivElement>(null)
  const day = useDemoDay()
  // shipment no. 1 of the saved plan rides through the guide
  const first = day?.rows.find(r => r.priority_rank === 1) ?? day?.rows[0] ?? null

  // Ambient marquee loop and a gentle hero entrance (skipped for reduced motion).
  useLayoutEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const ctx = gsap.context(() => {
      gsap.to('.marquee-track', { xPercent: -50, duration: 25, ease: 'none', repeat: -1 })
      gsap.from('.landing-hero-line', {
        scaleY: 0,
        duration: 1.1,
        ease: 'power4.out',
        stagger: 0.12,
      })
    }, root)
    return () => ctx.revert()
  }, [])

  const scrollToGuide = () => {
    gsap.to(window, { duration: 1, ease: 'power3.inOut', scrollTo: { y: '#guide', offsetY: 70 } })
  }

  return (
    <div ref={root} className="landing-page">
      {/* HERO: what FreshRoute does in plain words, with produce spilling out of a crate beside it */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-hero-copy">
            <span className="sec-tag">[A PLANNING TOOL FOR FRUIT AND VEGETABLE WAREHOUSES]</span>

            <h1 className="display landing-title" aria-label="Get food to market before it spoils">
              <span className="hero-mask">
                <span className="landing-hero-line">GET FOOD TO MARKET</span>
              </span>
              <span className="hero-mask">
                <span className="landing-hero-line outline">BEFORE IT SPOILS.</span>
              </span>
            </h1>

            <Text className="hero-lede">
              Fruit and vegetables only stay fresh for a few days. Every morning, a warehouse has to decide which
              crate goes on which truck, and to which market. Get it wrong and the food goes bad on the way.{' '}
              <strong>FreshRoute makes that plan for you.</strong>
            </Text>

            <ol className="hero-steps">
              <li><span>1</span>It checks how many hours each crate has before it goes bad.</li>
              <li><span>2</span>It picks a truck and a market for every crate, so the most food sells while it is fresh.</li>
              <li><span>3</span>If a road closes or a truck breaks down, it makes a new plan in seconds.</li>
            </ol>

            <Group mt={30} gap="md">
              <button className="atelier-cta" onClick={(e) => onLaunch(e.currentTarget)} data-cursor="OPEN">
                <span className="cta-mask">
                  <span className="cta-label">OPEN THE LIVE DEMO</span>
                  <span className="cta-clone">OPEN THE LIVE DEMO</span>
                </span>
                <span className="cta-div" aria-hidden />
                <IconArrowRight size={16} />
              </button>
              <button className="atelier-ghost" onClick={scrollToGuide} data-cursor="GUIDE">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  <IconBook2 size={16} />
                  SEE HOW IT WORKS
                </span>
              </button>
            </Group>
            <Text size="sm" c="var(--muted)" mt="md">
              The demo uses a made-up practice warehouse near Bengaluru, not a real company’s numbers.
            </Text>
          </div>

          <ProducePile />
        </div>
      </section>

      {/* MARQUEE (kept as-is) */}
      <div className="marquee" aria-hidden>
        <div className="marquee-track">
          {[0, 1].map((k) => (
            <span key={k} className="marquee-chunk">
              TOMATOES · MANGOES · SPINACH · BANANAS · ONIONS · POTATOES ·&nbsp;
            </span>
          ))}
        </div>
      </div>

      {/* HOW OUR WEBSITE WORKS: 7 vendor steps, one crate carried through them */}
      <section id="guide" className="guide-sec">
        <CrateJourney row={first} onLaunch={() => onLaunch()}>
          <Text className="sec-tag">[HOW TO USE THIS WEBSITE]</Text>
          <div className="guide-head">
            <Title order={2} className="anton" style={{ fontSize: 'clamp(2rem, 4vw, 3.2rem)' }}>
              PLAN A DAY IN 7 STEPS
            </Title>
            <button className="atelier-cta" onClick={(e) => onLaunch(e.currentTarget)} data-cursor="OPEN">
              <span className="cta-mask">
                <span className="cta-label">OPEN THE LIVE DEMO</span>
                <span className="cta-clone">OPEN THE LIVE DEMO</span>
              </span>
              <span className="cta-div" aria-hidden />
              <IconArrowRight size={16} />
            </button>
          </div>
          <Text size="md" c="var(--muted)" maw={640}>
            Seven short steps, no technical words: what to click and what you get.
            {first && ` Follow one real crate from the demo plan (batch ${first.batch_id}, ${first.commodity}) from the warehouse to the driver’s phone.`}
          </Text>
        </CrateJourney>
      </section>

      {/* MINIMAL FOOTER */}
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
