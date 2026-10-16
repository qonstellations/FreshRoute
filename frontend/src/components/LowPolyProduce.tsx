// Low-poly produce spilling out of a crate, for the landing hero (decoration only, no data).
// Each piece is a faceted SVG lit from the top left, so it reads as 3-D without a 3-D library. Pieces pop in once,
// bob gently, lean away from the pointer by their depth, and spring when hovered. Reduced motion: still pictures.
import { m, useMotionValue, useReducedMotion, useSpring, useTransform, type MotionValue } from 'motion/react'
import { useEffect, type ReactNode } from 'react'
import { spring } from '../theme'

type Pt = [number, number]
type Hsl = [number, number, number]
const LIGHT: Pt = [-0.6, -0.8] // light comes from the top left

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v))
const hsl = ([h, s, l]: Hsl) => `hsl(${h.toFixed(0)} ${s}% ${clamp(l, 8, 94).toFixed(1)}%)`
const P = (pts: Pt[]) => pts.map(p => p.join(',')).join(' ')

// An ellipse of n points; `wob` nudges each radius so the outline is not perfectly smooth.
function ring(cx: number, cy: number, rx: number, ry: number, n: number, wob: number[] = [1], rot = 0): Pt[] {
  return Array.from({ length: n }, (_, i) => {
    const a = rot + (i / n) * Math.PI * 2, k = wob[i % wob.length]
    return [cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]
  })
}

// Facet shade: brighter where the facet faces the light, darker toward the rim; a little jitter per facet.
function shade(base: Hsl, tri: Pt[], c: Pt, r: number, i: number, tint?: (dx: number, dy: number) => number): string {
  const x = (tri[0][0] + tri[1][0] + tri[2][0]) / 3, y = (tri[0][1] + tri[1][1] + tri[2][1]) / 3
  const dx = (x - c[0]) / r, dy = (y - c[1]) / r
  const face = dx * LIGHT[0] + dy * LIGHT[1]
  return hsl([base[0] + (tint?.(dx, dy) ?? 0), base[1], base[2] + face * 13 - Math.hypot(dx, dy) * 7 + ((i * 7) % 3 - 1) * 2.2])
}

// Dome facets: outer ring -> a half-step inner ring -> centre. Covers any star-shaped outline.
function dome(outline: Pt[], c: Pt, base: Hsl, tint?: (dx: number, dy: number) => number) {
  const n = outline.length
  const r = Math.max(...outline.map(p => Math.hypot(p[0] - c[0], p[1] - c[1])))
  const mid = outline.map((p, i) => {
    const q = outline[(i + 1) % n]
    return [c[0] + ((p[0] + q[0]) / 2 - c[0]) * 0.55, c[1] + ((p[1] + q[1]) / 2 - c[1]) * 0.55] as Pt
  })
  const tris: Pt[][] = []
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n, h = (i + n - 1) % n
    tris.push([outline[i], outline[j], mid[i]], [mid[h], outline[i], mid[i]], [mid[h], mid[i], c])
  }
  return tris.map((t, i) => <polygon key={i} points={P(t)} fill={shade(base, t, c, r, i, tint)} stroke={shade(base, t, c, r, i, tint)} strokeWidth={0.4} />)
}

const rotate = (pts: Pt[], c: Pt, deg: number): Pt[] => {
  const a = (deg * Math.PI) / 180, s = Math.sin(a), k = Math.cos(a)
  return pts.map(([x, y]) => [c[0] + (x - c[0]) * k - (y - c[1]) * s, c[1] + (x - c[0]) * s + (y - c[1]) * k])
}

const LEAF: Hsl = [118, 48, 36]

function Tomato() {
  const body = ring(50, 57, 40, 34, 12, [1, .97, 1.02, .96, 1, .98, 1.03, .97, 1, .96, 1.02, .98], -Math.PI / 2)
  const star = Array.from({ length: 5 }, (_, i) => {
    const a = -Math.PI / 2 + (i / 5) * Math.PI * 2 + 0.3
    const tip: Pt = [50 + Math.cos(a) * 16, 27 + Math.sin(a) * 7]
    const l: Pt = [50 + Math.cos(a - 0.5) * 4, 27 + Math.sin(a - 0.5) * 3], r: Pt = [50 + Math.cos(a + 0.5) * 4, 27 + Math.sin(a + 0.5) * 3]
    return <polygon key={i} points={P([l, tip, r])} fill={hsl([LEAF[0], LEAF[1], LEAF[2] + (i % 2 ? 6 : -2)])} />
  })
  return <svg viewBox="0 0 100 100">{dome(body, [46, 52], [5, 78, 52])}{star}
    <polygon points="48,27 52,27 53,16 49,15" fill={hsl([90, 40, 30])} /></svg>
}

