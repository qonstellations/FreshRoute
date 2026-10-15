// Plan tab display helpers (ARCHITECTURE §15–§16): formatting and colour bands only, no KPI maths.
import type { ReasonCode } from '../../types'

export const num = (v: number | null | undefined) =>
  v == null ? '' : v.toLocaleString('en-IN', { maximumFractionDigits: 1 })

export const signed = (v: number) => (v > 0 ? '+' : '') + num(v)

// ponytail: display bands for colour only, not a model parameter; move to config if the engine ever owns them
export const band = (h: number) => (h < 6 ? ['#c0392b', '< 6 h to spare (urgent)', 'red'] : h < 24 ? ['#e08e0b', '6–24 h to spare', 'orange'] : ['#1f7a4d', '24 h+ to spare', 'green'])
export const BANDS = [band(0), band(12), band(48)]
export const HUB = '#5b6575'

// Fixed display scale for the shelf-life fuse: a bar at full width means ≥ this many hours of slack.
export const FUSE_SCALE_H = 48
export const fuseFrac = (slackH: number) => Math.min(Math.max(slackH / FUSE_SCALE_H, 0), 1)

// Plain words for why a discount stopped where it did (served discount.capped_by).
export const cappedText = (c: string) =>
  c === 'max_discount' ? 'limited by the largest discount allowed'
    : c === 'salvage_floor' ? 'limited so the price stays above scrap value' : `limited by ${c}`

export const REASON_COLOUR: Record<ReasonCode, string> = {
  SHELF_LIFE: 'red', WINDOW: 'orange', CAPACITY_BOUND: 'grape', DEMAND_CAP: 'blue', LOWER_MARGIN: 'gray',
}
