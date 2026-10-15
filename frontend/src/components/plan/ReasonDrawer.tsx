// Reason-card drawer (ARCHITECTURE §15, DATABASE §5.9): spring slide-in, focus trap, Esc/backdrop close.
// Every number is a served reason_cards.json field; deltas are served (chosen − alternative), only coloured here.
import { Badge, Card, CloseButton, FocusTrap, Group, Paper, Portal, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core'
import { useFocusReturn, useHotkeys } from '@mantine/hooks'
import { IconFileUnknown } from '@tabler/icons-react'
import { AnimatePresence, m, type Variants } from 'motion/react'
import type { ReactNode } from 'react'
import { spring } from '../../theme'
import type { ReasonCard } from '../../types'
import { Fuse } from './Fuse'
import { band, cappedText, num, REASON_COLOUR, signed } from './format'
import { modeName, placeName, reasonText, type Names } from '../../lib/words'
import { Explain } from '../Explain'

/** What the drawer shows: the card (null = none found) and the element it morphs out of. */
export interface DrawerOpen { card: ReasonCard | null; layoutId: string; from: 'row' | 'card' }

const list: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.12 } } }
const item: Variants = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: spring.soft } }

const deltaColour = (v: number) => (v > 0 ? 'teal.7' : v < 0 ? 'red.7' : 'dimmed')

function Kv({ k, v }: { k: ReactNode; v: ReactNode }) {
  return <div><Text size="xs" c="dimmed" tt="uppercase" fw={600}>{k}</Text><Text fw={500}>{v}</Text></div>
}

