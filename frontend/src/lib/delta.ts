// ARCHITECTURE §16.1: the ONLY arithmetic in the UI — a display delta between two stored numbers.
// Everything else here is formatting.

/** ours − baseline, or null when there is no baseline. */
export function delta(ours: number, baseline: number | null | undefined): number | null {
  return baseline == null ? null : ours - baseline
}

const nf = (digits: number) =>
  new Intl.NumberFormat('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })

export const fmt = (x: number, digits = 0) => nf(digits).format(x)

export const fmtSigned = (x: number, digits = 0, unit = '') =>
  `${x > 0 ? '+' : x < 0 ? '−' : '±'}${fmt(Math.abs(x), digits)}${unit}`
