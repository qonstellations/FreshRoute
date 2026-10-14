// Replan tab (ARCHITECTURE §14.2, §16; DATABASE §5.13, §6): pick one of the 5 canned events, Apply (POST /api/replan,
// poll), then show diff.json as served: frozen count, moved batches (flying old → new destination), discount changes,
// ΔKPIs (served delta_kpis) and the server's narration. The engine re-solves; nothing here is computed.
// `step` (story mode): 0 event form · 1 apply + batches fly · 2 + ΔKPIs and narration. undefined = everything.
import {
  Alert, Badge, Blockquote, Button, Group, NumberInput, Paper, Select, SimpleGrid, Stack, Table, Text, TextInput, ThemeIcon, Title,
} from '@mantine/core'
import { IconAlertTriangle, IconArrowRight, IconBolt, IconMessage2, IconRefresh, IconSnowflake, IconTruck } from '@tabler/icons-react'
import { LayoutGroup, m, useReducedMotion } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { api, waitReplan } from '../api/client'
import { ExampleBanner } from '../components/Banners'
import { KpiTile, toneOf } from '../components/KpiTile'
import { Reveal } from '../components/score/Reveal'
import { fmt, fmtSigned } from '../lib/delta'
import type { TabProps } from '../lib/story'
import { spring } from '../theme'
import type { Diff, EventType, ReplanEvent, ReplanKpis, ReplanResult } from '../types'

// The 5 canned events of DATABASE §6; magnitudes are the documented demo defaults (editable inputs, not coefficients).
type Ids = { dest: string; commodity: string; vehicle: string }
const CANNED: Record<EventType, { label: string; note: string; magnitude: number; unit: string; target: (i: Ids) => string }> = {
  route_delay: { label: 'NH-48 jam: route delay', note: 'NH-48 jam', magnitude: 6, unit: '+h',
    target: i => `*|${i.dest}|*` },
  capacity_drop: { label: 'Reefer breakdown: capacity drop', note: 'reefer breakdown', magnitude: 0.5, unit: 'lost, 0–1',
    target: i => `vehicle:${i.vehicle}` },
  demand_spike: { label: 'Demand spike', note: 'festival demand', magnitude: 1.5, unit: '× demand',
    target: i => `dest:${i.dest}|${i.commodity}` },
  new_order: { label: 'New order', note: 'walk-in bulk order', magnitude: 300, unit: '+kg',
    target: i => `dest:${i.dest}|${i.commodity}` },
  price_shock: { label: 'Price shock', note: 'mandi glut', magnitude: 0.8, unit: '× price',
    target: i => `dest:${i.dest}|*` },
}
const TYPES = Object.keys(CANNED) as EventType[]
const AT_H = 8 // DATABASE §6 example event time

type Form = Omit<ReplanEvent, 'event_id'>
const formFor = (type: EventType, ids: Ids): Form =>
  ({ type, target: CANNED[type].target(ids), magnitude: CANNED[type].magnitude, at_h: AT_H, note: CANNED[type].note })