function Body({ open, names }: { open: DrawerOpen; names?: Names }) {
  const place = (id: string) => placeName(names, id)
  const { card } = open
  const c = card?.chosen
  const rankBadge = (rank: number | string) => (
    <m.span layoutId={open.from === 'row' ? open.layoutId : undefined} style={{ display: 'inline-block' }}>
      <Badge size="lg" radius="sm" variant="filled" color="green">#{rank}</Badge>
    </m.span>
  )
  if (!card || !c) return (
    <Stack align="center" gap="xs" py="xl" c="dimmed">
      {open.from === 'row' && rankBadge(open.layoutId.replace('rank-', ''))}
      <IconFileUnknown size={40} stroke={1.4} />
      <Text c="dimmed">No explanation was saved for this shipment.</Text>
    </Stack>
  )
  return (
    <m.div variants={list} initial="hidden" animate="show">
      <Stack gap="md">
        <m.div layoutId={open.from === 'card' ? open.layoutId : undefined} transition={spring.soft}>
          <Paper p="md" radius="md" bg={card.discount ? 'var(--mantine-color-yellow-light)' : 'var(--mantine-color-default-hover)'} withBorder>
            <Group gap="sm" wrap="nowrap" align="center">
              {rankBadge(card.priority.rank)}
              <div style={{ minWidth: 0 }}>
                <Title order={3} lh={1.2}>{card.batch_id} {card.commodity}</Title>
                <Text size="sm" c="dimmed">Batch {card.batch_id} ({card.commodity}) → {place(c.dest_id)} by {modeName(c.mode)} {c.vehicle_id}</Text>
              </div>
            </Group>
          </Paper>
        </m.div>

        <m.div variants={item}>
          <Paper p="sm" radius="md" bg="var(--mantine-color-blue-light)"><Text size="sm">{card.text.replace(/\b[A-Z]+\d+\b/g, place)}</Text></Paper>
        </m.div>

        <m.div variants={item}>
          <SimpleGrid cols={2} spacing="sm">
            <Card withBorder radius="md" padding="sm">
              <Group justify="space-between" mb={6}>
                <Text fw={700}>FreshRoute's choice</Text><Badge color="green" variant="light" tt="none">{place(c.dest_id)}</Badge>
              </Group>
              <Stack gap={6}>
                <Kv k="Leaves → arrives (hour)" v={`${num(c.dispatch_h)} h → ${num(c.arrival_h)} h`} />
                <Kv k="Load" v={`${num(c.kg)} kg`} />
                <Kv k={<Explain term="shelfLife">Shelf life left on arrival</Explain>} v={`${num(c.usable_life_at_arrival_h)} h`} />
                <Kv k={<Explain term="slack">Time to spare</Explain>} v={<Group gap={8} component="span">
                  <Badge color={band(c.slack_h)[2]} variant="light" tt="none">{num(c.slack_h)} h</Badge>
                  <Fuse slackH={c.slack_h} delay={0.35} width={80} /></Group>} />
                <Kv k="Profit per kg" v={`₹${num(c.margin_inr_kg)}/kg`} />
              </Stack>
            </Card>
            <Card withBorder radius="md" padding="sm">
              <Group justify="space-between" mb={6}>
                <Text fw={700}>Next-best option</Text>
                {card.runner_up && <Badge color="gray" variant="light" tt="none">{place(card.runner_up.dest_id)}</Badge>}
              </Group>
              {card.runner_up ? <Stack gap={6}>
                <Kv k="Why not chosen" v={<Badge color={REASON_COLOUR[card.runner_up.reason_code]} variant="light" tt="none">
                  {reasonText(card.runner_up.reason_code)}</Badge>} />
                <Kv k="Extra profit per kg with our choice" v={<Text span fw={700} c={deltaColour(card.runner_up.margin_delta_inr_kg)}>
                  ₹{signed(card.runner_up.margin_delta_inr_kg)}/kg</Text>} />
                <Kv k="Extra profit on this load" v={<Text span fw={700} c={deltaColour(card.runner_up.margin_delta_inr)}>
                  ₹{signed(card.runner_up.margin_delta_inr)}</Text>} />
                <Kv k="Extra time to spare" v={`${signed(card.runner_up.slack_delta_h)} h`} />
              </Stack> : <Text c="dimmed" size="sm">There was no other workable option.</Text>}
            </Card>
          </SimpleGrid>
        </m.div>

        {card.discount && <m.div variants={item}>
          <Paper withBorder radius="md" p="sm" bg="var(--mantine-color-yellow-light)">
            <Group justify="space-between">
              <Text fw={700} size="lg"><Explain term="markdown">{num(card.discount.tier_pct)} % off</Explain></Text>
              <Text size="sm">from day {card.discount.day}</Text>
            </Group>
            <Text size="sm" c="dimmed">Risk of not selling: {card.discount.risk.toFixed(2)}
              {card.discount.capped_by !== 'none' && ` · ${cappedText(card.discount.capped_by)}`}</Text>
          </Paper>
        </m.div>}

        <m.div variants={item}>
          <Group gap={6} mb={4}><Text fw={700}>Other options FreshRoute considered</Text>
            <Text size="sm" c="dimmed">Positive numbers = our choice is better by that much</Text></Group>
          <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
            <Table fz="sm" verticalSpacing={4} striped>
              <Table.Thead><Table.Tr>
                <Table.Th>Market</Table.Th><Table.Th>Transport</Table.Th><Table.Th ta="right">Day</Table.Th><Table.Th>Why not chosen</Table.Th>
                <Table.Th ta="right">Time to spare h</Table.Th><Table.Th ta="right">Extra ₹/kg for our choice</Table.Th>
                <Table.Th ta="right">Extra hours for our choice</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>{card.alternatives.map(a => (
                <Table.Tr key={`${a.dest_id}|${a.mode}|${a.dispatch_day}`} c={a.feasible ? undefined : 'dimmed'}
                  title={a.feasible ? undefined : `Not possible: ${a.reject_reason || reasonText(a.reason_code)}`}>
                  <Table.Td>{place(a.dest_id)}</Table.Td><Table.Td>{modeName(a.mode)}</Table.Td><Table.Td ta="right">{a.dispatch_day}</Table.Td>
                  <Table.Td><Badge size="sm" variant={a.feasible ? 'light' : 'outline'} color={REASON_COLOUR[a.reason_code]} tt="none">
                    {reasonText(a.reason_code)}</Badge></Table.Td>
                  <Table.Td ta="right" className="n">{num(a.slack_h)}</Table.Td>
                  <Table.Td ta="right" className="n" c={deltaColour(a.margin_delta_inr_kg)}>{signed(a.margin_delta_inr_kg)}</Table.Td>
                  <Table.Td ta="right" className="n">{signed(a.slack_delta_h)}</Table.Td>
                </Table.Tr>))}
              </Table.Tbody>
            </Table>
          </Paper>
        </m.div>
      </Stack>
    </m.div>
  )
}

export function ReasonDrawer({ open, onClose, names }: { open: DrawerOpen | undefined; onClose: () => void; names?: Names }) {
  useHotkeys([['Escape', onClose]], [])
  useFocusReturn({ opened: !!open })
  return (
    <AnimatePresence>
      {open && <Portal key="reason-drawer">
        <m.div className="drawer-backdrop" onClick={onClose}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} />
        <FocusTrap active>
          <m.aside className="reason-drawer plan" role="dialog" aria-modal="true" aria-label="Why this shipment?" tabIndex={-1}
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={spring.soft}>
            <Group justify="space-between" mb="sm">
              <Text fw={700} c="dimmed" tt="uppercase" size="sm">Why this shipment?</Text>
              <CloseButton size="lg" onClick={onClose} aria-label="Close explanation" />
            </Group>
            <Body open={open} names={names} />
          </m.aside>
        </FocusTrap>
      </Portal>}
    </AnimatePresence>
  )
}
