// SyntheticBanner + StatusBanner (ARCHITECTURE §16.1: synthetic banner always shown for synthetic data).
import { Alert, Stack } from '@mantine/core'
import { IconAlertTriangle, IconFlask, IconInfoCircle } from '@tabler/icons-react'
import { AnimatePresence, m } from 'motion/react'
import type { ReactNode } from 'react'
import { spring } from '../theme'
import type { Manifest } from '../types'

// One banner that springs in/out (transform + opacity only).
function Banner({ color, icon, children }: { color: string; icon: ReactNode; children: ReactNode }) {
  return (
    <m.div layout initial={{ opacity: 0, y: -10, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.98 }} transition={spring.soft}>
      <Alert variant="light" color={color} icon={icon} radius="md">{children}</Alert>
    </m.div>
  )
}

export function SyntheticBanner({ show }: { show: boolean }) {
  return (
    <AnimatePresence initial={false}>
      {show && (
        <Banner key="synthetic" color="yellow" icon={<IconFlask />}>
          <strong>SYNTHETIC DATA:</strong> figures come from a synthetic scenario or a hand-written example, not organizer data.
        </Banner>
      )}
    </AnimatePresence>
  )
}

export function StatusBanner({ fixture, manifest, error }:
  { fixture: boolean; manifest: Manifest | null; error: string }) {
  return (
    <Stack gap="xs">
      <AnimatePresence initial={false}>
        {fixture && (
          <Banner key="fixture" color="blue" icon={<IconInfoCircle />}>
            No run under outputs/. Showing the example fixture (placeholder).
          </Banner>
        )}
        {manifest?.solver?.fallback_used && (
          <Banner key="fallback" color="red" icon={<IconAlertTriangle />}>
            Solver fallback used: this plan came from the FEFO-greedy fallback, not HiGHS.
          </Banner>
        )}
        {error && (
          <Banner key="error" color="red" icon={<IconAlertTriangle />}><strong>{error}</strong></Banner>
        )}
      </AnimatePresence>
    </Stack>
  )
}
