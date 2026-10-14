// Shared theme + spring presets (D-24). Components import springs from here, not ad-hoc numbers.
import { createTheme } from '@mantine/core'

export const theme = createTheme({
  primaryColor: 'green',
  fontFamily: 'Inter Variable, system-ui, sans-serif',
  headings: { fontFamily: 'Inter Variable, system-ui, sans-serif' },
  defaultRadius: 'md',
})

export const spring = {
  snappy: { type: 'spring', stiffness: 420, damping: 32 },
  soft: { type: 'spring', stiffness: 180, damping: 24 },
  bouncy: { type: 'spring', stiffness: 300, damping: 18 },
} as const
