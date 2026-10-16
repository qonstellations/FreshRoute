// Shelf-life route board (ARCHITECTURE §16): hubs on the left, markets on the right, a lane per served route.
// Colours pick the smallest served slack_h per destination; routes are the served trips' origin → dest_id pairs.
// Layout only: geography is dropped on purpose (a 500 km market beside a 5 km one made the old map unreadable).
import { Button, ColorSwatch, Group, Paper, Skeleton, Stack, Table, Text, Title, Tooltip } from '@mantine/core'
import { AnimatePresence, m } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client'
import { spring } from '../../theme'
import type { DispatchRow, GeoRecord } from '../../types'
import { Explain } from '../Explain'
import { band, BANDS, curve, HUB, num } from './format'
import './plan.css'

const W = 1000, PAD = 24, ROW = 62, HUB_X = 30, HUB_W = 250, HUB_H = 76, DEST_X = 600, DEST_W = 370

const trunc = (t: string, n: number) => (t.length > n ? `${t.slice(0, n - 1)}…` : t)

// `onRoute` makes each route clickable (Replan: close that road). `after` = a replan's event hour and the origin → dest
// pairs of its trips leaving after it; against this run's trips leaving after that hour, dropped routes are drawn as
// cut and added ones as new (trips already on the road stay as they were).
// `closed` = the road the user closed: drawn red with a cross whatever the replan did (trucks that left before the
// event still finish on it). `busy` = a replan is running; roads stop taking clicks.
// `rev` changes when a live solve publishes a better plan for the same run: lanes and cards then spring to the
// new layout instead of redrawing from nothing.
export function ShelfLifeMap({ scenario, runId, rev, rows, filter, onPick, onRoute, after, closed, busy }: {
  scenario: string; runId: string; rev?: number; rows: DispatchRow[]
  filter?: string; onPick: (destId: string | undefined) => void
  onRoute?: (origin: string, dest: string, name: string) => void; after?: { at_h: number; routes: [string, string][] }
  closed?: [string, string] | null; busy?: boolean
}) {
  const [geo, setGeo] = useState<GeoRecord[] | null | undefined>(undefined)
  const [routes, setRoutes] = useState<[string, string][]>([])
  const [late, setLate] = useState<{ h: number; key: string }[]>([]) // trips' dispatch hour per route, for `after`
  const [hover, setHover] = useState<string | undefined>(undefined)
  const [road, setRoad] = useState<string | undefined>(undefined) // the road under the pointer, when roads are clickable
  const [intro, setIntro] = useState(true) // first draw staggers; lanes added later draw at once
  const shown = useRef(runId)
  useEffect(() => {
    setGeo(undefined)
    api.geo(scenario).then(setGeo).catch(() => setGeo(null)) // 404 = no geo.csv → colour table
  }, [scenario])
  useEffect(() => {
    if (shown.current !== runId) { shown.current = runId; setRoutes([]); setIntro(true) }
    let stale = false
    api.table(runId, 'trips').then(t => {
      if (stale) return
      const seen = new Set(t.records.map(r => `${r.origin}|${r.dest_id}`))
      setRoutes([...seen].sort().map(k => k.split('|') as [string, string]))
      setLate(t.records.map(r => ({ h: Number(r.dispatch_h), key: `${r.origin}|${r.dest_id}` })))
    }).catch(() => !stale && setRoutes([])) // routes are decoration; the board still works without them
    return () => { stale = true }
  }, [runId, rev])
  const any = routes.length > 0
  useEffect(() => {
    if (!any) return
    const t = setTimeout(() => setIntro(false), 2500)
    return () => clearTimeout(t)
  }, [any])

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
  const shut = closed ? key(closed) : undefined
  const fate = (r: [string, string]) => key(r) === shut ? ' closed' :
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
          <div className="plan-map-scroll">
          <svg className="plan-map" viewBox={`0 0 ${W} ${H}`} role="img"
            aria-label="Route board: warehouses linked to the markets they serve, markets coloured by their least time to spare">
            <g fill="none">
              <AnimatePresence>
                {lines.map(([o, d], i) => {
                  const cls = (active ? (d === active ? ' on' : ' dim') : '') + fate([o, d])
                    + (road === `${o}|${d}` && !busy ? ' hot' : '')
                  const path = pathOf(o, d)
                  const delay = intro ? 0.15 + i * 0.09 : 0
                  return (
                    <m.g key={`r-${o}-${d}`} className={`route${cls}`} exit={{ opacity: 0, transition: { duration: 0.3 } }}>
                      <m.path className="route-base" initial={{ d: path, pathLength: 0, opacity: 0 }}
                        animate={{ d: path, pathLength: 1, opacity: 1 }}
                        transition={{ d: spring.soft, pathLength: { duration: 0.9, ease: 'easeOut', delay }, opacity: { duration: 0.1, delay } }} />
                      <m.path className="route-flow" initial={{ d: path }} animate={{ d: path }} transition={spring.soft} />
                    </m.g>
                  )
                })}
              </AnimatePresence>
            </g>

            {/* ponytail: decorative only — dots glide along each route on a loop; they are not vehicle positions. */}
            <g className="trucks">
              {lines.filter(r => ![' cut', ' closed'].includes(fate(r))).map(([o, d], i) => (
                <circle key={`t-${o}-${d}`} r={3.5} className="truck">
                  <animateMotion dur={`${3.2 + (i % 4) * 0.5}s`} begin={`${1.4 + i * 0.35}s`} repeatCount="indefinite"
                    path={pathOf(o, d)} />
                </circle>
              ))}
            </g>

            {/* Hit areas sit above the trucks in one layer, so a click always lands on the road the label names. */}
            {onRoute && <g className={`route-hits${busy ? ' busy' : ''}`}>
              {lines.map(([o, d]) => {
                const k = `${o}|${d}`
                const go = () => !busy && k !== shut && onRoute(o, d, `${nameOf(o)} → ${nameOf(d)}`)
                return <path key={`h-${k}`} d={pathOf(o, d)} className="route-hit" tabIndex={busy ? -1 : 0} role="button"
                  aria-disabled={busy || k === shut}
                  aria-label={k === shut ? `Road from ${nameOf(o)} to ${nameOf(d)} is closed`
                    : `Close the road from ${nameOf(o)} to ${nameOf(d)} and re-plan`}
                  onPointerEnter={() => setRoad(k)} onPointerLeave={() => setRoad(r => (r === k ? undefined : r))}
                  onFocus={() => setRoad(k)} onBlur={() => setRoad(undefined)}
                  onClick={go} onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), go())} />
              })}
            </g>}

            {[closed, road && !busy && road !== shut ? road.split('|') as [string, string] : undefined].map((r, i) => {
              if (!r || !at.has(r[0]) || !at.has(r[1])) return null
              // curve() is symmetric, so the midpoint of its endpoints lies on the road
              const [x1, y1] = at.get(r[0])!, [x2, y2] = at.get(r[1])!, x = (x1 + x2) / 2, y = (y1 + y2) / 2
              const label = i === 0 ? (busy ? 'closing…' : 'closed') : `close ${nameOf(r[0])} → ${nameOf(r[1])}`
              return (
                <g key={i ? 'hint' : 'shut'} className={i ? 'road-hint' : 'road-shut'} transform={`translate(${x},${y})`}>
                  {i === 0 && <path d="M-7,-7 L7,7 M7,-7 L-7,7" className="road-x" />}
                  <text y={i === 0 ? -14 : -10} textAnchor="middle" className="road-label">{label}</text>
                </g>
              )
            })}

            {hubs.map(g => {
              const id = String(g.node_id), y = hy.get(id)!
              const n = lines.filter(([o]) => o === id).length
              // cards sit at y = 0 inside a group that springs to its row when a better plan re-sorts them
              return (
                <m.g key={id} className="node hub" initial={{ y }} animate={{ y }} transition={spring.soft}>
                  <rect x={HUB_X} y={-HUB_H / 2} width={HUB_W} height={HUB_H} rx={12} className="card" />
                  <rect x={HUB_X} y={-HUB_H / 2} width={6} height={HUB_H} rx={3} fill={HUB} />
                  <text x={HUB_X + 22} y={-8} className="card-title">{short(g)}</text>
                  <text x={HUB_X + 22} y={10} className="card-sub">{trunc(String(g.name), 32)}</text>
                  <text x={HUB_X + 22} y={27} className="card-sub">sends to {n} market{n === 1 ? '' : 's'}</text>
                </m.g>
              )
            })}

            {markets.map(g => {
              const id = String(g.node_id), y = dy.get(id)!, top = -ROW / 2 + 5, h = ROW - 10
              const u = urgent.get(id)
              const colour = u ? band(u.slack_h)[0] : undefined
              const node = (
                <m.g className={`node dest${u ? '' : ' idle'}${active === id ? ' on' : active ? ' dim' : ''}`}
                  initial={{ y }} animate={{ y }} transition={spring.soft}
                  onMouseEnter={() => setHover(id)} onMouseLeave={() => setHover(undefined)}
                  onClick={() => u && onPick(filter === id ? undefined : id)}
                  onKeyDown={e => u && (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onPick(filter === id ? undefined : id))}
                  tabIndex={u ? 0 : undefined} role={u ? 'button' : undefined}
                  aria-label={u ? `${g.name}: least time to spare ${num(u.slack_h)} h. Show only this market in the loading list`
                    : `${g.name}: no deliveries`}>
                  <rect x={DEST_X} y={top} width={DEST_W} height={h} rx={10} className="card" />
                  {u && <rect x={DEST_X} y={top} width={6} height={h} rx={3} fill={colour} />}
                  <text x={DEST_X + 20} y={-3} className="card-title">{trunc(short(g), 32)}</text>
                  <text x={DEST_X + 20} y={14} className="card-sub">
                    {u ? `${num(kg.get(id) ?? 0)} kg · ${u.commodity}` : 'no deliveries'}</text>
                  {u && <>
                    <rect x={DEST_X + DEST_W - 86} y={-13} width={72} height={26} rx={13} fill={colour} />
                    <text x={DEST_X + DEST_W - 50} y={5} textAnchor="middle" className="pill-text">{num(u.slack_h)} h</text>
                  </>}
                </m.g>
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
          </div>
        )}
        {onRoute && pts.length > 0 && (
          <Group gap={6}>
            <Text size="xs" c="dimmed">Or close a road from this list:</Text>
            {lines.map(([o, d]) => (
              <Button key={`b-${o}-${d}`} size="compact-xs" radius="xl" color={fate([o, d]) === ' closed' ? 'red' : 'gray'}
                variant={fate([o, d]) === ' closed' ? 'filled' : 'default'} disabled={busy}
                onClick={() => fate([o, d]) !== ' closed' && onRoute(o, d, `${nameOf(o)} → ${nameOf(d)}`)}>
                {nameOf(o)} → {nameOf(d)}</Button>
            ))}
          </Group>
        )}
      </Stack>
    </Paper>
  )
}
