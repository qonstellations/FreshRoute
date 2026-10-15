// Shelf-life countdown map (ARCHITECTURE §16): offline SVG route network over geo.csv, or a colour table without it.
// Colours pick the smallest served slack_h per destination; routes are the served trips' origin → dest_id pairs.
import { Button, ColorSwatch, Group, Paper, Skeleton, Stack, Table, Text, Title, Tooltip } from '@mantine/core'
import { m, type Variants } from 'motion/react'
import { useEffect, useId, useState } from 'react'
import { api } from '../../api/client'
import type { DispatchRow, GeoRecord } from '../../types'
import { band, BANDS, HUB, num } from './format'
import './plan.css'

// Fixed viewBox; points are fitted inside it with equal x/y scale (lon squeezed by cos(lat) so shapes stay true).
const W = 1000, H = 460, PAD = 70

const draw: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.09, delayChildren: 0.15 } } }
const stroke: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  show: { pathLength: 1, opacity: 1, transition: { pathLength: { duration: 0.9, ease: 'easeOut' }, opacity: { duration: 0.1 } } },
}

const pulse = (h: number) => (h < 6 ? 'fast' : h < 24 ? 'mid' : 'slow')

// Quadratic Bézier hub → destination, bowed sideways by a fraction of its length so parallel lanes separate.
function curve([x1, y1]: number[], [x2, y2]: number[]) {
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, k = 0.18
  return `M${x1},${y1} Q${mx - (y2 - y1) * k},${my + (x2 - x1) * k} ${x2},${y2}`
}

