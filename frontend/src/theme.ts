// Shared theme + spring presets (D-24, D-27). Atelier palette: cream paper, ink blue.
// Components import springs from here, not ad-hoc numbers.
import { createTheme, type MantineColorsTuple } from '@mantine/core'

// ink blue #0048ae ramp (filled = [8])
const ink: MantineColorsTuple = [
  '#eef3fc', '#d8e4f8', '#b3cbf1', '#8aafe8', '#6489d4',
  '#4569bd', '#2f55a8', '#1c4696', '#0b3c85', '#062f6c',
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
