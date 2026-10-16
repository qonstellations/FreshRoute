// POST /api/runs, then poll GET /api/runs/{id}/status every second until done/error (D-21).
import { Box, Button, Loader, Tooltip } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconCheck, IconPlayerPlayFilled } from '@tabler/icons-react'
import { AnimatePresence, m } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { api, pollSleep } from '../api/client'
import { NO_SOLVES_HINT, useLiveSolves } from '../api/useLiveSolves'
import { spring } from '../theme'
import type { PostRunRequest, Progress } from '../types'

// ponytail: decorative burst only (produce colours, fixed geometry), carries no data
const PRODUCE = ['#e03131', '#f76707', '#fab005', '#74b816', '#2f9e44', '#ae3ec9']
const BURST = Array.from({ length: 10 }, (_, i) => {
  const a = (i / 10) * 2 * Math.PI
  return { x: Math.cos(a) * 70, y: Math.sin(a) * 34, color: PRODUCE[i % PRODUCE.length] }
})

export function RunButton({ request, onDone, onProgress, onError }: {
  request: PostRunRequest
  onDone: (runId: string) => void
  onProgress?: (runId: string, p: Progress) => void // a better plan is on disk; the run keeps improving
  onError: (msg: string) => void
}) {
  const live = useLiveSolves()
  const mounted = useRef(true)
  // stop polling after navigating away; set true on (re)mount, or StrictMode's dev remount leaves it false and the
  // loop quits after its first sleep: the run finishes on the server but the page never hears about it
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const [busy, setBusy] = useState<string | null>(null)
  const [improving, setImproving] = useState(false) // a first plan is already on screen
  const [done, setDone] = useState<number | null>(null) // set per success: re-keys the burst + check

  function fail(msg: string) {
    onError(msg)
    notifications.show({ color: 'red', title: 'Could not make a plan', message: msg })
  }

  async function run() {
    if (busy) return
    onError('')
    try {
      const { run_id } = await api.postRun(request)
      setBusy(run_id)
      let seen = 0
      for (;;) {
        await pollSleep(1000)
        if (!mounted.current) return
        const s = await api.status(run_id)
        if (s.progress && s.progress.version > seen) { seen = s.progress.version; setImproving(true); onProgress?.(run_id, s.progress) }
        if (s.state === 'done') {
          setDone(Date.now())
          setTimeout(() => setDone(null), 1800) // back to the idle label
          notifications.show({ color: 'green', title: 'Plan ready', message: 'Your plan is ready. Results are up to date.', icon: <IconCheck size={18} /> })
          return onDone(run_id)
        }
        if (s.state === 'error') return fail(`Planning stopped with an error (${run_id}): ${s.error ?? 'unknown error'}`)
      }
    } catch (err) {
      fail(String(err instanceof Error ? err.message : err))
    } finally {
      setBusy(null)
      setImproving(false)
    }
  }

  const state = busy ? 'busy' : done !== null ? 'done' : 'idle'

  return (
    <Box pos="relative">
      <Tooltip multiline w={280} withArrow
        label={live ? 'Works out the best plan for the day (takes up to 30 seconds). A first plan shows in about 1 second and keeps getting better while you watch.' : NO_SOLVES_HINT}>
      <Button fullWidth size="md" radius="md" onClick={run} disabled={!request.scenario || !live}
        aria-busy={!!busy} className="plan-btn" data-state={state}
        style={{ overflow: 'hidden', cursor: busy ? 'progress' : undefined }}>
        {busy && <span className="plan-btn-sweep" aria-hidden />}
        <AnimatePresence mode="popLayout" initial={false}>
          <m.span key={state} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, position: 'relative' }}
            initial={{ opacity: 0, y: 14, scale: 0.9 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -14, scale: 0.9 }} transition={spring.snappy}>
            {state === 'busy' && <><Loader size={16} color="white" type="dots" /> {improving ? 'Improving the plan…' : 'Planning…'}</>}
            {state === 'done' && <>
              <m.span style={{ display: 'inline-flex' }} initial={{ scale: 0, rotate: -45 }}
                animate={{ scale: 1, rotate: 0 }} transition={spring.bouncy}><IconCheck size={18} stroke={3} /></m.span>
              Done
            </>}
            {state === 'idle' && <><IconPlayerPlayFilled size={16} /> Make my plan</>}
          </m.span>
        </AnimatePresence>
      </Button>
      </Tooltip>
      {/* one-shot burst, re-keyed per success */}
      {state === 'done' && (
        <Box key={done} pos="absolute" inset={0} style={{ pointerEvents: 'none' }} aria-hidden>
          {BURST.map((p, i) => (
            <m.span key={i} className="burst-dot" style={{ background: p.color }}
              initial={{ x: 0, y: 0, scale: 0.4, opacity: 1 }}
              animate={{ x: p.x, y: p.y, scale: [0.4, 1.2, 0], opacity: [1, 1, 0] }}
              transition={{ ...spring.bouncy, scale: { duration: 0.9 }, opacity: { duration: 0.9 } }} />
          ))}
        </Box>
      )}
    </Box>
  )
}
