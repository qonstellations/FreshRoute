// Shelf-life countdown map (ARCHITECTURE §16): offline react-leaflet (no tiles) or a colour table without geo.csv.
// Colours pick the smallest served slack_h per destination; routes are the served trips' origin → dest_id pairs.
import 'leaflet/dist/leaflet.css'
import type { CircleMarker as LCircleMarker, LatLngTuple } from 'leaflet'
import { Badge, ColorSwatch, Group, Paper, Skeleton, Stack, Table, Text, Title } from '@mantine/core'
import { useEffect, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, Tooltip, useMap } from 'react-leaflet'
import { api } from '../../api/client'
import type { DispatchRow, GeoRecord } from '../../types'
import { band, BANDS, HUB, num } from './format'

// ponytail: decorative only — trucks glide origin → destination on a loop, they are not vehicle positions.
// Pixel offsets are recomputed on zoom so the CSS transform stays on the line.
function Truck({ a, b, i }: { a: LatLngTuple; b: LatLngTuple; i: number }) {
  const map = useMap()
  const ref = useRef<LCircleMarker>(null)
  useEffect(() => {
    const place = () => {
      const el = ref.current?.getElement() as SVGElement | undefined
      if (!el) return
      const p = map.latLngToLayerPoint(a), q = map.latLngToLayerPoint(b)
      el.style.setProperty('--dx', `${q.x - p.x}px`)
      el.style.setProperty('--dy', `${q.y - p.y}px`)
      el.style.animationDelay = `${1.2 + i * 0.45}s`
    }
    place()
    map.on('zoomend', place)
    return () => { map.off('zoomend', place) }
  }, [map, a, b, i])
  return <CircleMarker ref={ref} center={a} radius={4} interactive={false}
    pathOptions={{ className: 'truck', color: '#1d2430', weight: 2, fillColor: '#fff', fillOpacity: 1 }} />
}

const pulse = (h: number) => (h < 6 ? 'fast' : h < 24 ? 'mid' : 'slow')

export function ShelfLifeMap({ scenario, runId, rows }: { scenario: string; runId: string; rows: DispatchRow[] }) {
  const [geo, setGeo] = useState<GeoRecord[] | null | undefined>(undefined)
  const [routes, setRoutes] = useState<[string, string][]>([])
  useEffect(() => {
    setGeo(undefined)
    api.geo(scenario).then(setGeo).catch(() => setGeo(null)) // 404 = no geo.csv → colour table
  }, [scenario])
  useEffect(() => {
    setRoutes([])
    api.table(runId, 'trips').then(t => {
      const seen = new Set(t.records.map(r => `${r.origin}|${r.dest_id}`))
      setRoutes([...seen].sort().map(k => k.split('|') as [string, string]))
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
    <Stack gap={6}>
      <Group gap="md">
        {BANDS.map(([c, l]) => <Group key={l} gap={6}><ColorSwatch color={c} size={14} /><Text size="sm">{l}</Text></Group>)}
        <Group gap={6}><ColorSwatch color={HUB} size={14} /><Text size="sm">hub</Text></Group>
        <Text size="sm" c="dimmed">· marker size ∝ kg shipped</Text>
      </Group>
      <Group gap={6}>
        <Text size="sm" c="dimmed" mr={4}>Tightest slack per destination:</Text>
        {dests.map(d => (
          <Badge key={d.dest_id} variant="outline" color="gray" radius="sm" size="lg" tt="none" fw={500}
            leftSection={<ColorSwatch color={band(d.slack_h)[0]} size={10} />}>
            {d.dest_id} <b>{num(d.slack_h)} h</b>
          </Badge>))}
      </Group>
    </Stack>
  )

  if (geo === undefined) return (
    <Paper withBorder radius="md" p="md"><Skeleton h={22} w={260} mb="sm" /><Skeleton h={380} /></Paper>
  )
  const pts = (geo ?? []).filter(g => typeof g.lat === 'number' && typeof g.lon === 'number')
  const at = new Map(pts.map(g => [String(g.node_id), [g.lat, g.lon] as LatLngTuple]))
  const lines = routes.filter(([o, d]) => at.has(o) && at.has(d))

  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap="sm">
        <div>
          <Title order={3}>Shelf-life countdown</Title>
          <Text size="sm" c="dimmed">{pts.length ? 'Offline, no map tiles · routes from served trips' : 'No geo.csv for this scenario, table view'}</Text>
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
          <MapContainer className="plan-map" bounds={pts.map(g => [g.lat, g.lon] as LatLngTuple)}
            boundsOptions={{ padding: [50, 50] }} attributionControl={false} scrollWheelZoom={false}>
            {lines.map(([o, d]) => (
              <Polyline key={`r-${o}-${d}`} positions={[at.get(o)!, at.get(d)!]} interactive={false}
                pathOptions={{ className: 'route', color: '#7d8797', weight: 2.5, opacity: 0.75 }} />
            ))}
            {lines.map(([o, d], i) => <Truck key={`t-${o}-${d}`} a={at.get(o)!} b={at.get(d)!} i={i} />)}
            {pts.map(g => {
              const id = String(g.node_id)
              const hub = g.node_type === 'hub'
              const u = urgent.get(id)
              const colour = hub ? HUB : u ? band(u.slack_h)[0] : '#b8c0cc'
              const r = hub ? 8 : 8 + 10 * Math.sqrt((kg.get(id) ?? 0) / maxKg)
              const pos = [g.lat, g.lon] as LatLngTuple
              return [
                !hub && u && <CircleMarker key={`h-${id}`} center={pos} radius={r} interactive={false}
                  pathOptions={{ className: `halo halo-${pulse(u.slack_h)}`, color: colour, weight: 3, fill: false }} />,
                <CircleMarker key={`m-${id}`} center={pos} radius={r}
                  pathOptions={{ color: '#fff', weight: 2, fillColor: colour, fillOpacity: 0.95 }}>
                  <Tooltip permanent direction={hub ? 'left' : 'right'} offset={[hub ? -10 : r + 2, 0]} className="plan-tip">
                    <b>{g.name}</b>{hub ? ' (hub)' : u ? ` · ${num(u.slack_h)} h` : ' · no load'}
                  </Tooltip>
                </CircleMarker>,
              ]
            })}
          </MapContainer>
        )}
      </Stack>
    </Paper>
  )
}