export function Replan({ run, runId, step }: TabProps) {
  const at = (s: number) => step == null || step >= s
  const [ids, setIds] = useState<Ids>({
    dest: run.per_destination[0]?.dest_id ?? '*', commodity: run.per_commodity[0]?.commodity ?? '*', vehicle: '',
  })
  const [form, setForm] = useState<Form>(() => formFor('route_delay', ids))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ReplanResult | null>(null)
  const started = useRef(false)

  // a vehicle id for the reefer-breakdown default, from the run's own dispatch sheet
  useEffect(() => {
    started.current = false; setResult(null); setError('')
    api.dispatchSheet(runId).then(s => {
      const v = s?.csv[0]?.vehicle_id
      if (v) setIds(i => ({ ...i, vehicle: v }))
    }).catch(() => { /* optional: the vehicle target stays editable */ })
  }, [runId])
  useEffect(() => { if (form.type === 'capacity_drop' && ids.vehicle) setForm(f => ({ ...f, target: CANNED.capacity_drop.target(ids) })) },
    [ids])

  async function apply() {
    if (busy) return
    started.current = true
    setBusy(true); setError('')
    // ponytail: time-based id, unique per click; the engine keys replan/<event_id>/ by it
    const event: ReplanEvent = { ...form, event_id: `E-${Date.now().toString(36).toUpperCase()}` }
    try {
      const r = await api.postReplan({ run_id: runId, event })
      setResult(await waitReplan(r.run_id, r.event_id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }
  // story beat 1 presses Apply once if nothing is on screen yet
  useEffect(() => { if (step != null && step >= 1 && !started.current) apply() }, [step])

  const meta = CANNED[form.type]
  return (
    <Stack gap="lg">
      <ExampleBanner show={!!result?.example} what="replan" />
      <Paper withBorder radius="lg" p="lg">
        <Group gap="md" mb="md" wrap="nowrap">
          <ThemeIcon size={44} radius="md" variant="light"><IconBolt size={26} /></ThemeIcon>
          <div>
            <Title order={3}>Something changed mid-day</Title>
            <Text size="sm" c="dimmed">Shipments dispatched at or before the event hour are frozen; HiGHS re-solves the rest.</Text>
          </div>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }} spacing="sm">
          <Select label="Event" value={form.type} allowDeselect={false} data={TYPES.map(t => ({ value: t, label: CANNED[t].label }))}
            onChange={v => v && setForm(formFor(v as EventType, ids))} style={{ gridColumn: 'span 2' }} />
          <TextInput label="Target" value={form.target} onChange={e => setForm({ ...form, target: e.currentTarget.value })} />
          <NumberInput label={`Magnitude (${meta.unit})`} value={form.magnitude} min={0} decimalScale={2}
            onChange={v => setForm({ ...form, magnitude: Number(v) })} />
          <NumberInput label="At hour" value={form.at_h} min={0} decimalScale={1}
            onChange={v => setForm({ ...form, at_h: Number(v) })} />
        </SimpleGrid>
        <Group mt="md" justify="space-between" align="flex-end">
          <TextInput label="Note (not used by the solver)" value={form.note ?? ''} w={320}
            onChange={e => setForm({ ...form, note: e.currentTarget.value })} />
          <Button size="md" radius="xl" leftSection={<IconRefresh size={18} />} loading={busy} onClick={apply}
            disabled={!form.target.trim()}>Apply and replan</Button>
        </Group>
      </Paper>
      {error && <Alert color="red" icon={<IconAlertTriangle />} title="Replan failed">{error}</Alert>}
      {result && <DiffView r={result} step={step} at={at} />}
    </Stack>
  )
}

const KPI_TILES: { key: keyof ReplanKpis; label: string; unit: string; digits: number; lowerIsBetter?: boolean
  show: (v: number) => string }[] = [
  { key: 'net_inr', label: 'Net (replanned)', unit: ' ₹', digits: 0, show: v => `₹${fmt(v)}` },
  { key: 'spoilage_kg', label: 'Spoilage (replanned)', unit: ' kg', digits: 0, lowerIsBetter: true, show: v => `${fmt(v)} kg` },
  { key: 'demand_fulfillment_pct', label: 'Fulfilment (replanned)', unit: ' pp', digits: 1, show: v => `${fmt(v, 1)}%` },
]

type Spot = { dest_id: string | null; dispatch_day: number | null } // null = left unshipped by the replan (§5.13)
const destOf = (x: Spot) => x.dest_id ?? 'unshipped'
const dayOf = (x: Spot) => (x.dispatch_day === null ? '' : ` · day ${x.dispatch_day}`)
const where = (x: Spot) => `${destOf(x)}${dayOf(x)}`

function DiffView({ r, step, at }: { r: ReplanResult; step?: number; at: (s: number) => boolean }) {
  const d = r.diff
  const kpiRef = useRef<HTMLDivElement>(null), flightRef = useRef<HTMLDivElement>(null)
  const reduce = useReducedMotion()
  useEffect(() => {
    if (step == null || step < 1) return
    const t = setTimeout(() => (step >= 2 ? kpiRef : flightRef).current?.scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' }), 250)
    return () => clearTimeout(t)
  }, [step, reduce])
  return (
    <Stack gap="lg">
      <div ref={flightRef} className="story-anchor">
        <Reveal show={at(1)} collapse={step != null}>
          <Paper withBorder radius="lg" p="lg">
            <Group justify="space-between" mb="sm">
              <Title order={3}>What moved</Title>
              <Group gap="xs">
                <Badge size="lg" variant="light" color="gray">{d.event_id} at hour {d.at_h}</Badge>
                <Badge size="lg" variant="light" color="blue" leftSection={<IconSnowflake size={14} />}>
                  {d.frozen_shipments} shipments frozen</Badge>
                <Badge size="lg" variant="light" color="grape">re-solved in {d.solve_seconds} s</Badge>
              </Group>
            </Group>
            <Flights key={d.event_id} diff={d} />
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mt="lg">
              <div>
                <Text fw={700} mb={4}>Moved batches ({d.moved_batches.length})</Text>
                <Table striped fz="sm" className="num">
                  <Table.Thead><Table.Tr><Table.Th>batch</Table.Th><Table.Th>from</Table.Th><Table.Th /><Table.Th>to</Table.Th>
                    <Table.Th ta="right">kg</Table.Th></Table.Tr></Table.Thead>
                  <Table.Tbody>
                    {d.moved_batches.map(b => (
                      <Table.Tr key={b.batch_id}><Table.Td fw={600}>{b.batch_id}</Table.Td>
                        <Table.Td>{where(b.from)}</Table.Td><Table.Td><IconArrowRight size={14} /></Table.Td>
                        <Table.Td>{where(b.to)}</Table.Td><Table.Td ta="right">{fmt(b.kg, 1)}</Table.Td></Table.Tr>))}
                  </Table.Tbody>
                </Table>
                {!d.moved_batches.length && <Text c="dimmed" size="sm">Every batch kept its destination.</Text>}
              </div>
              <div>
                <Text fw={700} mb={4}>Discount changes ({d.discount_changes.length})</Text>
                <Table striped fz="sm" className="num">
                  <Table.Thead><Table.Tr><Table.Th>lot</Table.Th><Table.Th ta="right">day</Table.Th>
                    <Table.Th ta="right">from</Table.Th><Table.Th /><Table.Th>to</Table.Th></Table.Tr></Table.Thead>
                  <Table.Tbody>
                    {d.discount_changes.map(c => (
                      <Table.Tr key={`${c.lot_id}-${c.day}`}><Table.Td>{c.lot_id}</Table.Td><Table.Td ta="right">{c.day}</Table.Td>
                        <Table.Td ta="right">{c.from_pct}%</Table.Td><Table.Td><IconArrowRight size={14} /></Table.Td>
                        <Table.Td fw={700}>{c.to_pct}%</Table.Td></Table.Tr>))}
                  </Table.Tbody>
                </Table>
                {!d.discount_changes.length && <Text c="dimmed" size="sm">No markdown changed.</Text>}
              </div>
            </SimpleGrid>
          </Paper>
        </Reveal>
      </div>
      <div ref={kpiRef} className="story-anchor">
        <Reveal show={at(2)} collapse={step != null}>
          <Stack gap="md">
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
              {KPI_TILES.map(t => {
                const now = d.kpis_replanned[t.key], dk = d.delta_kpis[t.key], old = d.kpis_old_plan_under_event[t.key]
                if (now == null) return null
                return <KpiTile key={t.key} label={t.label} value={t.show(now)}
                  delta={dk == null ? null : fmtSigned(dk, t.digits, t.unit)} tone={toneOf(dk ?? null, t.lowerIsBetter)}
                  sub={old == null ? undefined : `old plan under the event: ${t.show(old)}`} />
              })}
            </SimpleGrid>
            <Text size="sm" c="dimmed" mt={0}>Badges: replanned minus the old plan executed in the changed world (diff.json delta_kpis).</Text>
            <Blockquote color="green" icon={<IconMessage2 size={22} />} radius="lg" p="lg">
              <Text fz="lg">{r.narration}</Text>
            </Blockquote>
          </Stack>
        </Reveal>
      </div>
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
        <Text size="xs" c="dimmed">{landed ? 'new destinations (replanned)' : 'old destinations (before the event)'}</Text>
        <Button size="compact-sm" variant="subtle" onClick={() => setLanded(false)} disabled={!landed}>Replay</Button>
      </Group>
    </>
  )
}