// `onRoute` makes each route clickable (Replan: close that road). `after` = a replan's event hour and the origin → dest
// pairs of its trips leaving after it; against this run's trips leaving after that hour, dropped routes are drawn as
// cut and added ones as new (trips already on the road stay as they were).
export function ShelfLifeMap({ scenario, runId, rows, filter, onPick, onRoute, after }: {
  scenario: string; runId: string; rows: DispatchRow[]
  filter?: string; onPick: (destId: string | undefined) => void
  onRoute?: (origin: string, dest: string) => void; after?: { at_h: number; routes: [string, string][] }
}) {
  const uid = useId().replace(/:/g, '')
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
    }).catch(() => setRoutes([])) // routes are decoration; the map still works without them
  }, [runId])

  // Per destination: the smallest served slack_h among its dispatch rows (picks a value, computes none).
  const urgent = new Map<string, DispatchRow>()
  // Served kg grouped per destination, used only to size markers (never printed).
  const kg = new Map<string, number>()
  for (const r of rows) {
    if (!urgent.has(r.dest_id) || r.slack_h < urgent.get(r.dest_id)!.slack_h) urgent.set(r.dest_id, r)
    kg.set(r.dest_id, (kg.get(r.dest_id) ?? 0) + r.kg)
  }
  const dests = [...urgent.values()].sort((a, b) => a.slack_h - b.slack_h)
  const maxKg = Math.max(1, ...kg.values())

  const legend = (
    <Group gap="md">
      {BANDS.map(([c, l]) => <Group key={l} gap={6}><ColorSwatch color={c} size={14} /><Text size="sm">{l}</Text></Group>)}
      <Group gap={6}><ColorSwatch color={HUB} size={14} radius={3} /><Text size="sm">hub</Text></Group>
      <Text size="sm" c="dimmed">· circle size ∝ kg shipped · label = tightest slack h · click a destination to filter the sheet</Text>
    </Group>
  )

  if (geo === undefined) return (
    <Paper withBorder radius="md" p="md"><Skeleton h={22} w={260} mb="sm" /><Skeleton h={420} /></Paper>
  )
  const pts = (geo ?? []).filter(g => typeof g.lat === 'number' && typeof g.lon === 'number')

  // Linear projection into the viewBox (display geometry only).
  const lats = pts.map(g => g.lat as number), lons = pts.map(g => g.lon as number)
  const midLat = (Math.min(...lats) + Math.max(...lats)) / 2
  const sx = Math.cos((midLat * Math.PI) / 180)
  const spanX = Math.max((Math.max(...lons) - Math.min(...lons)) * sx, 1e-6)
  const spanY = Math.max(Math.max(...lats) - Math.min(...lats), 1e-6)
  const s = Math.min((W - 2 * PAD) / spanX, (H - 2 * PAD) / spanY)
  const ox = (W - spanX * s) / 2, oy = (H - spanY * s) / 2
  const at = new Map(pts.map(g => [String(g.node_id), [
    ox + ((g.lon as number) - Math.min(...lons)) * sx * s,
    oy + (Math.max(...lats) - (g.lat as number)) * s,
  ]]))
  const key = ([o, d]: [string, string]) => `${o}|${d}`
  const all = new Set(routes.map(key)), next = after && new Set(after.routes.map(key))
  const was = new Set(late.filter(t => after && t.h > after.at_h).map(t => t.key))
  const extra = (after?.routes ?? []).filter(r => !all.has(key(r)))
  const lines = [...routes, ...extra].filter(([o, d]) => at.has(o) && at.has(d))
  const fate = (r: [string, string]) =>
    !next ? '' : next.has(key(r)) ? (was.has(key(r)) ? ' kept' : ' new') : was.has(key(r)) ? ' cut' : ' kept'
  const active = hover ?? filter

  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap="sm">
        <div>
          <Title order={3}>Shelf-life countdown</Title>
          <Text size="sm" c="dimmed">{pts.length ? 'Offline route network · routes from served trips' : 'No geo.csv for this scenario, table view'}</Text>
        </div>
        {legend}
        {!pts.length ? (
          <Table striped fz="sm">
            <Table.Thead><Table.Tr><Table.Th>Destination</Table.Th><Table.Th ta="right">Tightest slack h</Table.Th>
              <Table.Th>Batch</Table.Th><Table.Th>Vehicle</Table.Th></Table.Tr></Table.Thead>
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
            aria-label="Route network: hubs, destinations coloured by tightest slack, served routes">
            <defs>
              <filter id={`glow-${uid}`} x="-100%" y="-100%" width="300%" height="300%">
                <feGaussianBlur stdDeviation="9" />
              </filter>
            </defs>

            <m.g variants={draw} initial="hidden" animate="show" fill="none">
              {lines.map(([o, d]) => {
                const cls = (active ? (d === active ? ' on' : ' dim') : '') + fate([o, d]) + (onRoute ? ' clickable' : '')
                const path = curve(at.get(o)!, at.get(d)!)
                return (
                  <g key={`r-${o}-${d}`} className={`route${cls}`}>
                    <m.path variants={stroke} d={path} className="route-base" />
                    <path d={path} className="route-flow" />
                    {onRoute && <path d={path} className="route-hit" tabIndex={0} role="button"
                      aria-label={`Close the road ${o} to ${d} and replan`}
                      onClick={() => onRoute(o, d)}
                      onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onRoute(o, d))} />}
                  </g>
                )
              })}
            </m.g>

            {/* ponytail: decorative only — dots glide along each route on a loop; they are not vehicle positions. */}
            <g className="trucks">
              {lines.filter(r => fate(r) !== ' cut').map(([o, d], i) => (
                <circle key={`t-${o}-${d}`} r={4.5} className="truck">
                  <animateMotion dur={`${3.2 + (i % 4) * 0.5}s`} begin={`${1.4 + i * 0.35}s`} repeatCount="indefinite"
                    path={curve(at.get(o)!, at.get(d)!)} />
                </circle>
              ))}
            </g>

            {pts.map(g => {
              const id = String(g.node_id)
              const [x, y] = at.get(id)!
              if (g.node_type === 'hub') return (
                <g key={id} className="node hub">
                  <rect x={x - 12} y={y - 12} width={24} height={24} rx={6} fill={HUB} className="node-mark" />
                  <text x={x} y={y - 20} textAnchor="middle" className="node-label">{String(g.name)} <tspan className="dim-label">hub</tspan></text>
                </g>
              )
              const u = urgent.get(id)
              const colour = u ? band(u.slack_h)[0] : undefined
              const r = 9 + 13 * Math.sqrt((kg.get(id) ?? 0) / maxKg)
              const node = (
                <g className={`node dest${u ? '' : ' idle'}${active === id ? ' on' : active ? ' dim' : ''}`}
                  onMouseEnter={() => setHover(id)} onMouseLeave={() => setHover(undefined)}
                  onClick={() => u && onPick(filter === id ? undefined : id)}
                  onKeyDown={e => u && (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onPick(filter === id ? undefined : id))}
                  tabIndex={u ? 0 : undefined} role={u ? 'button' : undefined}
                  aria-label={u ? `${g.name}: tightest slack ${num(u.slack_h)} h. Filter dispatch sheet` : `${g.name}: no load`}>
                  {u && <circle cx={x} cy={y} r={r + 6} fill={colour} filter={`url(#glow-${uid})`} className="glow" />}
                  {u && <circle cx={x} cy={y} r={r} fill="none" stroke={colour} className={`halo halo-${pulse(u.slack_h)}`} />}
                  <circle cx={x} cy={y} r={r} fill={colour} className="node-mark" />
                  <text x={x + r + 7} y={y + 5} className="node-label">
                    {String(g.name)}{u && <tspan className="slack" fill={colour}> {num(u.slack_h)} h</tspan>}
                  </text>
                </g>
              )
              return u ? (
                <Tooltip key={id} withArrow position="top" offset={r + 4} transitionProps={{ transition: 'pop', duration: 150 }}
                  label={<Stack gap={0}>
                    <Text size="sm" fw={700}>{u.dest_name} ({u.dest_id})</Text>
                    <Text size="xs">Tightest slack {num(u.slack_h)} h · arrive by {num(u.arrive_by_h)} h</Text>
                    <Text size="xs">{u.batch_id} {u.commodity} · {num(u.kg)} kg · {u.vehicle_id} {u.depart_clock}</Text>
                  </Stack>}>
                  {node}
                </Tooltip>
              ) : <g key={id}>{node}</g>
            })}
          </svg>
        )}
        {/* ponytail: far destinations squeeze the hub cluster on the map, so every road also gets a plain button */}
        {onRoute && pts.length > 0 && (
          <Group gap={6}>
            <Text size="xs" c="dimmed">Close a road:</Text>
            {lines.map(([o, d]) => (
              <Button key={`b-${o}-${d}`} size="compact-xs" radius="xl" color={fate([o, d]) === ' cut' ? 'red' : 'gray'}
                variant={fate([o, d]) === ' cut' ? 'filled' : 'default'} onClick={() => onRoute(o, d)}>
                {o} → {String(pts.find(g => String(g.node_id) === d)?.name ?? d)}</Button>
            ))}
          </Group>
        )}
      </Stack>
    </Paper>
  )
}
