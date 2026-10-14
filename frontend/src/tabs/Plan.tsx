// Plan tab (ARCHITECTURE §15–§16): dispatch table, reason cards, discount cards, shelf-life map.
// Every number is a served field (DATABASE §5.9–§5.10), only rounded for display.
import { Alert, Paper, Skeleton, Stack, Text } from '@mantine/core'
import { IconAlertTriangle, IconClipboardOff, IconFileUnknown } from '@tabler/icons-react'
import { m } from 'motion/react'
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import { DiscountCards, cardLayoutId } from '../components/plan/DiscountCards'
import { Dispatch, rowLayoutId } from '../components/plan/Dispatch'
import { ReasonDrawer, type DrawerOpen } from '../components/plan/ReasonDrawer'
import { ShelfLifeMap } from '../components/plan/ShelfLifeMap'
import '../components/plan/plan.css'
import { spring } from '../theme'
import type { DispatchRow, DispatchSheet, ReasonCard, ReasonCards, RunDetail } from '../types'

function Empty({ icon: Icon, text }: { icon: typeof IconFileUnknown; text: string }) {
  return (
    <Stack align="center" gap={6} py="xl" c="dimmed">
      <Icon size={40} stroke={1.3} /><Text c="dimmed">{text}</Text>
    </Stack>
  )
}

// Story beats keep sections mounted and fold them away, so a reveal is a spring, not a remount.
function Reveal({ hidden, children }: { hidden?: boolean; children: ReactNode }) {
  if (hidden === undefined) return children // normal mode: no wrapper
  return (
    <m.div initial={false} aria-hidden={hidden || undefined} inert={hidden}
      animate={hidden ? { height: 0, opacity: 0, y: 24, overflow: 'hidden' }
        // height back to plain 'auto' once open, so content that loads or filters later is not clipped or overlapped
        : { height: 'auto', opacity: 1, y: 0, transitionEnd: { overflow: 'visible', height: 'auto' } }}
      transition={spring.soft}>
      {children}
    </m.div>
  )
}

/** step: presenter story beat (undefined = normal). 0 map only · 1 + dispatch sheet · 2 + rank-1 reason card. */
export function Plan({ run, runId, step }: { run: RunDetail; runId: string; step?: number }) {
  const [sheet, setSheet] = useState<DispatchSheet | null | undefined>(undefined)
  const [cards, setCards] = useState<ReasonCards | undefined>(undefined)
  const [open, setOpen] = useState<DrawerOpen | undefined>(undefined) // undefined = drawer closed
  const [dest, setDest] = useState<string | undefined>(undefined) // map pick → dispatch display filter
  const [error, setError] = useState('')
  const close = useCallback(() => setOpen(undefined), [])

  useEffect(() => {
    setSheet(undefined); setCards(undefined); setOpen(undefined); setDest(undefined); setError('')
    const fail = (what: string) => (e: Error) => setError(`Cannot load ${what}: ${e.message}`)
    api.dispatchSheet(runId).then(setSheet).catch(fail('dispatch sheet'))
    api.reasonCards(runId).then(setCards).catch(fail('reason cards'))
  }, [runId])

  // dispatch rows carry no shipment_id; priority_rank + batch_id identify the plan row (§5.2, §5.10)
  const openRow = useCallback((r: DispatchRow) => setOpen({
    card: cards?.find(c => c.priority.rank === r.priority_rank && c.batch_id === r.batch_id) ?? null,
    layoutId: rowLayoutId(r), from: 'row',
  }), [cards])
  const openCard = (c: ReasonCard) => setOpen({ card: c, layoutId: cardLayoutId(c), from: 'card' })

  // Beat 2 opens the top-priority line's reason card; stepping back below it closes the drawer.
  useEffect(() => {
    if (step === undefined) return
    const top = step >= 2 ? sheet?.csv.find(r => r.priority_rank === 1) : undefined
    if (top) openRow(top)
    else setOpen(undefined)
  }, [step, sheet, openRow])

  const folded = step === undefined ? undefined : step === 0

  // Beat 1 brings the revealed dispatch sheet into view (Scoreboard scrolls its own beats the same way).
  const sheetRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (step !== 1) return
    const t = setTimeout(() => sheetRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 250)
    return () => clearTimeout(t)
  }, [step])

  return (
    <Stack gap="xl" pb="xl" className="plan">
      {error && <Alert color="red" icon={<IconAlertTriangle />} title="Load error">{error}</Alert>}
      {sheet === undefined ? <>
        <Paper withBorder radius="md" p="md"><Skeleton h={22} w={260} mb="sm" /><Skeleton h={380} /></Paper>
        <Stack gap={8}><Skeleton h={22} w={200} />{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} h={30} />)}</Stack>
      </>
        : sheet ? <>
          <ShelfLifeMap scenario={run.scenario.split(/[\\/]/).pop() ?? run.scenario} runId={runId} rows={sheet.csv}
            filter={dest} onPick={setDest} />
          <Reveal hidden={folded}>
            <div ref={sheetRef} style={{ scrollMarginTop: 80 }} />
            <Dispatch sheet={sheet} runId={runId} onRow={openRow} filter={dest} onClear={() => setDest(undefined)} />
          </Reveal>
        </>
        : <Empty icon={IconClipboardOff} text="No dispatch sheet for this run." />}
      <Reveal hidden={folded}>
        {cards === null && <Empty icon={IconFileUnknown} text="No reason cards for this run." />}
        {cards === undefined && sheet !== undefined && <Skeleton h={120} />}
        {cards && <DiscountCards cards={cards} onOpen={openCard} />}
      </Reveal>
      <ReasonDrawer open={open} onClose={close} />
    </Stack>
  )
}
