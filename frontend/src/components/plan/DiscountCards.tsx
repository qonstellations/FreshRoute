// Discount cards (ARCHITECTURE §15): one card per marked-down shipment; a click morphs it into the drawer header.
import { Badge, Card, Group, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import { IconDiscountOff } from '@tabler/icons-react'
import { m } from 'motion/react'
import { spring } from '../../theme'
import type { DiscountAdvice, ReasonCard } from '../../types'
import { cappedText, num } from './format'
import { Explain } from '../Explain'
import { ADVICE, placeName, type Names } from '../../lib/words'

export const cardLayoutId = (c: ReasonCard) => `disc-${c.shipment_id}`

export function DiscountCards({ cards, advice, onOpen, names }: { cards: ReasonCard[]; advice: DiscountAdvice; onOpen: (c: ReasonCard) => void; names?: Names }) {
  const list = cards.filter(c => c.discount)
  return (
    <Stack gap="sm">
      <div>
        <Title order={3}><Explain term="markdown">Price cuts</Explain></Title>
        <Text size="sm" c="dimmed">{list.length
          ? `${list.length} shipments get a discount to help them sell before spoiling · click one for the full reason`
          : 'A discount helps old stock sell before it spoils.'}</Text>
      </div>
      {!list.length ? (advice?.length ? <AdviceList advice={advice} names={names} />
        : <Group gap="xs" c="dimmed" py="md"><IconDiscountOff size={28} stroke={1.4} />
          <Text c="dimmed">No price cuts were needed in this plan.</Text></Group>)
        : <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
          {list.map((c, i) => c.discount && (
            <m.div key={c.shipment_id} layoutId={cardLayoutId(c)} transition={spring.soft}
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0, transition: { ...spring.soft, delay: i * 0.06 } }}
              whileHover={{ y: -4, scale: 1.02, transition: spring.bouncy }} whileTap={{ scale: 0.98 }}>
              <Card component="button" onClick={() => onOpen(c)} withBorder radius="md" padding="md" bg="var(--mantine-color-yellow-light)"
                w="100%" ta="left" style={{ cursor: 'pointer', borderColor: 'var(--mantine-color-yellow-outline)' }}>
                <Group justify="space-between" align="flex-start">
                  <Text fw={800} fz={26} lh={1}>{num(c.discount.tier_pct)} %<Text span fz="sm" fw={500}> off</Text></Text>
                  <Badge variant="light" color="yellow" tt="none">from day {c.discount.day}</Badge>
                </Group>
                <Text fw={600} mt="sm">{c.batch_id} {c.commodity} → {placeName(names, c.chosen.dest_id)}</Text>
                <Text size="sm" c="dimmed">Risk of not selling: {c.discount.risk.toFixed(2)}
                  {c.discount.capped_by !== 'none' && ` · ${cappedText(c.discount.capped_by)}`}</Text>
              </Card>
            </m.div>))}
        </SimpleGrid>}
    </Stack>
  )
}

const ADVICE_SHOWN = 3

function AdviceList({ advice, names }: { advice: NonNullable<DiscountAdvice>; names?: Names }) {
  const good = advice.filter(a => a.best_cut_pct > 0)
  const shown = (good.length ? good : advice).slice(0, ADVICE_SHOWN)
  return (
    <Stack gap={6} py="xs">
      <Group gap="xs" c="dimmed"><IconDiscountOff size={24} stroke={1.4} />
        <Text fw={600}>{ADVICE.title}</Text></Group>
      <Text size="sm" c="dimmed">{good.length ? ADVICE.some(good.length, advice.length) : ADVICE.count(advice.length)}</Text>
      {shown.map(a => (
        <Text key={`${a.dest_id}-${a.commodity}-${a.day}`} size="sm">
          <b>{placeName(names, a.dest_id)} · {a.commodity} · day {a.day}</b>{a.best_cut_pct > 0 && ` · ${ADVICE.found(a.best_cut_pct, num(a.delta_net_inr))}`}: {a.reason}
        </Text>))}
      {advice.length > shown.length && <Text size="xs" c="dimmed">{ADVICE.more(advice.length - shown.length)}</Text>}
    </Stack>
  )
}