function Mango() {
  const body = rotate(ring(50, 56, 30, 40, 11, [1, .98, 1.04, 1, .96, 1, 1.02, .97, 1, 1.03, .99], -Math.PI / 2), [50, 56], 24)
  // red blush on the upper right, yellow elsewhere
  return <svg viewBox="0 0 100 100">{dome(body, [46, 50], [40, 92, 55], (dx, dy) => (dx > 0 && dy < 0.2 ? -(dx - dy) * 16 : 0))}
    <polygon points="58,20 74,8 80,16" fill={hsl([LEAF[0], LEAF[1], LEAF[2] + 6])} />
    <polygon points="58,20 80,16 70,24" fill={hsl(LEAF)} />
    <polygon points="56,22 59,18 61,13 58,12" fill={hsl([30, 40, 30])} /></svg>
}

function Onion() {
  const body: Pt[] = [[50, 14], [60, 30], [74, 46], [80, 62], [74, 80], [60, 90], [50, 92], [40, 90], [26, 80], [20, 62], [26, 46], [40, 30]]
  return <svg viewBox="0 0 100 100">{dome(body, [46, 60], [318, 42, 46])}
    <g stroke={hsl([LEAF[0], LEAF[1], LEAF[2] + 8])} strokeWidth={3} strokeLinecap="round">
      <line x1={50} y1={16} x2={44} y2={2} /><line x1={50} y1={16} x2={56} y2={1} /></g>
    <g stroke={hsl([35, 40, 40])} strokeWidth={1.4} strokeLinecap="round">
      <line x1={50} y1={92} x2={45} y2={98} /><line x1={50} y1={92} x2={50} y2={99} /><line x1={50} y1={92} x2={55} y2={98} /></g></svg>
}

function Potato() {
  const body = ring(50, 55, 42, 30, 11, [1, .9, 1.05, .95, 1.08, .92, 1, .96, 1.04, .9, 1], 0.3)
  return <svg viewBox="0 0 100 100">{dome(body, [46, 50], [33, 48, 58])}
    {[[34, 48], [62, 44], [56, 68], [76, 58]].map(([x, y], i) =>
      <ellipse key={i} cx={x} cy={y} rx={2.2} ry={1.4} fill={hsl([28, 40, 34])} />)}</svg>
}

function Spinach() {
  const body: Pt[] = [[50, 8], [64, 18], [74, 36], [76, 56], [68, 74], [56, 86], [50, 90], [44, 86], [32, 74], [24, 56], [26, 36], [36, 18]]
  return <svg viewBox="0 0 100 100">{dome(body, [46, 46], [135, 50, 36])}
    <g stroke={hsl([110, 45, 62])} strokeWidth={1.4} strokeLinecap="round" fill="none" opacity={0.85}>
      <path d="M50,12 L50,98" /><path d="M50,40 L64,28 M50,56 L70,44 M50,40 L36,28 M50,56 L30,44 M50,72 L62,64 M50,72 L38,64" /></g></svg>
}

function Banana() {
  // a quadratic curve thickened along its normal: outer, middle and inner rows, two strips of facets
  const n = 9, rows: Pt[][] = [[], [], []]
  for (let i = 0; i <= n; i++) {
    const t = i / n, u = 1 - t
    const x = u * u * 10 + 2 * u * t * 46 + t * t * 92, y = u * u * 26 + 2 * u * t * 104 + t * t * 20
    const tx = 2 * u * 36 + 2 * t * 46, ty = 2 * u * 78 + 2 * t * -84, k = Math.hypot(tx, ty)
    const w = Math.sin(Math.PI * t) * 12 + 1.5
    rows.forEach((row, r) => row.push([x - (ty / k) * w * (1 - r), y + (tx / k) * w * (1 - r)]))
  }
  const f: ReactNode[] = []
  for (let s = 0; s < 2; s++) for (let i = 0; i < n; i++) {
    const a = rows[s], b = rows[s + 1], l = 60 + (s ? -9 : 6) + ((i * 5) % 3 - 1) * 2.5
    const col = hsl([48 - (i === 0 || i === n - 1 ? 18 : 0), 90, i === 0 || i === n - 1 ? l - 22 : l])
    f.push(<polygon key={`${s}a${i}`} points={P([a[i], a[i + 1], b[i]])} fill={col} stroke={col} strokeWidth={0.4} />,
      <polygon key={`${s}b${i}`} points={P([a[i + 1], b[i + 1], b[i]])} fill={col} stroke={col} strokeWidth={0.4} />)
  }
  return <svg viewBox="0 0 100 100">{f}<polygon points="88,22 96,10 99,13 92,24" fill={hsl([90, 30, 32])} /></svg>
}

