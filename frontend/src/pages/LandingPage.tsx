// Landing: scroll-driven fullscreen intro video, then hero with two actions,
// the marquee, a vendor-friendly 7-step usage guide, and a minimal footer.
// No KPI maths here: the UI only shows served numbers; this page shows none.
import { Group, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import { IconArrowRight, IconBook2, IconLeaf } from '@tabler/icons-react'
import { gsap } from 'gsap'
import { ScrollToPlugin } from 'gsap/ScrollToPlugin'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useLayoutEffect, useRef, useState } from 'react'

gsap.registerPlugin(ScrollTrigger, ScrollToPlugin)

// Vendor-facing usage flow: how to operate the demo, not how the engine works.
const GUIDE_STEPS = [
  {
    n: '01',
    title: 'Open the live demo',
    body: 'Press “Open the live demo”. A ready-made demo day loads: stock batches, markets, and trucks. Nothing to upload.',
  },
  {
    n: '02',
    title: 'Check what you have to sell',
    body: 'Look at your batches: each one shows its quantity and how much freshness it has left. The oldest-feeling stock is flagged first.',
  },
  {
    n: '03',
    title: 'Check where it can go',
    body: 'Each market shows what it ordered and the time window your truck must arrive in. If produce would arrive too old to sell, that trip is blocked for you.',
  },
  {
    n: '04',
    title: 'Press “Make my plan”',
    body: 'FreshRoute works out every possible batch → truck → market trip, then picks the combination with the highest profit after transport, handling, and waste costs.',
  },
  {
    n: '05',
    title: 'Read the plan in plain words',
    body: 'Every line says what goes where, on which truck, and when. Click any line to see why that trip won and why the next-best option lost.',
  },
  {
    n: '06',
    title: 'Send it to your drivers',
    body: 'Download the loading list as a file, or copy the ready-written driver message and paste it into WhatsApp.',
  },
  {
    n: '07',
    title: 'Fix the day when things change',
    body: 'Road closed or truck broke down? Tell the demo what happened and it re-plans the rest of the day in seconds. Trucks already on the road stay as they are.',
  },
]

interface LandingPageProps {
  onLaunch: () => void
}

