// Plan tab (ARCHITECTURE §15–§16): dispatch table, reason cards, discount cards, shelf-life map.
// Every number is a served field (DATABASE §5.9–§5.10), only rounded for display.
import { Alert, Paper, Skeleton, Stack, Text } from '@mantine/core'
import { IconAlertTriangle, IconClipboardOff, IconFileUnknown } from '@tabler/icons-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { DiscountCards, cardLayoutId } from '../components/plan/DiscountCards'
import { Dispatch, rowLayoutId } from '../components/plan/Dispatch'
import { ReasonDrawer, type DrawerOpen } from '../components/plan/ReasonDrawer'
import { ShelfLifeMap } from '../components/plan/ShelfLifeMap'
import '../components/plan/plan.css'
import type { Names } from '../lib/words'
import type { DiscountAdvice, DispatchRow, DispatchSheet, ReasonCard, ReasonCards, RunDetail } from '../types'

function Empty({ icon: Icon, text }: { icon: typeof IconFileUnknown; text: string }) {
  return (
    <Stack align="center" gap={6} py="xl" c="dimmed">
      <Icon size={40} stroke={1.3} /><Text c="dimmed">{text}</Text>
    </Stack>
  )
}

// `rev` bumps when a live solve publishes a better plan under the same run id: refetch, keep the old one on screen.
export function Plan({ run, runId, rev }: { run: RunDetail; runId: string; rev?: number }) {
  const scenario = run.scenario.split(/[\\/]/).pop() ?? run.scenario
  const [sheet, setSheet] = useState<DispatchSheet | null | undefined>(undefined)
  const [cards, setCards] = useState<ReasonCards | undefined>(undefined)
  const [advice, setAdvice] = useState<DiscountAdvice | undefined>(undefined)
  const [geoNames, setGeoNames] = useState<Names>({})
  const [open, setOpen] = useState<DrawerOpen | undefined>(undefined) // undefined = drawer closed
  const [dest, setDest] = useState<string | undefined>(undefined) // map pick → dispatch display filter
  const [error, setError] = useState('')
  const close = useCallback(() => setOpen(undefined), [])
  const shown = useRef(runId)

  useEffect(() => {
    if (shown.current !== runId) {
      shown.current = runId
      setSheet(undefined); setCards(undefined); setOpen(undefined); setDest(undefined); setAdvice(undefined)
    }
    setError('')
    let stale = false
    const fail = (what: string) => (e: Error) => !stale && setError(`Couldn't load ${what}. Try refreshing the page. (${e.message})`)
    api.dispatchSheet(runId).then(s => !stale && setSheet(s)).catch(fail('the truck loading list'))
    api.discountAdvice(runId).then(a => !stale && setAdvice(a)).catch(() => !stale && setAdvice(null)) // optional extra, never an error banner
    api.reasonCards(runId).then(c => !stale && setCards(c)).catch(fail('the explanations for each shipment'))
    return () => { stale = true }
  }, [runId, rev])
  useEffect(() => { // market names for the reason cards; ids stay on screen if geo.csv is missing
    api.geo(scenario).then(g => setGeoNames(Object.fromEntries(g.map(r => [String(r.node_id), String(r.name).split(',')[0]]))))
      .catch(() => setGeoNames({}))
  }, [scenario])
  const names: Names = { ...Object.fromEntries((sheet?.csv ?? []).map(r => [r.dest_id, r.dest_name])), ...geoNames }

  // dispatch rows carry no shipment_id; priority_rank + batch_id identify the plan row (§5.2, §5.10)
  const openRow = useCallback((r: DispatchRow) => setOpen({
    card: cards?.find(c => c.priority.rank === r.priority_rank && c.batch_id === r.batch_id) ?? null,
    layoutId: rowLayoutId(r), from: 'row',
  }), [cards])
  const openCard = (c: ReasonCard) => setOpen({ card: c, layoutId: cardLayoutId(c), from: 'card' })

  return (
    <Stack gap="xl" pb="xl" className="plan">
      {error && <Alert color="red" icon={<IconAlertTriangle />} title="Something didn't load">{error}</Alert>}
      {sheet === undefined ? <>
        <Paper withBorder radius="md" p="md"><Skeleton h={22} w={260} mb="sm" /><Skeleton h={380} /></Paper>
        <Stack gap={8}><Skeleton h={22} w={200} />{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} h={30} />)}</Stack>
      </>
        : sheet ? <>
          {/* the landing page's hero board morphs into this one (App.tsx view transition) */}
          <div>
            <ShelfLifeMap scenario={scenario} runId={runId} rev={rev} rows={sheet.csv} filter={dest} onPick={setDest} />
          </div>
          <Dispatch sheet={sheet} runId={runId} onRow={openRow} filter={dest} onClear={() => setDest(undefined)} />
        </>
        : <Empty icon={IconClipboardOff} text="No loading list was saved for this result." />}
      {cards === null && <Empty icon={IconFileUnknown} text="No explanations or price cuts were saved for this result." />}
      {cards === undefined && sheet !== undefined && <Skeleton h={120} />}
      {cards && <DiscountCards cards={cards} advice={advice ?? null} onOpen={openCard} names={names} />}
      <ReasonDrawer open={open} onClose={close} names={names} />
    </Stack>
  )
}
