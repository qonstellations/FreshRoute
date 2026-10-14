// Trust tab (ARCHITECTURE §16): assumptions, cost-model coefficients (GET /api/config), run_manifest.json.
import { Alert, Badge, Code, Group, Paper, Skeleton, Stack, Table, Text, TextInput, ThemeIcon, Title } from '@mantine/core'
import { IconAdjustments, IconAlertTriangle, IconBook2, IconFileOff, IconFingerprint, IconSearch } from '@tabler/icons-react'
import { m } from 'motion/react'
import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import { spring } from '../theme'
import type { ConfigConstants, RunDetail } from '../types'

const show = (v: unknown) => (typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v))

function Section({ icon, title, sub, children }: { icon: ReactNode; title: ReactNode; sub?: ReactNode; children: ReactNode }) {
  return (
    <m.div initial={{ opacity: 0, y: 32 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.15 }}
      transition={spring.soft}>
      <Paper withBorder radius="lg" p="lg">
        <Group gap="md" mb="md" wrap="nowrap">
          <ThemeIcon size={44} radius="md" variant="light">{icon}</ThemeIcon>
          <div>
            <Title order={3}>{title}</Title>
            {sub && <Text size="sm" c="dimmed">{sub}</Text>}
          </div>
        </Group>
        {children}
      </Paper>
    </m.div>
  )
}

const KV = ({ rows }: { rows: [string, ReactNode][] }) => (
  <Table fz="md" verticalSpacing="xs" withRowBorders>
    <Table.Tbody>
      {rows.map(([k, v]) => <Table.Tr key={k}><Table.Th w={200} c="dimmed" fw={500}>{k}</Table.Th><Table.Td>{v}</Table.Td></Table.Tr>)}
    </Table.Tbody>
  </Table>
)

export function Trust({ run }: { run: RunDetail }) {
  const [config, setConfig] = useState<ConfigConstants | null>(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  useEffect(() => { api.config().then(setConfig).catch(e => setError(String(e.message ?? e))) }, [])
  const m_ = run.manifest
  const s = m_?.solver
  // display-only filter over served constants
  const entries = Object.entries(config ?? {}).filter(([k, v]) =>
    `${k} ${show(v)}`.toLowerCase().includes(q.trim().toLowerCase()))

  return (
    <Stack gap="lg">
      <Section icon={<IconFingerprint size={26} />} title="Run manifest"
        sub="run_manifest.json: everything needed to reproduce this run bit for bit.">
        {!m_ ? (
          <Stack align="center" gap="xs" py="lg">
            <ThemeIcon size={48} radius="xl" variant="light" color="gray"><IconFileOff size={28} /></ThemeIcon>
            <Text fw={600}>No run_manifest.json for this run</Text>
          </Stack>
        ) : <>
          <Group gap="sm" mb="md">
            <Badge size="lg" variant="light" color="blue">solver status {s?.status ?? 'n/a (no solver)'}</Badge>
            <Badge size="lg" variant="light" color="grape">MIP gap {s ? show(s.mip_gap) : 'n/a'}</Badge>
            <Badge size="lg" variant="light" color="gray">solve {s ? `${show(s.solve_seconds)} s` : 'n/a'}</Badge>
            {s && <Badge size="lg" variant={s.fallback_used ? 'filled' : 'light'} color={s.fallback_used ? 'orange' : 'green'}>
              {s.fallback_used ? 'FEFO fallback used' : 'no fallback'}</Badge>}
          </Group>
          <KV rows={[
            ['run_id', <Code fz="sm">{m_.run_id}</Code>], ['policy', m_.policy], ['seed', show(m_.seed)],
            ['realization', m_.realization], ['flags', <Code fz="sm">{show(m_.flags)}</Code>],
            ['git SHA', <Code fz="sm">{m_.git_sha}</Code>], ['scenario', <Code fz="sm">{m_.scenario}</Code>],
            ['scenario sha256', <Code fz="sm">{m_.scenario_sha256}</Code>], ['timestamp (UTC)', m_.timestamp_utc],
            ['slack usage', <Code fz="sm">{s ? show(s.slack_usage) : 'n/a'}</Code>],
          ]} />
          <Text fw={600} mt="md" mb={6}>Package versions</Text>
          <Group gap="xs">
            {Object.entries(m_.package_versions ?? {}).map(([k, v]) =>
              <Badge key={k} variant="outline" color="gray" size="lg" tt="none">{k} {v}</Badge>)}
          </Group>
        </>}
      </Section>

      <Section icon={<IconAdjustments size={26} />} title={<>Coefficients (<Code fz="inherit">config.py</Code>)</>}
        sub="Served verbatim by GET /api/config. Per-commodity prices, costs and shelf lives come from the scenario tables, not from code.">
        {error ? <Alert color="red" icon={<IconAlertTriangle />} title="Cannot load config">{error}</Alert>
          : !config ? <Stack gap={8}>{[0, 1, 2, 3, 4].map(i => <Skeleton key={i} h={28} />)}</Stack>
          : <>
            <TextInput placeholder="Filter constants…" leftSection={<IconSearch size={18} />} value={q}
              onChange={e => setQ(e.currentTarget.value)} mb="sm" maw={360} size="md" />
            <Table striped highlightOnHover fz="md">
              <Table.Thead><Table.Tr><Table.Th>constant</Table.Th><Table.Th>value</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {entries.map(([k, v]) =>
                  <Table.Tr key={k}><Table.Td><Code fz="sm">{k}</Code></Table.Td><Table.Td>{show(v)}</Table.Td></Table.Tr>)}
              </Table.Tbody>
            </Table>
            {!entries.length && <Text c="dimmed" ta="center" py="md">No constant matches “{q}”.</Text>}
          </>}
      </Section>

      <Section icon={<IconBook2 size={26} />} title="Assumptions">
        <Text>Every modelling assumption (A-01, A-02, …) and its status (confirm / team) is logged in{' '}
          <Code>docs/ARCHITECTURE.md §20</Code> (Assumption log). Team-chosen constants above are tagged there and in{' '}
          <Code>§19</Code>.</Text>
      </Section>
    </Stack>
  )
}
