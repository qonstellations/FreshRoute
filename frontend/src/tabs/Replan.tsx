// Replan tab (ARCHITECTURE §14.2, §16; DATABASE §5.13, §6): pick one of the 5 canned events, Apply (POST /api/replan,
// poll), then show diff.json as served: frozen count, moved batches (flying old → new destination), discount changes,
// ΔKPIs (served delta_kpis) and the server's narration. The engine re-solves; nothing here is computed.
import {
  Alert, Badge, Blockquote, Button, Group, NumberInput, Paper, Select, SimpleGrid, Stack, Table, Text, TextInput, ThemeIcon, Title,
} from '@mantine/core'
import { IconAlertTriangle, IconArrowRight, IconBolt, IconMessage2, IconRefresh, IconRestore, IconSnowflake, IconTruck } from '@tabler/icons-react'
import { LayoutGroup, m } from 'motion/react'
import { useEffect, useState } from 'react'
import { api, waitReplan } from '../api/client'
import { NO_SOLVES_HINT, useLiveSolves } from '../api/useLiveSolves'
import { ExampleBanner } from '../components/Banners'
import { Explain } from '../components/Explain'
import { KpiTile, toneOf } from '../components/KpiTile'
import { ShelfLifeMap } from '../components/plan/ShelfLifeMap'
import { fmt, fmtSigned } from '../lib/delta'
import { spring } from '../theme'
import type { Diff, DispatchRow, EventType, ReplanEvent, ReplanKpis, ReplanResult, TabProps } from '../types'

// The 5 canned events of DATABASE §6; magnitudes are the documented demo defaults (editable inputs, not coefficients).
type Ids = { dest: string; commodity: string; vehicle: string }
// `field` labels the magnitude input; `where` explains the target format in a hover note.
const CANNED: Record<EventType, { label: string; note: string; magnitude: number; field: string; where: string
  target: (i: Ids) => string }> = {
  route_delay: { label: 'Traffic jam on a highway (route delay)', note: 'highway traffic jam', magnitude: 6,
    field: 'Extra delay (hours)',
    where: 'Which roads, as from|to|truck type (* = any). Example: *|M3|* means every road into market M3.',
    target: i => `*|${i.dest}|*` },
  capacity_drop: { label: 'Refrigerated truck breaks down (loses capacity)', note: 'refrigerated truck breakdown', magnitude: 0.5,
    field: 'Share of capacity lost (0–1)',
    where: 'Which truck, as vehicle:<truck id>. Example: vehicle:V1 means truck V1.',
    target: i => `vehicle:${i.vehicle}` },
  demand_spike: { label: 'Festival demand spike at a market', note: 'festival demand', magnitude: 1.5,
    field: 'Demand multiplier (×)',
    where: 'Which market and produce, as dest:<market>|<produce> (* = any). Example: dest:M3|tomato.',
    target: i => `dest:${i.dest}|${i.commodity}` },
  new_order: { label: 'Surprise bulk order', note: 'walk-in bulk order', magnitude: 300,
    field: 'Extra order (kg)',
    where: 'Which market and produce, as dest:<market>|<produce>. Example: dest:M3|tomato.',
    target: i => `dest:${i.dest}|${i.commodity}` },
  price_shock: { label: 'Market price crash', note: 'market glut', magnitude: 0.8,
    field: 'Price multiplier (×)',
    where: 'Which market and produce, as dest:<market>|<produce> (* = any). Example: dest:M3|* means everything sold at M3.',
    target: i => `dest:${i.dest}|*` },
}
const TYPES = Object.keys(CANNED) as EventType[]
const AT_H = 8 // DATABASE §6 example event time
// A click on the map closes a road: a route_delay longer than the whole 3-day plan, so no arrival on it stays feasible
// and the engine stops using it (a 12 h delay left the road usable, so clicks looked like they did nothing).
const CLOSE_H = 72

type Form = Omit<ReplanEvent, 'event_id'>
const formFor = (type: EventType, ids: Ids): Form =>
  ({ type, target: CANNED[type].target(ids), magnitude: CANNED[type].magnitude, at_h: AT_H, note: CANNED[type].note })

