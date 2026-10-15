// Dispatch sheet (ARCHITECTURE §16, DATABASE §5.10): priority table, CSV download, copyable driver message.
import { Badge, Button, Code, CopyButton, Group, Paper, Pill, Stack, Table, Text, Title } from '@mantine/core'
import { IconCheck, IconCopy, IconDownload } from '@tabler/icons-react'
import { AnimatePresence, m, type HTMLMotionProps, type Variants } from 'motion/react'
import { useEffect, useState } from 'react'
import { spring } from '../../theme'
import type { DispatchRow, DispatchSheet } from '../../types'
import { TERM } from '../../lib/words'
import { Explain } from '../Explain'
import { band, FUSE_SCALE_H, num } from './format'
import { Fuse } from './Fuse'

// ponytail: only the first rows stagger/burn in; the rest render settled so 300+ rows don't queue animations
const ANIMATED_ROWS = 40

const body: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.02 } } }
const row: Variants = { hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0, transition: spring.snappy } }

// Formatting the served records back into CSV (no endpoint serves dispatch_sheet.csv as a file).
function csvUrl(rows: DispatchSheet['csv']) {
  const cols = Object.keys(rows[0] ?? {})
  const cell = (v: unknown) => {
    const s = v == null ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s
  }
  const text = [cols.join(','), ...rows.map(r => cols.map(c => cell(r[c as keyof typeof r])).join(','))].join('\n')
  return URL.createObjectURL(new Blob([text + '\n'], { type: 'text/csv' }))
}

// Mantine's Table.Tbody/Tr keep their striping/hover data attributes and render a motion element via Box's
// `component` prop (factory types are not polymorphic, hence the cast).
const MTbody = (p: HTMLMotionProps<'tbody'>) => <Table.Tbody {...({ ...p, component: m.tbody } as object)} />
const MTr = (p: HTMLMotionProps<'tr'>) => <Table.Tr {...({ ...p, component: m.tr } as object)} />

export const rowLayoutId = (r: { priority_rank: number }) => `rank-${r.priority_rank}`

export function Dispatch({ sheet, runId, onRow, filter, onClear }: {
  sheet: DispatchSheet; runId: string; onRow: (r: DispatchRow) => void
  filter?: string; onClear: () => void // filter = dest_id picked on the map; display filter only
}) {
  const rows = filter ? sheet.csv.filter(r => r.dest_id === filter) : sheet.csv
  const [href, setHref] = useState('')
  useEffect(() => {
    const u = csvUrl(sheet.csv)
    setHref(u)
    return () => URL.revokeObjectURL(u)
  }, [sheet])

  return (
    <Stack gap="sm">
      <Group justify="space-between" align="flex-end">
        <div>
          <Title order={3}>Truck loading list</Title>
          <Text size="sm" c="dimmed">{filter ? `${rows.length} of ${sheet.csv.length}` : sheet.csv.length} shipments, most urgent first ·
            click any row to see why FreshRoute chose it</Text>
        </div>
        {filter && <Pill size="lg" withRemoveButton onRemove={onClear} ml="auto"
          removeButtonProps={{ 'aria-label': 'Show all markets again' }}>Market: {rows[0]?.dest_name ?? filter}</Pill>}
        <Button component="a" href={href} download={`${runId}__dispatch_sheet.csv`} variant="light"
          leftSection={<IconDownload size={18} />}>Download as spreadsheet (CSV)</Button>
      </Group>
      <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
        <Table.ScrollContainer minWidth={900} maxHeight={460}>
          <Table stickyHeader highlightOnHover striped verticalSpacing={7} fz="md">
            <Table.Thead><Table.Tr>
              <Table.Th>Load order</Table.Th><Table.Th>Truck</Table.Th><Table.Th>Trip</Table.Th><Table.Th>Leaves at</Table.Th>
              <Table.Th>Market</Table.Th><Table.Th>Batch</Table.Th><Table.Th>Produce</Table.Th>
              <Table.Th ta="right">kg</Table.Th>
              <Table.Th><Explain note={`${TERM.slack} The bar shows it on a ${FUSE_SCALE_H} h scale: a full bar means ${FUSE_SCALE_H} h or more.`}>
                Time to spare (h)</Explain></Table.Th>
              <Table.Th ta="right">Must arrive by (hour)</Table.Th>
            </Table.Tr></Table.Thead>
            <MTbody variants={body} initial="hidden" animate="show">
              {rows.map((r, i) => {
                const lively = i < ANIMATED_ROWS
                return (
                  <MTr key={`${r.trip_id}|${r.batch_id}|${r.priority_rank}`} variants={lively ? row : undefined}
                    whileHover={{ y: -2 }} transition={spring.snappy} onClick={() => onRow(r)}
                    onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onRow(r))}
                    tabIndex={0} title="Why this shipment?" style={{ cursor: 'pointer' }}>
                    <Table.Td>
                      <m.span layoutId={rowLayoutId(r)} style={{ display: 'inline-block' }}>
                        <Badge variant="default" radius="sm" size="lg">{r.priority_rank}</Badge>
                      </m.span>
                    </Table.Td>
                    <Table.Td>{r.vehicle_id}</Table.Td><Table.Td>{r.trip_id}</Table.Td>
                    <Table.Td>{r.depart_clock}</Table.Td><Table.Td>{r.dest_name}</Table.Td>
                    <Table.Td>{r.batch_id}</Table.Td><Table.Td>{r.commodity}</Table.Td>
                    <Table.Td ta="right" className="n">{num(r.kg)}</Table.Td>
                    <Table.Td>
                      <Group gap={8} wrap="nowrap">
                        <Badge color={band(r.slack_h)[2]} variant="light" size="lg" w={76} className="n">{num(r.slack_h)}</Badge>
                        <Fuse slackH={r.slack_h} animate={lively} delay={lively ? 0.25 + i * 0.02 : 0} />
                      </Group>
                    </Table.Td>
                    <Table.Td ta="right" className="n">{num(r.arrive_by_h)}</Table.Td>
                  </MTr>
                )
              })}
            </MTbody>
          </Table>
        </Table.ScrollContainer>
      </Paper>

      <Group justify="space-between" mt="sm">
        <div>
          <Title order={4}>Message for drivers</Title>
          <Text size="sm" c="dimmed">Ready to paste into WhatsApp</Text>
        </div>
        <CopyButton value={sheet.text} timeout={1500}>
          {({ copied, copy }) => (
            <Button onClick={copy} variant={copied ? 'filled' : 'light'} color={copied ? 'teal' : undefined}
              leftSection={
                <AnimatePresence mode="popLayout" initial={false}>
                  <m.span key={copied ? 'ok' : 'copy'} style={{ display: 'inline-flex' }} transition={spring.bouncy}
                    initial={{ scale: 0, rotate: -90, opacity: 0 }} animate={{ scale: 1, rotate: 0, opacity: 1 }}
                    exit={{ scale: 0, rotate: 90, opacity: 0 }}>
                    {copied ? <IconCheck size={18} /> : <IconCopy size={18} />}
                  </m.span>
                </AnimatePresence>
              }>
              {copied ? 'Copied' : 'Copy message'}
            </Button>
          )}
        </CopyButton>
      </Group>
      <Paper withBorder radius="md" p={0} className="whatsapp">
        <Code block>{sheet.text}</Code>
      </Paper>
    </Stack>
  )
}
