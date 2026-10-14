// ARCHITECTURE §16.1: the ONLY arithmetic in the UI — a display delta between two stored numbers.
// Plus display-only waterfall bar placement. Everything else here is formatting.

/** ours − baseline, or null when there is no baseline. */
export function delta(ours: number, baseline: number | null | undefined): number | null {
  return baseline == null ? null : ours - baseline
}

/** DISPLAY-ONLY: [low, high] bar extents for waterfall.json steps (running total for placement).
 * Steps and their values are the engine's; this only decides where each floating bar is drawn. */
export function waterfallBars<T extends { value: number; type: 'total' | 'delta' }>(steps: T[]) {
  let run = 0
  const ends: number[] = []
  const bars = steps.map(s => {
    const from = s.type === 'total' ? 0 : run
    run = s.type === 'total' ? s.value : run + s.value
    ends.push(run)
    if (s.type === 'delta') ends.push(from)
    return { ...s, range: [Math.min(from, run), Math.max(from, run)] as [number, number] }
  })
  // axis floor so small deltas stay visible next to large totals (totals are clipped at it)
  const lo = Math.min(...ends), hi = Math.max(...ends)
  const floor = lo <= 0 ? lo : Math.max(0, lo - 0.25 * (hi - lo || Math.abs(hi)))
  return { bars, floor }
}

const nf =(digits: number) =>
  new Intl.NumberFormat('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })

export const fmt = (x: number, digits = 0) => nf(digits).format(x)

export const fmtSigned = (x: number, digits = 0, unit = '') =>
  `${x > 0 ? '+' : x < 0 ? '−' : '±'}${fmt(Math.abs(x), digits)}${unit}`