export function Replan({ run, runId }: TabProps) {
  const live = useLiveSolves()
  const [ids, setIds] = useState<Ids>({
    dest: run.per_destination[0]?.dest_id ?? '*', commodity: run.per_commodity[0]?.commodity ?? '*', vehicle: '',
  })
  const [form, setForm] = useState<Form>(() => formFor('route_delay', ids))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ReplanResult | null>(null)
  const [rows, setRows] = useState<DispatchRow[]>([])
  const [closed, setClosed] = useState<[string, string] | null>(null) // the road a map click closed
  const [closedName, setClosedName] = useState('')

  // a vehicle id for the reefer-breakdown default, from the run's own dispatch sheet
  useEffect(() => {
    setResult(null); setError(''); setRows([]); setClosed(null)
    api.dispatchSheet(runId).then(s => {
      setRows(s?.csv ?? [])
      const v = s?.csv[0]?.vehicle_id
      if (v) setIds(i => ({ ...i, vehicle: v }))
    }).catch(() => { /* optional: the vehicle target stays editable */ })
  }, [runId])
  useEffect(() => { if (form.type === 'capacity_drop' && ids.vehicle) setForm(f => ({ ...f, target: CANNED.capacity_drop.target(ids) })) },
    [ids])

  async function apply(f: Form = form, road: [string, string] | null = null) {
    if (busy) return
    setBusy(true); setError(''); setResult(null); setClosed(road)
    // ponytail: time-based id, unique per click; the engine keys replan/<event_id>/ by it
    const event: ReplanEvent = { ...f, event_id: `E-${Date.now().toString(36).toUpperCase()}` }
    try {
      const r = await api.postReplan({ run_id: runId, event })
      setResult(await waitReplan(r.run_id, r.event_id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); setClosed(null)
    } finally { setBusy(false) }
  }

  // Break it live: a road click closes that road and replans at once; a destination click only fills the form.
  function closeRoad(o: string, d: string, name: string) {
    if (busy || !live) return
    setClosedName(name)
    const f: Form = { type: 'route_delay', target: `${o}|${d}|*`, magnitude: CLOSE_H, at_h: AT_H, note: `road ${o} → ${d} closed` }
    setForm(f); apply(f, [o, d])
  }
  // Back to the saved plan: the replan only ever wrote its own replan/<event_id>/ folder, so there is nothing to undo.
  function reset() {
    setResult(null); setError(''); setClosed(null); setForm(formFor('route_delay', ids))
  }
  const spikeAt = (d: string | undefined) => d && setForm(formFor('demand_spike', { ...ids, dest: d }))
  const after = result?.trips && { at_h: result.diff.at_h, routes: result.trips
    .filter(t => t.dispatch_h > result.diff.at_h).map(t => [t.origin, t.dest_id] as [string, string]) }

  const meta = CANNED[form.type]
  return (
    <Stack gap="lg">
      <ExampleBanner show={!!result?.example} what="replan" />
      {rows.length > 0 && (
        <Stack gap={4}>
          <Text fw={700}>Break the plan and watch FreshRoute recover</Text>
          <Text size="sm">1. Click any road on the map to close it from hour {AT_H} to the end of the plan. FreshRoute re-plans in a few
            seconds. Trucks that left before hour {AT_H} are already on the road and finish their trip.</Text>
          <Text size="sm">2. Or click a market to set up a demand spike there, or pick any event below and press “Re-plan now”.</Text>
          <Text size="sm" mb={4}>3. Below, see which shipments moved and how profit changed.</Text>
          <ShelfLifeMap scenario={run.scenario.split(/[\\/]/).pop() ?? run.scenario} runId={runId} rows={rows}
            onPick={spikeAt} onRoute={live ? closeRoad : undefined} after={after} closed={closed} busy={busy} />
          {(closed || result) && (
            <Group justify="space-between" gap="xs">
              <Text size="sm" fw={600} c={closed ? 'red' : undefined}>
                {closed ? (busy ? `Closing the road ${closedName} and re-planning…`
                  : `Road ${closedName} closed. ${result?.diff.moved_batches.length ?? 0} batches now go to a different market.`)
                  : 'Showing the re-planned routes.'}</Text>
              <Button size="compact-sm" variant="default" leftSection={<IconRestore size={14} />} onClick={reset} disabled={busy}>
                Reset to the saved plan</Button>
            </Group>
          )}
          {after && <Text size="xs" c="dimmed">Red ✕ = the road you closed · red dashed = roads the new plan stopped using · bold green = roads it uses now</Text>}
        </Stack>
      )}
      <Paper withBorder radius="lg" p="lg">
        <Group gap="md" mb="md" wrap="nowrap">
          <ThemeIcon size={44} radius="md" variant="light"><IconBolt size={26} /></ThemeIcon>
          <div>
            <Title order={3}>Something changed mid-day</Title>
            <Text size="sm" c="dimmed">Shipments already on the road are <Explain term="frozen">frozen</Explain>; FreshRoute re-plans everything else.</Text>
          </div>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }} spacing="sm">
          <Select label="What happened" value={form.type} allowDeselect={false} data={TYPES.map(t => ({ value: t, label: CANNED[t].label }))}
            onChange={v => v && setForm(formFor(v as EventType, ids))} style={{ gridColumn: 'span 2' }} />
          <TextInput label={<Explain note={meta.where}>Where</Explain>} value={form.target} onChange={e => setForm({ ...form, target: e.currentTarget.value })} />
          <NumberInput label={meta.field} value={form.magnitude} min={0} decimalScale={2}
            onChange={v => setForm({ ...form, magnitude: Number(v) })} />
          <NumberInput label="Happens at hour (of the 3-day plan)" value={form.at_h} min={0} decimalScale={1}
            onChange={v => setForm({ ...form, at_h: Number(v) })} />
        </SimpleGrid>
        <Group mt="md" justify="space-between" align="flex-end">
          <TextInput label="Your note (for the record only)" value={form.note ?? ''} w="100%" maw={320}
            onChange={e => setForm({ ...form, note: e.currentTarget.value })} />
          <Button size="md" radius="xl" leftSection={<IconRefresh size={18} />} loading={busy} onClick={() => apply()} title={live ? undefined : NO_SOLVES_HINT}
            disabled={!live || !form.target.trim()}>Re-plan now</Button>
        </Group>
      </Paper>
      {error && <Alert color="red" icon={<IconAlertTriangle />} title="Re-plan failed">{error}</Alert>}
      {result && <DiffView r={result} />}
    </Stack>
  )
}

