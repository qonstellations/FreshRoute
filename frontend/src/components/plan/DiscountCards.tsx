// Discount cards (ARCHITECTURE §15): one card per marked-down shipment; a click morphs it into the drawer header.
import { Badge, Card, Group, SimpleGrid, Stack, Text, Title } from '@mantine/core'
import { IconDiscountOff } from '@tabler/icons-react'
import { m } from 'motion/react'
import { spring } from '../../theme'
import type { ReasonCard } from '../../types'
import { num } from './format'

export const cardLayoutId = (c: ReasonCard) => `disc-${c.shipment_id}`

export function DiscountCards({ cards, onOpen }: { cards: ReasonCard[]; onOpen: (c: ReasonCard) => void }) {
  const list = cards.filter(c => c.discount)
  return (
    <Stack gap="sm">
      <div>
        <Title order={3}>Discount cards</Title>
        <Text size="sm" c="dimmed">{list.length} shipments marked down · click for the reason card</Text>
      </div>
      {!list.length ? <Group gap="xs" c="dimmed" py="md"><IconDiscountOff size={28} stroke={1.4} />
        <Text c="dimmed">No discounts in this run.</Text></Group>
        : <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
          {list.map((c, i) => c.discount && (
            <m.div key={c.shipment_id} layoutId={cardLayoutId(c)} transition={spring.soft}
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0, transition: { ...spring.soft, delay: i * 0.06 } }}
              whileHover={{ y: -4, scale: 1.02, transition: spring.bouncy }} whileTap={{ scale: 0.98 }}>
              <Card component="button" onClick={() => onOpen(c)} withBorder radius="md" padding="md" bg="var(--mantine-color-yellow-light)"
                w="100%" ta="left" style={{ cursor: 'pointer', borderColor: 'var(--mantine-color-yellow-outline)' }}>
                <Group justify="space-between" align="flex-start">
                  <Text fw={800} fz={26} lh={1}>{num(c.discount.tier_pct)} %<Text span fz="sm" fw={500}> off</Text></Text>
                  <Badge variant="light" color="yellow">day {c.discount.day}</Badge>
                </Group>
                <Text fw={600} mt="sm">{c.batch_id} {c.commodity} → {c.chosen.dest_id}</Text>
                <Text size="sm" c="dimmed">unsold-risk {c.discount.risk.toFixed(2)}
                  {c.discount.capped_by !== 'none' && ` · capped by ${c.discount.capped_by}`}</Text>
              </Card>
            </m.div>))}
        </SimpleGrid>}
    </Stack>
  )
}
