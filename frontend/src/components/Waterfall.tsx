// Net reconciling waterfall (ARCHITECTURE §12/§16, DATABASE §5.11 waterfall.json). Steps drawn as given.
import { Group, Paper, Stack, Text, Title } from '@mantine/core'
import { fmt, fmtSigned } from '../lib/delta'
import { policyName } from '../lib/words'
import type { Ladder } from '../types'

export const C = {
  good: 'var(--mantine-color-green-6)', bad: 'var(--mantine-color-red-6)', total: 'var(--mantine-color-blue-7)',
  grid: 'light-dark(var(--mantine-color-gray-3), var(--border))', axis: 'light-dark(var(--mantine-color-gray-7), var(--muted))',
}
export const tooltipStyle = {
  contentStyle: { borderRadius: 10, border: '1px solid var(--border)', background: 'var(--panel)', color: 'var(--text)', boxShadow: '0 8px 24px rgb(0 0 0 / .12)', fontSize: 15 },
  labelStyle: { fontWeight: 700, marginBottom: 4 },
  itemStyle: { color: 'var(--text)' },
  cursor: { fill: 'color-mix(in srgb, var(--accent) 12%, transparent)' },
}

export function Waterfall({ waterfall }: { waterfall: Ladder['waterfall'] }) {
  const maxAbs = Math.max(1, ...waterfall.steps.filter(s => s.type === 'delta').map(s => Math.abs(s.value)))
  return (
    <Paper withBorder radius="lg" p="lg">
      <Title order={3}>Where the extra profit comes from: {policyName(waterfall.baseline)} → {policyName(waterfall.plan)}</Title>
      <Text size="sm" c="dimmed" mb="md">
        Read top to bottom: we start from the old rule&apos;s profit, add or subtract what each change is worth, and
        land on FreshRoute&apos;s profit. Green is money gained, red is money lost.
      </Text>
      <Stack gap={6}>
        {waterfall.steps.map(s => s.type === 'total' ? (
          <Group key={s.label} justify="space-between" px="sm" py={8}
            style={{ background: 'var(--mantine-color-blue-light)', borderRadius: 8 }}>
            <Text fw={700}>{s.label}</Text>
            <Text fw={700} c={C.total}>₹{fmt(s.value)}</Text>
          </Group>
        ) : (
          <Group key={s.label} wrap="nowrap" gap="sm" px="sm">
            <Text size="sm" style={{ flex: '0 0 38%' }}>{s.label}</Text>
            <div style={{ flex: 1, height: 14, background: 'color-mix(in srgb, var(--accent) 12%, transparent)', borderRadius: 7 }}>
              <div style={{ width: `${(Math.abs(s.value) / maxAbs) * 100}%`, height: '100%', borderRadius: 7,
                background: s.value >= 0 ? C.good : C.bad }} />
            </div>
            <Text size="sm" fw={600} w={110} ta="right" c={s.value >= 0 ? C.good : C.bad}>{fmtSigned(s.value, 0, ' ₹')}</Text>
          </Group>
        ))}
      </Stack>
      <Text size="sm" c="dimmed" mt="sm">
        Every step is measured by the engine; the steps add up to the final total within ₹{waterfall.tolerance_inr}.
        Bar lengths are relative to the biggest step.
      </Text>
    </Paper>
  )
}