const KPI_TILES: { key: keyof ReplanKpis; label: string; unit: string; digits: number; lowerIsBetter?: boolean
  show: (v: number) => string }[] = [
  { key: 'net_inr', label: 'Profit after re-planning', unit: ' ₹', digits: 0, show: v => `₹${fmt(v)}` },
  { key: 'spoilage_kg', label: 'Food spoiled after re-planning', unit: ' kg', digits: 0, lowerIsBetter: true, show: v => `${fmt(v)} kg` },
  { key: 'demand_fulfillment_pct', label: 'Orders filled after re-planning', unit: ' pp', digits: 1, show: v => `${fmt(v, 1)}%` },
]

type Spot = { dest_id: string | null; dispatch_day: number | null } // null = left unshipped by the replan (§5.13)
const destOf = (x: Spot) => x.dest_id ?? 'not shipped'
const dayOf = (x: Spot) => (x.dispatch_day === null ? '' : ` · day ${x.dispatch_day}`)
const where = (x: Spot) => `${destOf(x)}${dayOf(x)}`

function DiffView({ r }: { r: ReplanResult }) {
  const d = r.diff
  return (
    <Stack gap="lg">
          <Paper withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="sm">
              <div>
                <Title order={3}>What moved</Title>
                <Text size="sm" c="dimmed">Each card is a batch sliding from its old market to its new one. The tables list every change.</Text>
              </div>
              <Group gap="xs">
                <Badge size="lg" variant="light" color="gray" title={d.event_id}>Event at hour {d.at_h}</Badge>
                <Badge size="lg" variant="light" color="blue" leftSection={<IconSnowflake size={14} />}>
                  {d.frozen_shipments} shipments already on the road (frozen)</Badge>
                <Badge size="lg" variant="light" color="grape">Re-planned in {d.solve_seconds} s</Badge>
              </Group>
            </Group>
            <Flights key={d.event_id} diff={d} />
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mt="lg">
              <div>
                <Text fw={700} mb={4}>Batches sent to a different market ({d.moved_batches.length})</Text>
                <Table striped fz="sm" className="num">
                  <Table.Thead><Table.Tr><Table.Th>Batch</Table.Th><Table.Th>Was going to</Table.Th><Table.Th /><Table.Th>Now going to</Table.Th>
                    <Table.Th ta="right">kg</Table.Th></Table.Tr></Table.Thead>
                  <Table.Tbody>
                    {d.moved_batches.map(b => (
                      <Table.Tr key={b.batch_id}><Table.Td fw={600}>{b.batch_id}</Table.Td>
                        <Table.Td>{where(b.from)}</Table.Td><Table.Td><IconArrowRight size={14} /></Table.Td>
                        <Table.Td>{where(b.to)}</Table.Td><Table.Td ta="right">{fmt(b.kg, 1)}</Table.Td></Table.Tr>))}
                  </Table.Tbody>
                </Table>
                {!d.moved_batches.length && <Text c="dimmed" size="sm">Every batch still goes to the same market.</Text>}
              </div>
              <div>
                <Text fw={700} mb={4}>Price changes ({d.discount_changes.length})</Text>
                <Table striped fz="sm" className="num">
                  <Table.Thead><Table.Tr><Table.Th>Stock lot</Table.Th><Table.Th ta="right">Day</Table.Th>
                    <Table.Th ta="right">Old discount</Table.Th><Table.Th /><Table.Th>New discount</Table.Th></Table.Tr></Table.Thead>
                  <Table.Tbody>
                    {d.discount_changes.map(c => (
                      <Table.Tr key={`${c.lot_id}-${c.day}`}><Table.Td>{c.lot_id}</Table.Td><Table.Td ta="right">{c.day}</Table.Td>
                        <Table.Td ta="right">{c.from_pct}%</Table.Td><Table.Td><IconArrowRight size={14} /></Table.Td>
                        <Table.Td fw={700}>{c.to_pct}%</Table.Td></Table.Tr>))}
                  </Table.Tbody>
                </Table>
                {!d.discount_changes.length && <Text c="dimmed" size="sm">No discount changed.</Text>}
              </div>
            </SimpleGrid>
          </Paper>
          <Stack gap="md">
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
              {KPI_TILES.map(t => {
                const now = d.kpis_replanned[t.key], dk = d.delta_kpis[t.key], old = d.kpis_old_plan_under_event[t.key]
                if (now == null) return null
                return <KpiTile key={t.key} label={t.label} value={t.show(now)}
                  delta={dk == null ? null : fmtSigned(dk, t.digits, t.unit)} tone={toneOf(dk ?? null, t.lowerIsBetter)}
                  sub={old == null ? undefined : `If we had kept the old plan: ${t.show(old)}`} />
              })}
            </SimpleGrid>
            <Text size="sm" c="dimmed" mt={0}>Coloured badges = re-planned result minus keeping the old plan after the event.</Text>
            <Blockquote color="green" icon={<IconMessage2 size={22} />} radius="lg" p="lg">
              <Text fz="lg">{r.narration}</Text>
            </Blockquote>
          </Stack>
    </Stack>
  )
}

