// The saved demo run the landing page draws from (ARCHITECTURE §16). Served files only: the dispatch sheet rows.
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { DispatchRow } from '../types'

export const DEMO_RUN = 'practice__milp__s42'

export interface DemoDay { rows: DispatchRow[] }

// ponytail: one shared request for the guide's crate; retried after a failure.
let once: Promise<DemoDay> | undefined
function load(): Promise<DemoDay> {
  once ??= api.dispatchSheet(DEMO_RUN).then(sheet => ({ rows: sheet?.csv ?? [] }))
  once.catch(() => { once = undefined })
  return once
}

/** undefined while loading, null when the demo run is not on disk. */
export function useDemoDay() {
  const [day, setDay] = useState<DemoDay | null | undefined>(undefined)
  useEffect(() => {
    let live = true
    load().then(d => live && setDay(d), () => live && setDay(null))
    return () => { live = false }
  }, [])
  return day
}