function Crate() {
  const wood = (l: number) => hsl([30, 46, l])
  const planks = [0, 1, 2].map(i => {
    const y0 = 50 + i * 18, y1 = y0 + 15, inset = (y: number) => 14 + (y - 46) * 0.1
    return <polygon key={i} points={P([[inset(y0), y0], [160 - inset(y0), y0], [160 - inset(y1), y1], [inset(y1), y1]])}
      fill={wood(60 - i * 5)} />
  })
  return <svg viewBox="0 0 160 110">
    <polygon points="24,26 136,26 146,46 14,46" fill={wood(30)} />
    <polygon points="24,26 136,26 132,34 28,34" fill={wood(22)} />
    <polygon points="14,46 146,46 140,106 20,106" fill={wood(40)} />
    {planks}
    <polygon points="14,46 30,46 32,106 20,106" fill={wood(48)} /><polygon points="130,46 146,46 140,106 128,106" fill={wood(36)} />
  </svg>
}

const PIECES: { el: ReactNode; x: number; y: number; w: number; depth: number; rot: number; bob: number }[] = [
  { el: <Spinach />, x: 30, y: 10, w: 22, depth: 0.6, rot: -24, bob: 6.5 },
  { el: <Mango />, x: 52, y: 3, w: 25, depth: 0.9, rot: 10, bob: 5.2 },
  { el: <Tomato />, x: 6, y: 25, w: 29, depth: 1.3, rot: -6, bob: 5.8 },
  { el: <Banana />, x: 56, y: 26, w: 38, depth: 1.1, rot: -8, bob: 6.1 },
  { el: <Onion />, x: 2, y: 54, w: 21, depth: 1.5, rot: 12, bob: 4.9 },
  { el: <Potato />, x: 74, y: 60, w: 25, depth: 1.4, rot: -14, bob: 5.5 },
]

function Piece({ i, p, px, py, still }: { i: number; p: typeof PIECES[number]; px: MotionValue<number>; py: MotionValue<number>; still: boolean }) {
  const x = useTransform(px, v => v * p.depth * -26), y = useTransform(py, v => v * p.depth * -20)
  return (
    <m.div className="produce-piece" style={{ left: `${p.x}%`, top: `${p.y}%`, width: `${p.w}%`, x, y }}
      initial={still ? false : { scale: 0, opacity: 0, y: 60 }} animate={{ scale: 1, opacity: 1, rotate: p.rot }}
      whileHover={{ scale: 1.14, rotate: p.rot + 12 }}
      transition={{ ...spring.bouncy, delay: still ? 0 : 0.35 + i * 0.09 }}>
      <div className="produce-bob" style={{ animationDuration: `${p.bob}s`, animationDelay: `${-i * 0.8}s` }}>{p.el}</div>
    </m.div>
  )
}

export function ProducePile() {
  const still = !!useReducedMotion()
  const mx = useMotionValue(0), my = useMotionValue(0)
  const px = useSpring(mx, spring.soft), py = useSpring(my, spring.soft)
  useEffect(() => {
    if (still) return
    const move = (e: PointerEvent) => { mx.set(e.clientX / innerWidth - 0.5); my.set(e.clientY / innerHeight - 0.5) }
    addEventListener('pointermove', move)
    return () => removeEventListener('pointermove', move)
  }, [still, mx, my])
  return (
    <div className="produce-stage" aria-hidden>
      <div className="produce-shadow" />
      <m.div className="produce-crate" initial={still ? false : { y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
        transition={{ ...spring.soft, delay: 0.15 }}><Crate /></m.div>
      {PIECES.map((p, i) => <Piece key={i} i={i} p={p} px={px} py={py} still={still} />)}
    </div>
  )
}