/** Each moved batch is a chip that flies from its old destination column to its new one (shared layoutId). */
function Flights({ diff }: { diff: Diff }) {
  const [landed, setLanded] = useState(false)
  useEffect(() => { // take off shortly after mount; Replay re-runs the flight
    if (landed) return
    const t = setTimeout(() => setLanded(true), 600)
    return () => clearTimeout(t)
  }, [landed])
  const dests = [...new Set(diff.moved_batches.flatMap(b => [destOf(b.from), destOf(b.to)]))].sort()
  if (!dests.length) return null
  return (
    <>
      <LayoutGroup id={`flights-${diff.event_id}`}>
        <div className="flight-board">
          {dests.map(dest => (
            <div key={dest} className="flight-col">
              <Group gap={6} mb={8}><IconTruck size={16} /><Text fw={700}>{dest}</Text></Group>
              {diff.moved_batches.filter(b => destOf(landed ? b.to : b.from) === dest).map(b => (
                <m.div key={b.batch_id} layoutId={`flight-${b.batch_id}`} transition={spring.bouncy}
                  className="flight-chip" data-landed={landed || undefined}>
                  <Text fw={700} size="sm">{b.batch_id}</Text>
                  <Text size="xs" c="dimmed">{fmt(b.kg, 1)} kg{dayOf(landed ? b.to : b.from)}</Text>
                </m.div>
              ))}
            </div>
          ))}
        </div>
      </LayoutGroup>
      <Group justify="space-between" mt="xs">
        <Text size="xs" c="dimmed">{landed ? 'Now: where each batch goes after re-planning' : 'Before: where each batch was going'}</Text>
        <Button size="compact-sm" variant="subtle" onClick={() => setLanded(false)} disabled={!landed}>Replay the move</Button>
      </Group>
    </>
  )
}
