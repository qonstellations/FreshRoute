// Scoreboard tab (ARCHITECTURE §16; port of C-12). Shows stored KPIs; deltas via lib/delta.ts only.
import { Group, Paper, Progress, Tooltip, SimpleGrid, Stack, Text, ThemeIcon } from '@mantine/core'
import { IconTrendingDown, IconTrendingUp } from '@tabler/icons-react'
import { m } from 'motion/react'
import { Explain } from '../components/Explain'
import { KpiTile, Odometer, toneOf } from '../components/KpiTile'
import { LadderCharts } from '../components/Ladder'
import { SpoilageMelt } from '../components/score/SpoilageMelt'
import { ValidatorPanel } from '../components/ValidatorPanel'
import { delta, fmt, fmtSigned } from '../lib/delta'
import { policyName, SPOIL_PARTS } from '../lib/words'
import { spring } from '../theme'
import type { Kpis, RunDetail } from '../types'

const lower = (s: string) => /^[A-Z][a-z]/.test(s) ? s[0].toLowerCase() + s.slice(1) : s // 'Expiry-first…' mid-sentence
const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } }

export function Scoreboard({ run }: { run: RunDetail }) {
  const k = run.kpis
  const base = run.fixture ? null : run.baseline
  const bk = base?.kpis
  const tile = (key: keyof Kpis, digits: number, unit: string, lowerIsBetter = false) => {
    const d = delta(k[key], bk?.[key])
    return { delta: d == null ? null : fmtSigned(d, digits, unit), tone: toneOf(d, lowerIsBetter) }
  }
  const dNet = delta(k.net_inr, bk?.net_inr)

  return (
    <Stack gap="lg">
      {base && dNet != null && base.policy !== run.policy && (
        <m.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={spring.soft}>
          <Paper radius="lg" p="xl" className="band">
            <Group gap="lg" wrap="nowrap">
              <ThemeIcon size={64} radius="xl" variant="white" color={dNet >= 0 ? 'green' : 'red'}>
                {dNet >= 0 ? <IconTrendingUp size={38} /> : <IconTrendingDown size={38} />}
              </ThemeIcon>
              <div>
                <Text fz={40} fw={800} lh={1.1} c="white">
                  {policyName(run.policy)} earns ₹<Odometer text={fmt(Math.abs(dNet))} /> {dNet >= 0 ? 'more' : 'less'} than the {lower(policyName(base.policy))}
                </Text>
                <Text fz="lg" c="white" opacity={0.85} mt={6}>
                  ₹{fmt(k.net_inr)} vs ₹{fmt(bk!.net_inr)} profit after all costs · same 3 simulated days, same demand,
                  scored by <Explain term="simulator">one shared simulator</Explain> · <Explain term="seed">seed {run.seed}</Explain>
                </Text>
              </div>
            </Group>
            <SpoilageMelt ours={k.spoilage_kg} base={bk!.spoilage_kg} oursName={policyName(run.policy)} baseName={policyName(base.policy)} />
          </Paper>
        </m.div>
      )}

      <m.div variants={stagger} initial="hidden" animate="show">
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3, xl: 5 }} spacing="md">
          <KpiTile label="Profit after all costs" hint="net" value={`₹${fmt(k.net_inr)}`} {...tile('net_inr', 0, ' ₹')} />
          <KpiTile label="Food spoiled" hint="spoilage" value={`${fmt(k.spoilage_kg)} kg`} ring={k.spoilage_pct} ringTone="bad"
            sub={`${fmt(k.spoilage_pct, 1)}% of all produce`}
            {...tile('spoilage_kg', 0, ' kg', true)} />
          <KpiTile label="Orders filled" hint="fulfilment" value={`${fmt(k.demand_fulfillment_pct, 1)}%`}
            ring={k.demand_fulfillment_pct} ringTone="good" {...tile('demand_fulfillment_pct', 1, ' pp')} />
          <KpiTile label="Worst-served market" hint="minFill" value={`${fmt(k.min_dest_fill_pct, 1)}%`}
            ring={k.min_dest_fill_pct} ringTone="good" {...tile('min_dest_fill_pct', 1, ' pp')} />
          <KpiTile label="Rule breaks" hint="violations" value={String(k.violations)}
            sub={bk ? `${policyName(base!.policy)}: ${bk.violations}` : undefined} />
        </SimpleGrid>
      </m.div>
      <Text size="sm" c="dimmed" mt={-8}>
        <Explain note={`run ${run.run_id} · scenario ${run.scenario} · policy ${run.policy} · seed ${run.seed}${base ? ` · baseline ${base.policy} (${base.source})` : ''}`}>
          {base ? `Compared with the ${lower(policyName(base.policy))} on the same data.` : 'No baseline result saved yet, so there is nothing to compare with.'}
        </Explain>
      </Text>

      <SpoilageSplit parts={run.spoilage_breakdown_kg} total={k.spoilage_kg} />

      <LadderCharts scenario={run.scenario} seed={run.seed} />
      <ValidatorPanel validation={run.validation} />
    </Stack>
  )
}

// total is the engine's kpis.spoilage_kg (the UI never sums KPIs, AGENTS.md rule 8); the parts
// only size the bar. Older runs or the fixture may lack the breakdown: render nothing.
function SpoilageSplit({ parts, total }: { parts?: RunDetail['spoilage_breakdown_kg']; total: number }) {
  const keys = Object.keys(SPOIL_PARTS) as (keyof typeof SPOIL_PARTS)[]
  if (!parts || !(total > 0)) return null
  return (
    <Paper radius="lg" p="lg" withBorder>
      <Text fw={700} mb={4}>Where the spoiled food went</Text>
      <Text size="sm" c="dimmed" mb="sm">{fmt(total)} kg in total, split by cause. Hover a part to see what it means.</Text>
      <Progress.Root size={28} radius="md">
        {keys.map(key => (
          <Tooltip key={key} label={SPOIL_PARTS[key].note} multiline w={260} withArrow>
            <Progress.Section value={(parts[key] / total) * 100} color={SPOIL_PARTS[key].color} />
          </Tooltip>
        ))}
      </Progress.Root>
      <Group gap="lg" mt="sm">
        {keys.map(key => (
          <Text key={key} size="sm"><Explain note={SPOIL_PARTS[key].note}>{SPOIL_PARTS[key].label}</Explain>: {fmt(parts[key])} kg</Text>
        ))}
      </Group>
    </Paper>
  )
}
