// Independent validator output (validation.json, DATABASE §5.8), shown verbatim.
import { Badge, Group, Paper, Stack, Table, Text, ThemeIcon, Title } from '@mantine/core'
import { IconFileOff } from '@tabler/icons-react'
import { m, useReducedMotion } from 'motion/react'
import { spring } from '../theme'
import type { Validation } from '../types'

const SHIELD = 'M32 4 L56 13 V31 C56 46 45 56 32 60 C19 56 8 46 8 31 V13 Z'

/** Shield; when the served total is 0 the check mark is drawn on a spring, otherwise a cross. */
function Shield({ ok }: { ok: boolean }) {
  const reduce = useReducedMotion()
  const c = ok ? 'var(--mantine-color-green-6)' : 'var(--mantine-color-red-6)'
  const draw = (delay: number) => ({
    initial: { pathLength: reduce ? 1 : 0 }, animate: { pathLength: 1 }, transition: { ...spring.bouncy, delay },
  })
  return (
    <m.svg width="88" height="88" viewBox="0 0 64 64" aria-hidden
      initial={reduce ? false : { scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={spring.bouncy}>
      <path d={SHIELD} fill={ok ? 'var(--mantine-color-green-0)' : 'var(--mantine-color-red-0)'} stroke={c} strokeWidth="3"
        strokeLinejoin="round" />
      {ok
        ? <m.path d="M21 32 L29 40 L44 24" fill="none" stroke={c} strokeWidth="5" strokeLinecap="round"
          strokeLinejoin="round" {...draw(0.3)} />
        : <>
          <m.path d="M23 23 L41 41" fill="none" stroke={c} strokeWidth="5" strokeLinecap="round" {...draw(0.3)} />
          <m.path d="M41 23 L23 41" fill="none" stroke={c} strokeWidth="5" strokeLinecap="round" {...draw(0.45)} />
        </>}
    </m.svg>
  )
}

export function ValidatorPanel({ validation }: { validation: Validation | null }) {
  if (!validation) return (
    <Paper withBorder radius="lg" p="xl">
      <Stack align="center" gap="xs">
        <ThemeIcon size={48} radius="xl" variant="light" color="gray"><IconFileOff size={28} /></ThemeIcon>
        <Text fw={600}>No validation.json for this run</Text>
      </Stack>
    </Paper>
  )
  const ok = validation.violation_total === 0
  const counts = Object.entries(validation.counts ?? {}).sort(([a], [b]) => a.localeCompare(b))
  const warnings = validation.warnings ?? []
  return (
    <Paper withBorder radius="lg" p="lg">
      <Group gap="xl" wrap="nowrap" align="center">
        <Shield ok={ok} />
        <div>
          <Title order={3}>Independent validator</Title>
          <Text size="sm" c="dimmed">Re-implements the maths separately and checks the plan against every hard rule.</Text>
          <Badge mt="sm" size="xl" radius="sm" color={ok ? 'green' : 'red'} variant="filled">
            {validation.violation_total} violations
          </Badge>
          {warnings.length > 0 && <Badge mt="sm" ml="sm" size="xl" radius="sm" color="yellow" variant="light">
            {warnings.length} warnings</Badge>}
        </div>
      </Group>
      {counts.length > 0 && (
        <Table mt="md" striped fz="md" maw={480}>
          <Table.Thead><Table.Tr><Table.Th>code</Table.Th><Table.Th ta="right">count</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>
            {counts.map(([c, n]) => <Table.Tr key={c}><Table.Td>{c}</Table.Td><Table.Td ta="right">{n}</Table.Td></Table.Tr>)}
          </Table.Tbody>
        </Table>
      )}
      {warnings.length > 0 && (
        <Table mt="md" striped fz="md">
          <Table.Thead><Table.Tr><Table.Th>warning</Table.Th><Table.Th>detail</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>
            {warnings.map((w, i) => <Table.Tr key={i}><Table.Td>{w.code}</Table.Td><Table.Td>{w.detail}</Table.Td></Table.Tr>)}
          </Table.Tbody>
        </Table>
      )}
    </Paper>
  )
}
