// Spoilage melt (ARCHITECTURE §16): a row of crates sized to the baseline's served spoilage kg melts down to ours.
// Crate count is geometry from lib/delta.ts ratio(); the only numbers shown are the two served kg values.
import { Text } from '@mantine/core'
import { AnimatePresence, m } from 'motion/react'
import { useEffect, useState } from 'react'
import { fmt, ratio } from '../../lib/delta'
import { spring } from '../../theme'

const N = 24 // crates for the baseline's spoilage

export function SpoilageMelt({ ours, base, oursName, baseName }: {
  ours: number; base: number; oursName: string; baseName: string
}) {
  const [melted, setMelted] = useState(false) // plays once per mount
  useEffect(() => { const id = setTimeout(() => setMelted(true), 700); return () => clearTimeout(id) }, [])
  const r = ratio(ours, base)
  if (r == null) return null
  // ponytail: ours > baseline is capped at N crates (nothing melts); the kg labels stay exact
  const kept = Math.min(N, Math.round(N * r))
  return (
    <div className="melt">
      <div className="melt-crates" aria-hidden>
        <AnimatePresence>
          {Array.from({ length: melted ? kept : N }, (_, i) => (
            <m.span key={i} className="melt-crate"
              exit={{ y: 24, opacity: 0, transition: { ...spring.soft, delay: 0.04 * (N - 1 - i) } }} />
          ))}
        </AnimatePresence>
      </div>
      <Text fz="lg" c="white" fw={600} mt={8}>
        Spoilage: {baseName} {fmt(base)} kg → {oursName} {fmt(ours)} kg
      </Text>
    </div>
  )
}
