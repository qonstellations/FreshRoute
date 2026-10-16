// Run selector over GET /api/runs (DATABASE §11.2).
import { Select } from '@mantine/core'
import { IconFolderOpen } from '@tabler/icons-react'
import { policyName, scenarioName } from '../lib/words'
import type { RunSummary } from '../types'

// Plain label instead of the folder name ("practice__milp__s42"); a clash keeps the folder name so each stays unique.
const plain = (r: RunSummary) => r.scenario && r.policy
  ? `${scenarioName(r.scenario.split(/[\\/]/).pop()!).split(' · ')[0]} · ${policyName(r.policy)} · random seed ${r.seed}`
    + (r.run_id.endsWith('__nv') ? ' · flexible amounts' : '')
  : r.run_id

export function RunPicker({ runs, value, onChange }:
  { runs: RunSummary[]; value: string | null; onChange: (id: string) => void }) {
  return (
    <Select
      label="Saved results"
      leftSection={<IconFolderOpen size={16} />}
      data={runs.map((r, _, all) => {
        const label = plain(r)
        return { value: r.run_id, label: all.some(o => o !== r && plain(o) === label) ? `${label} (${r.run_id})` : label }
      })}
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
