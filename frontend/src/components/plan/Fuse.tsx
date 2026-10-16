// Shelf-life fuse (ARCHITECTURE §16): a bar that burns down on mount to the served slack_h on a fixed display scale.
import { m } from 'motion/react'
import { spring } from '../../theme'
import { band, fuseFrac } from './format'
import './plan.css'

export function Fuse({ slackH, animate = true, delay = 0, width = 72 }:
  { slackH: number; animate?: boolean; delay?: number; width?: number }) {
  const frac = fuseFrac(slackH)
  return (
    <div className="fuse" style={{ width }} aria-hidden>
      <m.div className="fuse-fill" style={{ background: band(slackH)[0], originX: 0 }}
        initial={animate ? { scaleX: 1 } : false} animate={{ scaleX: frac }}
        transition={{ ...spring.soft, delay }} />
    </div>
  )
}
