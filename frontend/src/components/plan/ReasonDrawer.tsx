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
import { band, num, REASON_COLOUR, signed } from './format'

/** What the drawer shows: the card (null = none found) and the element it morphs out of. */
export interface DrawerOpen { card: ReasonCard | null; layoutId: string; from: 'row' | 'card' }

const list: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.12 } } }
const item: Variants = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: spring.soft } }

const deltaColour = (v: number) => (v > 0 ? 'teal.7' : v < 0 ? 'red.7' : 'dimmed')

function Kv({ k, v }: { k: string; v: ReactNode }) {
  return <div><Text size="xs" c="dimmed" tt="uppercase" fw={600}>{k}</Text><Text fw={500}>{v}</Text></div>
}

function Body({ open }: { open: DrawerOpen }) {
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
      <Text c="dimmed">No reason card for this shipment (run written before reason cards existed?).</Text>
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
                <Text size="sm" c="dimmed">{card.shipment_id} · to {c.dest_id} by {c.vehicle_id} ({c.mode})</Text>
              </div>
            </Group>
          </Paper>
        </m.div>

        <m.div variants={item}>
          <Paper p="sm" radius="md" bg="var(--mantine-color-blue-light)"><Text size="sm">{card.text}</Text></Paper>
        </m.div>

        <m.div variants={item}>
          <SimpleGrid cols={2} spacing="sm">
            <Card withBorder radius="md" padding="sm">
              <Group justify="space-between" mb={6}>
                <Text fw={700}>Chosen</Text><Badge color="green" variant="light">{c.dest_id}</Badge>
              </Group>
              <Stack gap={6}>
                <Kv k="Depart → arrive" v={`${num(c.dispatch_h)} h → ${num(c.arrival_h)} h`} />
                <Kv k="Load" v={`${num(c.kg)} kg`} />
                <Kv k="Life at arrival" v={`${num(c.usable_life_at_arrival_h)} h`} />
                <Kv k="Slack" v={<Group gap={8} component="span">
                  <Badge color={band(c.slack_h)[2]} variant="light" tt="none">{num(c.slack_h)} h</Badge>
                  <Fuse slackH={c.slack_h} delay={0.35} width={80} /></Group>} />
                <Kv k="Margin" v={`₹${num(c.margin_inr_kg)}/kg`} />
              </Stack>
            </Card>
            <Card withBorder radius="md" padding="sm">
              <Group justify="space-between" mb={6}>
                <Text fw={700}>Runner-up</Text>
                {card.runner_up && <Badge color="gray" variant="light">{card.runner_up.dest_id}</Badge>}
              </Group>
              {card.runner_up ? <Stack gap={6}>
                <Kv k="Why not" v={<Badge color={REASON_COLOUR[card.runner_up.reason_code]} variant="light">
                  {card.runner_up.reason_code}</Badge>} />
                <Kv k="Margin, chosen − runner-up" v={<Text span fw={700} c={deltaColour(card.runner_up.margin_delta_inr_kg)}>
                  ₹{signed(card.runner_up.margin_delta_inr_kg)}/kg</Text>} />
                <Kv k="On this load" v={<Text span fw={700} c={deltaColour(card.runner_up.margin_delta_inr)}>
                  ₹{signed(card.runner_up.margin_delta_inr)}</Text>} />
                <Kv k="Slack, chosen − runner-up" v={`${signed(card.runner_up.slack_delta_h)} h`} />
              </Stack> : <Text c="dimmed" size="sm">No alternative.</Text>}
            </Card>
          </SimpleGrid>
        </m.div>

        {card.discount && <m.div variants={item}>
          <Paper withBorder radius="md" p="sm" bg="var(--mantine-color-yellow-light)">
            <Group justify="space-between">
              <Text fw={700} size="lg">{num(card.discount.tier_pct)} % off</Text>
              <Text size="sm">from day {card.discount.day}</Text>
            </Group>
            <Text size="sm" c="dimmed">unsold-risk {card.discount.risk.toFixed(2)}
              {card.discount.capped_by !== 'none' && ` · capped by ${card.discount.capped_by}`}</Text>
          </Paper>
        </m.div>}

        <m.div variants={item}>
          <Group gap={6} mb={4}><Text fw={700}>Alternatives</Text>
            <Text size="sm" c="dimmed">deltas = chosen − alternative</Text></Group>
          <Paper withBorder radius="md" style={{ overflow: 'hidden' }}>
            <Table fz="sm" verticalSpacing={4} striped>
              <Table.Thead><Table.Tr>
                <Table.Th>Dest</Table.Th><Table.Th>Mode</Table.Th><Table.Th ta="right">Day</Table.Th><Table.Th>Reason</Table.Th>
                <Table.Th ta="right">Slack h</Table.Th><Table.Th ta="right">Δ ₹/kg</Table.Th><Table.Th ta="right">Δ slack h</Table.Th>
              </Table.Tr></Table.Thead>
              <Table.Tbody>{card.alternatives.map(a => (
                <Table.Tr key={`${a.dest_id}|${a.mode}|${a.dispatch_day}`} c={a.feasible ? undefined : 'dimmed'}
                  title={a.feasible ? undefined : a.reject_reason || 'infeasible'}>
                  <Table.Td>{a.dest_id}</Table.Td><Table.Td>{a.mode}</Table.Td><Table.Td ta="right">{a.dispatch_day}</Table.Td>
                  <Table.Td><Badge size="sm" variant={a.feasible ? 'light' : 'outline'} color={REASON_COLOUR[a.reason_code]}>
                    {a.reason_code}</Badge></Table.Td>
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

export function ReasonDrawer({ open, onClose }: { open: DrawerOpen | undefined; onClose: () => void }) {
  useHotkeys([['Escape', onClose]], [])
  useFocusReturn({ opened: !!open })
  return (
    <AnimatePresence>
      {open && <Portal key="reason-drawer">
        <m.div className="drawer-backdrop" onClick={onClose}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} />
        <FocusTrap active>
          <m.aside className="reason-drawer plan" role="dialog" aria-modal="true" aria-label="Reason card" tabIndex={-1}
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={spring.soft}>
            <Group justify="space-between" mb="sm">
              <Text fw={700} c="dimmed" tt="uppercase" size="sm">Reason card</Text>
              <CloseButton size="lg" onClick={onClose} aria-label="Close reason card" />
            </Group>
            <Body open={open} />
          </m.aside>
        </FocusTrap>
      </Portal>}
    </AnimatePresence>
  )
}
