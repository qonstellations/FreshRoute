// Shelf-life route board (ARCHITECTURE §16): hubs on the left, markets on the right, a lane per served route.
// Colours pick the smallest served slack_h per destination; routes are the served trips' origin → dest_id pairs.
// Layout only: geography is dropped on purpose (a 500 km market beside a 5 km one made the old map unreadable).
import { Button, ColorSwatch, Group, Paper, Skeleton, Stack, Table, Text, Title, Tooltip } from '@mantine/core'
import { m, type Variants } from 'motion/react'
import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { DispatchRow, GeoRecord } from '../../types'
import { Explain } from '../Explain'
import { band, BANDS, HUB, num } from './format'
import './plan.css'

const W = 1000, PAD = 24, ROW = 62, HUB_X = 30, HUB_W = 250, HUB_H = 76, DEST_X = 600, DEST_W = 370

const draw: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.09, delayChildren: 0.15 } } }
const stroke: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  show: { pathLength: 1, opacity: 1, transition: { pathLength: { duration: 0.9, ease: 'easeOut' }, opacity: { duration: 0.1 } } },
}

// Cubic S-curve between the two columns.
function curve([x1, y1]: number[], [x2, y2]: number[]) {
  const mx = (x1 + x2) / 2
  return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`
}

const trunc = (t: string, n: number) => (t.length > n ? `${t.slice(0, n - 1)}…` : t)

// `onRoute` makes each route clickable (Replan: close that road). `after` = a replan's event hour and the origin → dest
// pairs of its trips leaving after it; against this run's trips leaving after that hour, dropped routes are drawn as
// cut and added ones as new (trips already on the road stay as they were).
export function ShelfLifeMap({ scenario, runId, rows, filter, onPick, onRoute, after }: {
  scenario: string; runId: string; rows: DispatchRow[]
  filter?: string; onPick: (destId: string | undefined) => void
  onRoute?: (origin: string, dest: string) => void; after?: { at_h: number; routes: [string, string][] }
}) {
  const [geo, setGeo] = useState<GeoRecord[] | null | undefined>(undefined)
  const [routes, setRoutes] = useState<[string, string][]>([])
  const [late, setLate] = useState<{ h: number; key: string }[]>([]) // trips' dispatch hour per route, for `after`
  const [hover, setHover] = useState<string | undefined>(undefined)
  useEffect(() => {
    setGeo(undefined)
    api.geo(scenario).then(setGeo).catch(() => setGeo(null)) // 404 = no geo.csv → colour table
  }, [scenario])
  useEffect(() => {
    setRoutes([])
    api.table(runId, 'trips').then(t => {
      const seen = new Set(t.records.map(r => `${r.origin}|${r.dest_id}`))
      setRoutes([...seen].sort().map(k => k.split('|') as [string, string]))
      setLate(t.records.map(r => ({ h: Number(r.dispatch_h), key: `${r.origin}|${r.dest_id}` })))
    }).catch(() => setRoutes([])) // routes are decoration; the board still works without them
  }, [runId])

  // Per destination: the smallest served slack_h among its dispatch rows (picks a value, computes none).
  const urgent = new Map<string, DispatchRow>()
  // Served kg grouped per destination (shown as a label).
  const kg = new Map<string, number>()
  for (const r of rows) {
    if (!urgent.has(r.dest_id) || r.slack_h < urgent.get(r.dest_id)!.slack_h) urgent.set(r.dest_id, r)
    kg.set(r.dest_id, (kg.get(r.dest_id) ?? 0) + r.kg)
  }
  const dests = [...urgent.values()].sort((a, b) => a.slack_h - b.slack_h)

  const legend = (
    <Group gap="md">
      {BANDS.map(([c, l]) => <Group key={l} gap={6}><ColorSwatch color={c} size={14} /><Text size="sm">{l}</Text></Group>)}
      <Group gap={6}><ColorSwatch color={HUB} size={14} radius={3} /><Text size="sm">hub (warehouse)</Text></Group>
      <Text size="sm" c="dimmed">· the pill = least <Explain term="slack">time to spare</Explain> at that market ·
        click a market to filter the list below</Text>
    </Group>
  )

  if (geo === undefined) return (
    <Paper withBorder radius="md" p="md"><Skeleton h={22} w={260} mb="sm" /><Skeleton h={420} /></Paper>
  )
  const pts = (geo ?? []).filter(g => typeof g.lat === 'number' && typeof g.lon === 'number')
  const hubs = pts.filter(g => g.node_type === 'hub')
  // Market order: served ones by urgency, then idle ones; ids break ties so the layout is stable.
  const markets = pts.filter(g => g.node_type !== 'hub').sort((a, b) => {
    const ua = urgent.get(String(a.node_id)), ub = urgent.get(String(b.node_id))
    return (ua ? ua.slack_h : Infinity) - (ub ? ub.slack_h : Infinity) || String(a.node_id).localeCompare(String(b.node_id))
  })
  const H = PAD * 2 + Math.max(markets.length * ROW, hubs.length * (HUB_H + 24))
  const dy = new Map(markets.map((g, i) => [String(g.node_id), PAD + ROW * i + ROW / 2]))
  const key = ([o, d]: [string, string]) => `${o}|${d}`
  const all = new Set(routes.map(key)), next = after && new Set(after.routes.map(key))
  const was = new Set(late.filter(t => after && t.h > after.at_h).map(t => t.key))
  const extra = (after?.routes ?? []).filter(r => !all.has(key(r)))
  const known = new Set(pts.map(g => String(g.node_id)))
  const lines = [...routes, ...extra].filter(([o, d]) => known.has(o) && dy.has(d))
  // Hubs sit at the average height of the markets they serve, then are spread so cards never overlap.
  const want = hubs.map(h => {
    const ys = lines.filter(([o]) => o === String(h.node_id)).map(([, d]) => dy.get(d)!)
    return { h, y: ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : H / 2 }
  }).sort((a, b) => a.y - b.y)
  for (let i = 1; i < want.length; i++) want[i].y = Math.max(want[i].y, want[i - 1].y + HUB_H + 16)
  const over = want.length ? want[want.length - 1].y + HUB_H / 2 + PAD - H : 0
  if (over > 0) want.forEach(w => { w.y -= over })
  const hy = new Map(want.map(w => [String(w.h.node_id), Math.max(PAD + HUB_H / 2, w.y)]))
  const at = new Map<string, number[]>([
    ...hubs.map(g => [String(g.node_id), [HUB_X + HUB_W, hy.get(String(g.node_id))!]] as [string, number[]]),
    ...markets.map(g => [String(g.node_id), [DEST_X, dy.get(String(g.node_id))!]] as [string, number[]]),
  ])
  // Short labels: "KR Market mandi, Bengaluru" -> "KR Market mandi"; hubs -> "Kolar hub". Full names stay in tooltips.
  const short = (g: GeoRecord) => g.node_type === 'hub' ? `${String(g.name).split(' ')[0]} hub` : String(g.name).split(',')[0]
  const nameOf = (id: string) => { const g = pts.find(p => String(p.node_id) === id); return g ? short(g) : id }
  // Lanes leave a hub at spread-out heights so they fan out instead of piling into one point.
  const pathOf = (o: string, d: string) => {
    const mine = lines.filter(([a]) => a === o), i = mine.findIndex(([, b]) => b === d)
    const [x, y] = at.get(o)!
    return curve([x, y + (i - (mine.length - 1) / 2) * Math.min(10, (HUB_H - 24) / mine.length)], at.get(d)!)
  }
  const fate = (r: [string, string]) =>
    !next ? '' : next.has(key(r)) ? (was.has(key(r)) ? ' kept' : ' new') : was.has(key(r)) ? ' cut' : ' kept'
  const active = hover ?? filter

  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap="sm">
        <div>
          <Title order={3}>Where every truck goes, and how much time each delivery has to spare</Title>
          <Text size="sm" c="dimmed">{pts.length
            ? 'Warehouses on the left, markets on the right, most urgent market first. Each line is a road with a truck on it.'
            : 'No map locations for this scenario, so the markets are listed in a table instead'}</Text>
        </div>
        {legend}
        {!pts.length ? (
          <Table striped fz="sm">
            <Table.Thead><Table.Tr><Table.Th>Market</Table.Th><Table.Th ta="right">Least time to spare (h)</Table.Th>
              <Table.Th>Batch</Table.Th><Table.Th>Truck</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{dests.map(d => (
              <Table.Tr key={d.dest_id}>
                <Table.Td><Group gap={8}><ColorSwatch color={band(d.slack_h)[0]} size={12} />{d.dest_name} ({d.dest_id})</Group></Table.Td>
                <Table.Td ta="right" className="n">{num(d.slack_h)}</Table.Td><Table.Td>{d.batch_id} {d.commodity}</Table.Td>
                <Table.Td>{d.vehicle_id}</Table.Td>
              </Table.Tr>))}
            </Table.Tbody>
          </Table>
        ) : (
          <svg className="plan-map" viewBox={`0 0 ${W} ${H}`} role="img"
            aria-label="Route board: warehouses linked to the markets they serve, markets coloured by their least time to spare">
            <m.g variants={draw} initial="hidden" animate="show" fill="none">
              {lines.map(([o, d]) => {
                const cls = (active ? (d === active ? ' on' : ' dim') : '') + fate([o, d]) + (onRoute ? ' clickable' : '')
                const path = pathOf(o, d)
                return (
                  <g key={`r-${o}-${d}`} className={`route${cls}`}>
                    <m.path variants={stroke} d={path} className="route-base" />
                    <path d={path} className="route-flow" />
                    {onRoute && <path d={path} className="route-hit" tabIndex={0} role="button"
                      aria-label={`Close the road from ${nameOf(o)} to ${nameOf(d)} and re-plan`}
                      onClick={() => onRoute(o, d)}
                      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onRoute(o, d))} />}
                  </g>
                )
              })}
            </m.g>

            {/* ponytail: decorative only — dots glide along each route on a loop; they are not vehicle positions. */}
            <g className="trucks">
              {lines.filter(r => fate(r) !== ' cut').map(([o, d], i) => (
                <circle key={`t-${o}-${d}`} r={3.5} className="truck">
                  <animateMotion dur={`${3.2 + (i % 4) * 0.5}s`} begin={`${1.4 + i * 0.35}s`} repeatCount="indefinite"
                    path={pathOf(o, d)} />
                </circle>
              ))}
            </g>

            {hubs.map(g => {
              const id = String(g.node_id), y = hy.get(id)!
              const n = lines.filter(([o]) => o === id).length
              return (
                <g key={id} className="node hub">
                  <rect x={HUB_X} y={y - HUB_H / 2} width={HUB_W} height={HUB_H} rx={12} className="card" />
                  <rect x={HUB_X} y={y - HUB_H / 2} width={6} height={HUB_H} rx={3} fill={HUB} />
                  <text x={HUB_X + 22} y={y - 8} className="card-title">{short(g)}</text>
                  <text x={HUB_X + 22} y={y + 10} className="card-sub">{trunc(String(g.name), 32)}</text>
                  <text x={HUB_X + 22} y={y + 27} className="card-sub">sends to {n} market{n === 1 ? '' : 's'}</text>
                </g>
              )
            })}

            {markets.map(g => {
              const id = String(g.node_id), y = dy.get(id)!, top = y - ROW / 2 + 5, h = ROW - 10
              const u = urgent.get(id)
              const colour = u ? band(u.slack_h)[0] : undefined
              const node = (
                <g className={`node dest${u ? '' : ' idle'}${active === id ? ' on' : active ? ' dim' : ''}`}
                  onMouseEnter={() => setHover(id)} onMouseLeave={() => setHover(undefined)}
                  onClick={() => u && onPick(filter === id ? undefined : id)}
                  onKeyDown={e => u && (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onPick(filter === id ? undefined : id))}
                  tabIndex={u ? 0 : undefined} role={u ? 'button' : undefined}
                  aria-label={u ? `${g.name}: least time to spare ${num(u.slack_h)} h. Show only this market in the loading list`
                    : `${g.name}: no deliveries`}>
                  <rect x={DEST_X} y={top} width={DEST_W} height={h} rx={10} className="card" />
                  {u && <rect x={DEST_X} y={top} width={6} height={h} rx={3} fill={colour} />}
                  <text x={DEST_X + 20} y={y - 3} className="card-title">{trunc(short(g), 32)}</text>
                  <text x={DEST_X + 20} y={y + 14} className="card-sub">
                    {u ? `${num(kg.get(id) ?? 0)} kg · ${u.commodity}` : 'no deliveries'}</text>
                  {u && <>
                    <rect x={DEST_X + DEST_W - 86} y={y - 13} width={72} height={26} rx={13} fill={colour} />
                    <text x={DEST_X + DEST_W - 50} y={y + 5} textAnchor="middle" className="pill-text">{num(u.slack_h)} h</text>
                  </>}
                </g>
              )
              return u ? (
                <Tooltip key={id} withArrow position="left" transitionProps={{ transition: 'pop', duration: 150 }}
                  label={<Stack gap={0}>
                    <Text size="sm" fw={700}>{u.dest_name} ({u.dest_id})</Text>
                    <Text size="xs">Least time to spare: {num(u.slack_h)} h · must arrive by hour {num(u.arrive_by_h)}</Text>
                    <Text size="xs">Batch {u.batch_id} ({u.commodity}) · {num(u.kg)} kg · truck {u.vehicle_id}, leaves {u.depart_clock}</Text>
                  </Stack>}>
                  {node}
                </Tooltip>
              ) : <g key={id}>{node}</g>
            })}
          </svg>
        )}
        {onRoute && pts.length > 0 && (
          <Group gap={6}>
            <Text size="xs" c="dimmed">Or close a road from this list:</Text>
            {lines.map(([o, d]) => (
              <Button key={`b-${o}-${d}`} size="compact-xs" radius="xl" color={fate([o, d]) === ' cut' ? 'red' : 'gray'}
                variant={fate([o, d]) === ' cut' ? 'filled' : 'default'} onClick={() => onRoute(o, d)}>
                {nameOf(o)} → {nameOf(d)}</Button>
            ))}
          </Group>
        )}
      </Stack>
    </Paper>
  )
}
