// Inline hover note for an uncommon term (ARCHITECTURE §16). Text only; the wording lives in lib/words.ts.
import { Tooltip } from '@mantine/core'
import type { ReactNode } from 'react'
import { TERM, type Term } from '../lib/words'

/** `<Explain term="slack">Time to spare</Explain>`: label with a dotted underline; hover or focus shows the note. */
export function Explain({ term, note, children }: { term?: Term; note?: ReactNode; children: ReactNode }) {
  return (
    <Tooltip label={note ?? (term && TERM[term])} multiline w={280} withArrow events={{ hover: true, focus: true, touch: true }}>
      <span tabIndex={0} style={{ textDecoration: 'underline dotted', textUnderlineOffset: 3, cursor: 'help' }}>
        {children}
      </span>
    </Tooltip>
  )
}
