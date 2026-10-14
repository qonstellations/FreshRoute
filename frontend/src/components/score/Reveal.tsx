// Story-mode reveal (ARCHITECTURE §16): children stay mounted; hidden = opacity 0 (or collapsed height) and inert.
// Each reveal remounts the children so their own entrance springs (odometer, shield, crates) replay.
import { m } from 'motion/react'
import { useState, type ReactNode } from 'react'
import { spring } from '../../theme'

export function Reveal({ show, collapse = false, children }: { show: boolean; collapse?: boolean; children: ReactNode }) {
  const [n, setN] = useState(0)
  const [was, setWas] = useState(show)
  if (show !== was) { setWas(show); if (show) setN(n + 1) } // React's "adjust state on prop change" pattern
  const hidden = collapse ? { opacity: 0, height: 0 } : { opacity: 0 }
  // initial={false}: normal mode (always shown) renders exactly as without the wrapper
  return (
    <m.div initial={false} animate={show ? { opacity: 1, height: 'auto' } : hidden} transition={spring.soft}
      style={collapse ? { overflow: 'hidden' } : undefined} inert={!show} aria-hidden={!show}>
      <div key={n}>{children}</div>
    </m.div>
  )
}
