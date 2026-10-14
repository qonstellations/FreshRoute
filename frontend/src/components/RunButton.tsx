// POST /api/runs, then poll GET /api/runs/{id}/status every second until done/error (D-21).
import { useState } from 'react'
import { api } from '../api/client'
import type { PostRunRequest } from '../types'

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))

export function RunButton({ request, onDone, onError }: {
  request: PostRunRequest
  onDone: (runId: string) => void
  onError: (msg: string) => void
}) {
  const [busy, setBusy] = useState<string | null>(null)

  async function run() {
    onError('')
    try {
      const { run_id } = await api.postRun(request)
      setBusy(run_id)
      for (;;) {
        await sleep(1000)
        const s = await api.status(run_id)
        if (s.state === 'done') return onDone(run_id)
        if (s.state === 'error') return onError(`Run ${run_id} failed: ${s.error ?? 'unknown error'}`)
      }
    } catch (err) {
      onError(String(err instanceof Error ? err.message : err))
    } finally {
      setBusy(null)
    }
  }

  return (
    <button onClick={run} disabled={busy !== null || !request.scenario}>
      {busy ? `Running ${busy}…` : 'Plan'}
    </button>
  )
}
