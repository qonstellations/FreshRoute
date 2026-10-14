// Plan tab (ARCHITECTURE §15–§16): dispatch table, reason cards, discount cards, shelf-life map.
// Every number is a served field (DATABASE §5.9–§5.10), only rounded for display.
import { Alert, Paper, Skeleton, Stack, Text } from '@mantine/core'
import { IconAlertTriangle, IconClipboardOff, IconFileUnknown } from '@tabler/icons-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { DiscountCards, cardLayoutId } from '../components/plan/DiscountCards'
import { Dispatch, rowLayoutId } from '../components/plan/Dispatch'
import { ReasonDrawer, type DrawerOpen } from '../components/plan/ReasonDrawer'
import { ShelfLifeMap } from '../components/plan/ShelfLifeMap'
import '../components/plan/plan.css'
import type { DispatchRow, DispatchSheet, ReasonCard, ReasonCards, RunDetail } from '../types'

function Empty({ icon: Icon, text }: { icon: typeof IconFileUnknown; text: string }) {
  return (
    <Stack align="center" gap={6} py="xl" c="dimmed">
      <Icon size={40} stroke={1.3} /><Text c="dimmed">{text}</Text>
    </Stack>
  )
}

export function Plan({ run, runId }: { run: RunDetail; runId: string }) {
  const [sheet, setSheet] = useState<DispatchSheet | null | undefined>(undefined)
  const [cards, setCards] = useState<ReasonCards | undefined>(undefined)
  const [open, setOpen] = useState<DrawerOpen | undefined>(undefined) // undefined = drawer closed
  const [error, setError] = useState('')
  const close = useCallback(() => setOpen(undefined), [])

  useEffect(() => {
    setSheet(undefined); setCards(undefined); setOpen(undefined); setError('')
    const fail = (what: string) => (e: Error) => setError(`Cannot load ${what}: ${e.message}`)
    api.dispatchSheet(runId).then(setSheet).catch(fail('dispatch sheet'))
    api.reasonCards(runId).then(setCards).catch(fail('reason cards'))
  }, [runId])

  // dispatch rows carry no shipment_id; priority_rank + batch_id identify the plan row (§5.2, §5.10)
  const openRow = (r: DispatchRow) => setOpen({
    card: cards?.find(c => c.priority.rank === r.priority_rank && c.batch_id === r.batch_id) ?? null,
    layoutId: rowLayoutId(r), from: 'row',
  })
  const openCard = (c: ReasonCard) => setOpen({ card: c, layoutId: cardLayoutId(c), from: 'card' })

  return (
    <Stack gap="xl" pb="xl" className="plan">
      {error && <Alert color="red" icon={<IconAlertTriangle />} title="Load error">{error}</Alert>}
      {sheet === undefined ? <>
        <Paper withBorder radius="md" p="md"><Skeleton h={22} w={260} mb="sm" /><Skeleton h={380} /></Paper>
        <Stack gap={8}><Skeleton h={22} w={200} />{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} h={30} />)}</Stack>
      </>
        : sheet ? <>
          <ShelfLifeMap scenario={run.scenario.split(/[\\/]/).pop() ?? run.scenario} runId={runId} rows={sheet.csv} />
          <Dispatch sheet={sheet} runId={runId} onRow={openRow} />
        </>
        : <Empty icon={IconClipboardOff} text="No dispatch sheet for this run." />}
      {cards === null && <Empty icon={IconFileUnknown} text="No reason cards for this run." />}
      {cards === undefined && sheet !== undefined && <Skeleton h={120} />}
      {cards && <DiscountCards cards={cards} onOpen={openCard} />}
      <ReasonDrawer open={open} onClose={close} />
    </Stack>
  )
}
