// A KPI tile: a stored value and an optional display delta (lib/delta.ts). ARCHITECTURE §16.
export type Tone = 'good' | 'bad' | 'neutral'

export function KpiTile({ label, value, delta, tone = 'neutral' }:
  { label: string; value: string; delta?: string | null; tone?: Tone }) {
  return (
    <div className="tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {delta && <div className={`tile-delta ${tone}`}>{delta}</div>}
    </div>
  )
}

/** Tone for a delta; `lowerIsBetter` inverts the colour (spoilage). */
export function toneOf(d: number | null, lowerIsBetter = false): Tone {
  if (d == null || d === 0) return 'neutral'
  return (d > 0) !== lowerIsBetter ? 'good' : 'bad'
}
