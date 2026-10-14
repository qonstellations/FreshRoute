// Run selector over GET /api/runs (DATABASE §11.2).
import type { RunSummary } from '../types'

export function RunPicker({ runs, value, onChange }:
  { runs: RunSummary[]; value: string | null; onChange: (id: string) => void }) {
  return (
    <label>
      Run
      <select value={value ?? ''} onChange={e => onChange(e.target.value)} disabled={!runs.length}>
        {!runs.length && <option value="">no runs on disk</option>}
        {runs.map(r => <option key={r.run_id} value={r.run_id}>{r.run_id}</option>)}
      </select>
    </label>
  )
}