export function LandingPage({ onLaunch }: LandingPageProps) {
  const root = useRef<HTMLDivElement>(null)
  const introRef = useRef<HTMLElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const guideRef = useRef<HTMLElement>(null)
  // Reduced-motion or a broken video skips the scroll intro and shows the hero directly.
  const [introOff, setIntroOff] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  useLayoutEffect(() => {
    if (introOff || !introRef.current || !videoRef.current) return
    const video = videoRef.current
    const ctx = gsap.context(() => {
      // Pin the fullscreen video while it plays continuously (muted autoplay loop).
      // Scrolling holds the video on screen, then releases into the hero below.
      const trigger = ScrollTrigger.create({
        trigger: introRef.current,
        start: 'top top',
        end: '+=120%',
        pin: true,
        onEnter: () => video.play().catch(() => {}),
        onEnterBack: () => video.play().catch(() => {}),
        onLeave: () => video.pause(),
        onLeaveBack: () => video.pause(),
      })
      // Keep the ambient marquee looping (the one section we kept as-is).
      gsap.to('.marquee-track', { xPercent: -50, duration: 25, ease: 'none', repeat: -1 })
      // Gentle hero entrance once it scrolls into view.
      gsap.from('.landing-hero-line', {
        scaleY: 0,
        duration: 1.1,
        ease: 'power4.out',
        stagger: 0.12,
        scrollTrigger: { trigger: '.landing-hero', start: 'top 80%', once: true },
      })
      return () => trigger.kill()
    }, root)
    return () => ctx.revert()
  }, [introOff])

  const scrollToGuide = () => {
    gsap.to(window, { duration: 1, ease: 'power3.inOut', scrollTo: { y: '#guide', offsetY: 70 } })
  }

  const skipIntro = () => {
    setIntroOff(true)
    requestAnimationFrame(() => {
      gsap.to(window, { duration: 0.8, ease: 'power3.inOut', scrollTo: { y: '.landing-hero', offsetY: 60 } })
    })
  }

  return (
    <div ref={root} className="landing-page">
      {/* SCROLL INTRO: fullscreen enter_video.mp4, pinned while it plays */}
      {!introOff && (
        <section ref={introRef} className="landing-intro" aria-label="Introduction video: scroll to continue">
          <div className="landing-intro-sticky">
            <video
              ref={videoRef}
              className="landing-intro-video"
              src="/enter_video.mp4"
              muted
              loop
              autoPlay
              playsInline
              preload="auto"
              aria-label="FreshRoute introduction video"
              onError={() => setIntroOff(true)}
            />
            <div className="landing-intro-overlay">
              <Text className="sec-tag">[SCROLL TO ENTER]</Text>
              <Text size="sm" c="var(--cream)" opacity={0.85}>
                Keep scrolling to enter the site.
              </Text>
              <button className="atelier-ghost landing-intro-skip" onClick={skipIntro} data-cursor="SKIP">
                SKIP INTRO ↓
              </button>
            </div>
          </div>
        </section>
      )}

      {/* HERO: big title + two actions */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <Group gap="xs" className="landing-hero-fade">
            <span className="sec-tag">[DAILY DISPATCH PLANNER FOR FRESH PRODUCE]</span>
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
              Every morning, a produce warehouse decides which crates go on which truck to which
              market. Choose badly and tomatoes rot on the road.{' '}
              <strong>FreshRoute</strong> checks how long each batch will stay fresh, then picks the
              plan that earns the most without breaking a single delivery rule.
            </Text>
          </div>

          <Group mt={32} className="landing-hero-fade" gap="md">
            <button className="atelier-ghost" onClick={scrollToGuide} data-cursor="GUIDE">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <IconBook2 size={16} />
                HOW OUR WEBSITE WORKS
              </span>
            </button>
            <button className="atelier-cta" onClick={onLaunch} data-cursor="OPEN">
              <span className="cta-mask">
                <span className="cta-label">OPEN THE LIVE DEMO</span>
                <span className="cta-clone">OPEN THE LIVE DEMO</span>
              </span>
              <span className="cta-div" aria-hidden />
              <IconArrowRight size={16} />
            </button>
          </Group>
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

      {/* HOW OUR WEBSITE WORKS: 7 vendor steps */}
      <section id="guide" ref={guideRef} className="atelier-sec">
        <Text className="sec-tag">[HOW TO USE THIS WEBSITE]</Text>
        <Title order={2} className="anton" style={{ fontSize: 'clamp(2rem, 4vw, 3.2rem)' }}>
          PLAN A DAY IN 7 STEPS
        </Title>
        <Text size="md" c="var(--muted)" maw={640}>
          Written for a first-time vendor: no technical terms, just what to click and what you get.
        </Text>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md" mt={36}>
          {GUIDE_STEPS.map((s) => (
            <div key={s.n} className="landing-card landing-guide-card">
              <div>
                <Text className="sec-tag">[{s.n}]</Text>
                <Title order={3} fz="1.35rem" mt={6}>
                  {s.title}
                </Title>
                <Text fz="1.02rem" lh={1.55} c="var(--text)" mt={8}>
                  {s.body}
                </Text>
              </div>
            </div>
          ))}
          <div className="landing-card landing-guide-card landing-guide-cta">
            <div>
              <Text className="sec-tag">[READY?]</Text>
              <Title order={3} fz="1.35rem" mt={6}>
                Try step 1 right now
              </Title>
              <Text fz="1.02rem" lh={1.55} c="var(--text)" mt={8}>
                Open the demo and follow the steps above on a real practice day.
              </Text>
              <button className="atelier-cta" onClick={onLaunch} data-cursor="OPEN" style={{ marginTop: 16 }}>
                <span className="cta-mask">
                  <span className="cta-label">OPEN THE LIVE DEMO</span>
                  <span className="cta-clone">OPEN THE LIVE DEMO</span>
                </span>
                <span className="cta-div" aria-hidden />
                <IconArrowRight size={16} />
              </button>
            </div>
          </div>
        </SimpleGrid>
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
