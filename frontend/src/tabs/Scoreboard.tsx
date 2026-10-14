// Scoreboard tab (ARCHITECTURE §16; port of C-12). Shows stored KPIs; deltas via lib/delta.ts only.
// `step` (presenter story mode): 0 tiles, 1 hero + spoilage melt, 2..6 ladder bars, 7 validator + waterfall.
// undefined = everything shown. Later beats stay mounted but hidden so the layout never jumps.
import { Group, Paper, SimpleGrid, Stack, Text, ThemeIcon } from '@mantine/core'
import { IconTrendingDown, IconTrendingUp } from '@tabler/icons-react'
import { m, useReducedMotion } from 'motion/react'
import { useEffect, useRef } from 'react'
import { KpiTile, Odometer, toneOf } from '../components/KpiTile'
import { LadderCharts } from '../components/Ladder'
import { Reveal } from '../components/score/Reveal'
import { SpoilageMelt } from '../components/score/SpoilageMelt'
import { ValidatorPanel } from '../components/ValidatorPanel'
import { delta, fmt, fmtSigned } from '../lib/delta'
import { spring } from '../theme'
import type { Kpis, RunDetail } from '../types'

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } }

export function Scoreboard({ run, step }: { run: RunDetail; step?: number }) {
  const at = (s: number) => step == null || step >= s
  const reduce = useReducedMotion()
  const ladderRef = useRef<HTMLDivElement>(null)
  useEffect(() => { // keep the current beat on the projector; step 7 scrolls itself (LadderCharts)
    if (step == null || step >= 7) return
    const behavior = reduce ? 'auto' : 'smooth'
    if (step < 2) window.scrollTo({ top: 0, behavior })
    else ladderRef.current?.scrollIntoView({ block: 'start', behavior })
  }, [step, reduce])
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
        <Reveal show={at(1)}><m.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={spring.soft}>
          <Paper radius="lg" p="xl" className="hero">
            <Group gap="lg" wrap="nowrap">
              <ThemeIcon size={64} radius="xl" variant="white" color={dNet >= 0 ? 'green' : 'red'}>
                {dNet >= 0 ? <IconTrendingUp size={38} /> : <IconTrendingDown size={38} />}
              </ThemeIcon>
              <div>
                <Text fz={40} fw={800} lh={1.1} c="white">
                  ₹<Odometer text={fmt(Math.abs(dNet))} /> {dNet >= 0 ? 'more' : 'less'} net than {base.policy}
                </Text>
                <Text fz="lg" c="white" opacity={0.85} mt={6}>
                  {run.policy} ₹{fmt(k.net_inr)} vs {base.policy} ₹{fmt(bk!.net_inr)} · same simulator, seed {run.seed}
                </Text>
              </div>
            </Group>
            <SpoilageMelt ours={k.spoilage_kg} base={bk!.spoilage_kg} oursName={run.policy} baseName={base.policy} />
          </Paper>
        </m.div></Reveal>
      )}

      <m.div variants={stagger} initial="hidden" animate="show">
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3, xl: 5 }} spacing="md">
          <KpiTile label="Net" value={`₹${fmt(k.net_inr)}`} {...tile('net_inr', 0, ' ₹')} />
          <KpiTile label="Spoilage" value={`${fmt(k.spoilage_kg)} kg`} ring={k.spoilage_pct} ringTone="bad"
            sub={`${fmt(k.spoilage_pct, 1)}% of supply`}
            {...tile('spoilage_kg', 0, ' kg', true)} />
          <KpiTile label="Demand fulfillment" value={`${fmt(k.demand_fulfillment_pct, 1)}%`}
            ring={k.demand_fulfillment_pct} ringTone="good" {...tile('demand_fulfillment_pct', 1, ' pp')} />
          <KpiTile label="Min destination fill" value={`${fmt(k.min_dest_fill_pct, 1)}%`}
            ring={k.min_dest_fill_pct} ringTone="good" {...tile('min_dest_fill_pct', 1, ' pp')} />
          <KpiTile label="Violations" value={String(k.violations)}
            sub={bk ? `baseline ${base!.policy}: ${bk.violations}` : undefined} />
        </SimpleGrid>
      </m.div>
      <Text size="sm" c="dimmed" mt={-8}>
        run {run.run_id} · scenario {run.scenario} · policy {run.policy} · seed {run.seed}
        {base ? ` · deltas vs ${base.policy} (${base.source})` : ' · no baseline on disk'}
      </Text>

      <div ref={ladderRef} className="story-anchor">
        <Reveal show={at(2)}><LadderCharts scenario={run.scenario} seed={run.seed} step={step} /></Reveal>
      </div>
      <Reveal show={at(7)}><ValidatorPanel validation={run.validation} /></Reveal>
    </Stack>
  )
}
