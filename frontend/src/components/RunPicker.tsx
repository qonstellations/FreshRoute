// Run selector over GET /api/runs (DATABASE §11.2).
import { Select } from '@mantine/core'
import { IconFolderOpen } from '@tabler/icons-react'
import type { RunSummary } from '../types'

export function RunPicker({ runs, value, onChange }:
  { runs: RunSummary[]; value: string | null; onChange: (id: string) => void }) {
  return (
    <Select
      label="Saved results"
      leftSection={<IconFolderOpen size={16} />}
      data={runs.map(r => r.run_id)}
      value={value}
      onChange={v => v && onChange(v)}
      disabled={!runs.length}
      placeholder={runs.length ? 'Pick a saved result' : 'No saved results yet'}
      allowDeselect={false}
      searchable
      comboboxProps={{ transitionProps: { transition: 'pop', duration: 150 } }}
    />
  )
}
