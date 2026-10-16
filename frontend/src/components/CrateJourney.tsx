// Landing "how to use" guide (ARCHITECTURE §16): seven vendor steps on a sideways track that vertical scroll drives
// (sticky stage, GSAP scrub, no pin). One crate, shipment no. 1 of the saved demo plan, rides along and changes form
// at each step. Its labels are that served dispatch row, shown as-is. Phones and reduced motion get a plain list.
import { Text, Title } from '@mantine/core'
import { IconArrowRight } from '@tabler/icons-react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { AnimatePresence, m } from 'motion/react'
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { spring } from '../theme'
import type { DispatchRow } from '../types'
import { num } from './plan/format'
import { Fuse } from './plan/Fuse'

gsap.registerPlugin(ScrollTrigger)

// Vendor-facing usage flow: how to operate the demo, not how the engine works.
const STEPS = [
  ['Open the live demo', 'Press “Open the live demo”. A ready-made demo day loads: stock batches, markets, and trucks. Nothing to upload.'],
  ['Check what you have to sell', 'See every batch in the warehouse: how many kg it holds and how many hours it has before it goes bad. The ones closest to going bad come first.'],
  ['Check where it can go', 'Each market shows what it wants to buy and the hours it accepts deliveries. If a crate would arrive too late to sell, FreshRoute will not send it there.'],
  ['Press “Make my plan”', 'FreshRoute tries every way to send each batch (which truck, which market) and picks the mix that earns the most after paying for transport, handling and food that goes bad.'],
  ['Read the plan in plain words', 'Every line says what goes where, on which truck, and when. Click any line to see why that trip won and why the next-best option lost.'],
  ['Send it to your drivers', 'Download the loading list as a file, or copy the ready-written driver message and paste it into WhatsApp.'],
  ['Fix the day when things change', 'Road closed or truck broke down? Tell the demo what happened and it re-plans the rest of the day in seconds. Trucks already on the road stay as they are.'],
] as const
const N = STEPS.length + 1 // + the closing call-to-action panel

const WIDE = '(min-width: 900px) and (prefers-reduced-motion: no-preference)'

// What the crate looks like at each step: it gains a fuse, a destination, a truck, then becomes a plan line and a message.
function CrateFace({ s, r }: { s: number; r: DispatchRow }) {
  const dest = r.dest_name.split(',')[0]
  const kg = `${num(Math.round(r.kg))} kg`
  if (s === 4) return (
    <div className="crate-line">
      <b>{r.depart_clock}</b><span>Truck {r.vehicle_id}</span><span>{dest}</span>
      <span>{r.batch_id} {r.commodity} {kg}</span><b>{num(r.slack_h)} h spare</b>
    </div>
  )
  if (s === 5) return (
    <div className="crate-msg">
      <span>Truck {r.vehicle_id}, leave at {r.depart_clock}.</span>
      <span>Load {r.batch_id}: {r.commodity}, {kg}.</span>
      <span>Deliver to {r.dest_name} by hour {num(r.arrive_by_h)}.</span>
    </div>
  )
  return (
    <div className="crate-box">
      <div className="crate-head">{r.batch_id}</div>
      <div className="crate-body">
        <span>{r.commodity}, {kg}</span>
        {s >= 1 && <span className="crate-row"><Fuse slackH={r.slack_h} width={110} />{num(r.slack_h)} h to spare</span>}
        {s >= 2 && <span>→ {dest}, by hour {num(r.arrive_by_h)}</span>}
        {s >= 3 && <span>Truck {r.vehicle_id}, leaves {r.depart_clock}</span>}
        {s >= 6 && <span className="crate-stamp">Re-planned around the closed road</span>}
      </div>
    </div>
  )
}

export function CrateJourney({ row, onLaunch, children }: { row: DispatchRow | null; onLaunch: () => void; children: ReactNode }) {
  const wrap = useRef<HTMLDivElement>(null)
  const track = useRef<HTMLDivElement>(null)
  const [step, setStep] = useState(0)

  useLayoutEffect(() => {
    const mm = gsap.matchMedia()
    mm.add(WIDE, () => {
      const panels = track.current!.children as HTMLCollectionOf<HTMLElement>
      gsap.to(track.current, {
        x: () => -(panels[N - 1].offsetLeft - panels[0].offsetLeft),
        ease: 'none',
        scrollTrigger: {
          trigger: wrap.current, start: 'top top+=60', end: 'bottom bottom', scrub: 0.5, invalidateOnRefresh: true,
          // nearest step, not velocity-projected: a flick or an anchor jump must not overshoot to the far end
          snap: { snapTo: 1 / (N - 1), inertia: false, duration: { min: 0.2, max: 0.5 }, delay: 0.1, ease: 'power2.inOut' },
          onUpdate: (st) => setStep(Math.round(st.progress * (N - 1))),
        },
      })
    })
    return () => mm.revert()
  }, [])
  // the intro text above grows once the demo row arrives; re-measure the scroll range
  useEffect(() => { ScrollTrigger.refresh() }, [row])

  const face = Math.min(step, 6)
  return (
    <div ref={wrap} className="journey">
      <div className="journey-stage">
        <div className="journey-head">{children}</div>
        <div className="journey-rail">
          <div ref={track} className="journey-track">
            {STEPS.map(([title, body], i) => (
              <article key={title} className="journey-panel" data-on={step === i || undefined}>
                <div className="journey-stop" aria-hidden><span /></div>
                <Text className="sec-tag">[{String(i + 1).padStart(2, '0')}]</Text>
                <Title order={3} fz="1.35rem" mt={6}>{title}</Title>
                <Text fz="1.02rem" lh={1.55} c="var(--text)" mt={8}>{body}</Text>
              </article>
            ))}
            <article className="journey-panel journey-cta" data-on={step === N - 1 || undefined}>
              <div className="journey-stop" aria-hidden><span /></div>
              <Title order={3} fz="1.35rem">Try step 1 right now</Title>
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
            </article>
          </div>

          {row && (
            <div className="journey-crate" aria-hidden>
              {/* step 7: the road ahead closes and the crate hops onto a new lane */}
              <AnimatePresence>
                {face === 6 && (
                  <m.svg key="detour" className="journey-detour" viewBox="0 0 240 60" initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                    {/* starts on the road behind the crate, climbs to the crate's new lane; X = the closed road ahead */}
                    <m.path d="M-30,52 C0,52 0,8 30,8 L240,8" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
                      transition={{ duration: 0.6, ease: 'easeOut' }} />
                    <g className="journey-closed"><path d="M60,42 l20,20 M80,42 l-20,20" /></g>
                  </m.svg>
                )}
              </AnimatePresence>
              <m.div layout className="crate" animate={{ y: face === 6 ? -44 : 0 }} transition={spring.bouncy}>
                <AnimatePresence mode="popLayout" initial={false}>
                  <m.div key={face >= 4 && face <= 5 ? face : 'box'} layout="position"
                    initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.92 }}
                    transition={spring.snappy}>
                    <CrateFace s={face} r={row} />
                  </m.div>
                </AnimatePresence>
              </m.div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
