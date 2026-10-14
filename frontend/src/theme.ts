// Shared theme + spring presets (D-24, D-27). Atelier palette: cream paper, ink blue.
// Components import springs from here, not ad-hoc numbers.
import { createTheme, type MantineColorsTuple } from '@mantine/core'

// ink green #1f7a4d ramp (filled = [6] light / [8] dark)
const ink: MantineColorsTuple = [
  '#ecf6ef', '#d3e9da', '#aed8bc', '#83c295', '#55a66e',
  '#2f8b52', '#1f7a4d', '#186641', '#124f34', '#0b3523',
];

export const theme = createTheme({
  primaryColor: 'ink',
  colors: { ink },
  fontFamily: '"Kode Mono", monospace',
  headings: { fontFamily: 'Anton, sans-serif', fontWeight: '400' },
  defaultRadius: 0,
})

export const spring = {
  snappy: { type: 'spring', stiffness: 420, damping: 32 },
  soft: { type: 'spring', stiffness: 180, damping: 24 },
  bouncy: { type: 'spring', stiffness: 300, damping: 18 },
} as const
