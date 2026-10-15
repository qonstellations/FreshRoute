// KPI tile: a stored value, rolled in like an odometer, plus an optional display delta (lib/delta.ts). ARCHITECTURE §16.
// Animation is display-only: every glyph rendered is a character of the served value's formatted string.
import { Badge, Group, Paper, Text } from '@mantine/core'
import { IconArrowDownRight, IconArrowUpRight, IconMinus } from '@tabler/icons-react'
import { m, useMotionValue, useReducedMotion, useSpring, useTransform, type Variants } from 'motion/react'
import type { PointerEvent } from 'react'
import type { Term } from '../lib/words'
import { spring } from '../theme'
import { Explain } from './Explain'

export type Tone = 'good' | 'bad' | 'neutral'

/** Tone for a delta; `lowerIsBetter` inverts the colour (spoilage). */
export function toneOf(d: number | null, lowerIsBetter = false): Tone {
  if (d == null || d === 0) return 'neutral'
  return (d > 0) !== lowerIsBetter ? 'good' : 'bad'
}

const DIGITS = '0123456789'

/** Rolls each digit of `text` from 0 to its final glyph on a spring. The DOM ends on exactly `text`
 * (screen readers get it whole via aria-label); the roll is interpolation for the eye only. */
export function Odometer({ text }: { text: string }) {
  const chars = [...text]
  return (
    <span className="odo" role="img" aria-label={text}>
      {chars.map((ch, i) => {
        const fromRight = chars.length - i // stable keys when the string grows/shrinks
        return DIGITS.includes(ch) ? (
          <span key={fromRight} className="odo-digit" aria-hidden>
            <m.span className="odo-col" initial={{ y: '0em' }} animate={{ y: `${-1.15 * Number(ch)}em` }}
              transition={{ ...spring.soft, delay: 0.05 * i }}>
              {[...DIGITS].map(d => <span key={d}>{d}</span>)}
            </m.span>
          </span>
        ) : <span key={fromRight} aria-hidden>{ch === ' ' ? ' ' : ch}</span> // flex drops bare spaces
      })}
    </span>
  )
}

/** Ring sweep to a served percentage. pct/100 is geometry for the arc, not a KPI. */
export function Ring({ pct, color }: { pct: number; color: string }) {
  const reduce = useReducedMotion()
  const frac = Math.min(1, Math.max(0, pct / 100))
  return (
    <svg width="52" height="52" viewBox="0 0 64 64" aria-hidden style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
      <circle cx="32" cy="32" r="26" fill="none" stroke="var(--mantine-color-gray-2)" strokeWidth="7" />
      <m.circle cx="32" cy="32" r="26" fill="none" stroke={color} strokeWidth="7" strokeLinecap="round"
        initial={{ pathLength: reduce ? frac : 0 }} animate={{ pathLength: frac }}
        transition={{ ...spring.soft, delay: 0.25 }} />
    </svg>
  )
}

export const tileVariants: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: spring.soft },
}

const toneColor = { good: 'green', bad: 'red', neutral: 'gray' } as const

export function KpiTile({ label, hint, value, delta, tone = 'neutral', ring, ringTone, sub }: {
  label: string; hint?: Term; value: string; delta?: string | null; tone?: Tone
  ring?: number; ringTone?: Tone; sub?: string
}) {
  const reduce = useReducedMotion()
  // pointer position 0..1 → springy tilt + shine (display only)
  const px = useMotionValue(0.5), py = useMotionValue(0.5)
  const sx = useSpring(px, { stiffness: spring.snappy.stiffness, damping: spring.snappy.damping })
  const sy = useSpring(py, { stiffness: spring.snappy.stiffness, damping: spring.snappy.damping })
  const rotateX = useTransform(sy, [0, 1], [7, -7])
  const rotateY = useTransform(sx, [0, 1], [-7, 7])
  const shineX = useTransform(sx, [0, 1], ['-40%', '40%'])
  const shineY = useTransform(sy, [0, 1], ['-40%', '40%'])
  const move = (e: PointerEvent<HTMLDivElement>) => {
    if (reduce) return
    const r = e.currentTarget.getBoundingClientRect()
    px.set((e.clientX - r.left) / r.width); py.set((e.clientY - r.top) / r.height)
  }
  const leave = () => { px.set(0.5); py.set(0.5) }
  const Arrow = delta?.startsWith('+') ? IconArrowUpRight : delta?.startsWith('−') ? IconArrowDownRight : IconMinus

  return (
    <m.div variants={tileVariants} whileHover={reduce ? undefined : { y: -6, transition: spring.snappy }}
      onPointerMove={move} onPointerLeave={leave}
      style={{ rotateX, rotateY, transformPerspective: 900 }} className="kpi-tile">
      <Paper withBorder radius="lg" p="lg" h="100%" className="kpi-paper">
        <m.div className="kpi-shine" style={{ x: shineX, y: shineY }} aria-hidden />
        <Text size="sm" c="dimmed" fw={600} tt="uppercase" lts={0.6}>{hint ? <Explain term={hint}>{label}</Explain> : label}</Text>
        <Text fz={28} fw={800} lh={1.2} mt={6}><Odometer text={value} /></Text>
        {sub && <Text size="sm" c="dimmed" mt={2}>{sub}</Text>}
        {(delta || ring != null) && (
          <Group justify="space-between" align="flex-end" wrap="nowrap" mt="md" gap="xs">
            {delta ? <Badge size="lg" radius="sm" variant="light" color={toneColor[tone]}
              leftSection={<Arrow size={16} stroke={2.5} />}>{delta}</Badge> : <span />}
            {ring != null && <Ring pct={ring} color={`var(--mantine-color-${toneColor[ringTone ?? 'neutral']}-6)`} />}
          </Group>
        )}
      </Paper>
    </m.div>
  )
}
