// Whether this deployment can start solves (false on Vercel: saved runs only). Fetched once.
import { useEffect, useState } from 'react'
import { api } from './client'

let cached: Promise<boolean> | null = null
const probe = () => (cached ??= api.capabilities().then((c) => c.live_solves).catch(() => true))

export const NO_SOLVES_HINT = 'Live solves are off on this hosted demo. Browse the saved runs, or run the app locally (make api) to plan.'

export function useLiveSolves(): boolean {
  const [live, setLive] = useState(true) // optimistic: local dev never flickers
  useEffect(() => { probe().then(setLive) }, [])
  return live
}
