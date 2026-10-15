// Trust tab (ARCHITECTURE §16): assumptions, cost-model coefficients (GET /api/config), run_manifest.json.
import { Alert, Badge, Code, Group, Paper, Skeleton, Stack, Table, Text, TextInput, ThemeIcon, Title } from '@mantine/core'
import { IconAdjustments, IconAlertTriangle, IconBook2, IconFileOff, IconFingerprint, IconSearch } from '@tabler/icons-react'
import { m } from 'motion/react'
import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import { Explain } from '../components/Explain'
import { policyName } from '../lib/words'
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

// [plain label, value, original manifest key shown small for auditors]
const KV = ({ rows }: { rows: [string, ReactNode, string][] }) => (
  <Table fz="md" verticalSpacing="xs" withRowBorders>
    <Table.Tbody>
      {rows.map(([k, v, key]) => <Table.Tr key={k}><Table.Th w={200} c="dimmed" fw={500}>{k}{' '}
        <Text span size="xs" c="dimmed" ff="monospace">({key})</Text></Table.Th><Table.Td>{v}</Table.Td></Table.Tr>)}
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
      <Section icon={<IconFingerprint size={26} />} title="Reproduce this exact result"
        sub={<>Everything needed to get exactly the same numbers again (the{' '}
          <Explain term="manifest">run manifest</Explain>, <Code fz="xs">run_manifest.json</Code>).</>}>
        {!m_ ? (
          <Stack align="center" gap="xs" py="lg">
            <ThemeIcon size={48} radius="xl" variant="light" color="gray"><IconFileOff size={28} /></ThemeIcon>
            <Text fw={600}>This result has no reproduction record (run_manifest.json is missing)</Text>
          </Stack>
        ) : <>
          <Group gap="sm" mb="md">
            <Badge size="lg" variant="light" color="blue">Solver result: {s?.status ?? 'none (rule-based plan)'}</Badge>
            <Badge size="lg" variant="light" color="grape" tt="none">
              <Explain term="mipGap">Distance from proven best</Explain>: {s ? show(s.mip_gap) : 'n/a'}</Badge>
            <Badge size="lg" variant="light" color="gray" tt="none">Solve time {s ? `${show(s.solve_seconds)} s` : 'n/a'}</Badge>
            {s && <Badge size="lg" variant={s.fallback_used ? 'filled' : 'light'} color={s.fallback_used ? 'orange' : 'green'}>
              <Explain term="fallback">{s.fallback_used ? 'Backup plan used' : 'No backup plan needed'}</Explain></Badge>}
          </Group>
          <KV rows={[
            ['Result ID', <Code fz="sm">{m_.run_id}</Code>, 'run_id'], ['Plan type', policyName(m_.policy), 'policy'],
            ['Random seed', show(m_.seed), 'seed'], ['Data draw', m_.realization, 'realization'],
            ['Options turned on', <Code fz="sm">{show(m_.flags)}</Code>, 'flags'],
            ['Code version (git)', <Code fz="sm">{m_.git_sha}</Code>, 'git_sha'],
            ['Scenario folder', <Code fz="sm">{m_.scenario}</Code>, 'scenario'],
            ['Fingerprint of input data (sha256)', <Code fz="sm">{m_.scenario_sha256}</Code>, 'scenario_sha256'],
            ['Created (UTC)', m_.timestamp_utc, 'timestamp_utc'],
            ['Soft-rule slack used', <Code fz="sm">{s ? show(s.slack_usage) : 'n/a'}</Code>, 'slack_usage'],
          ]} />
          <Text fw={600} mt="md" mb={6}>Software versions</Text>
          <Group gap="xs">
            {Object.entries(m_.package_versions ?? {}).map(([k, v]) =>
              <Badge key={k} variant="outline" color="gray" size="lg" tt="none">{k} {v}</Badge>)}
          </Group>
        </>}
      </Section>

      <Section icon={<IconAdjustments size={26} />} title="Every number the model uses"
        sub={<>The constants FreshRoute uses (from <Code fz="xs">config.py</Code>). Prices, costs and shelf lives come from the
          scenario data, not from code.</>}>
        {error ? <Alert color="red" icon={<IconAlertTriangle />} title="Couldn’t load the constants">{error}</Alert>
          : !config ? <Stack gap={8}>{[0, 1, 2, 3, 4].map(i => <Skeleton key={i} h={28} />)}</Stack>
          : <>
            <TextInput placeholder="Search the numbers…" leftSection={<IconSearch size={18} />} value={q}
              onChange={e => setQ(e.currentTarget.value)} mb="sm" maw={360} size="md" />
            <Table striped highlightOnHover fz="md">
              <Table.Thead><Table.Tr><Table.Th>Name</Table.Th><Table.Th>Value</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>
                {entries.map(([k, v]) =>
                  <Table.Tr key={k}><Table.Td><Code fz="sm">{k}</Code></Table.Td><Table.Td>{show(v)}</Table.Td></Table.Tr>)}
              </Table.Tbody>
            </Table>
            {!entries.length && <Text c="dimmed" ta="center" py="md">Nothing matches “{q}”.</Text>}
          </>}
      </Section>

      <Section icon={<IconBook2 size={26} />} title="Our assumptions">
        <Text>Where the data leaves a gap, we made an assumption. Each one is written down with a number
          (A-01, A-02, …) and marked as either confirmed or chosen by our team. Team-chosen constants in the list above
          are marked the same way.</Text>
        <Text size="xs" c="dimmed" mt={6}>Full list: <Code fz="xs">docs/ARCHITECTURE.md §20</Code> (assumption log) and{' '}
          <Code fz="xs">§19</Code>.</Text>
      </Section>
    </Stack>
  )
}
