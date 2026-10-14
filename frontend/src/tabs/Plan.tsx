// Plan tab (ARCHITECTURE §15–§16): dispatch table, reason cards, discount cards, shelf-life map.
// Every number is a served field (DATABASE §5.9–§5.10), only rounded for display.
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { DispatchSheet, RunDetail } from '../types'

const num = (v: number | null | undefined) =>
  v == null ? '' : v.toLocaleString('en-IN', { maximumFractionDigits: 1 })

// Formatting the served records back into CSV (no endpoint serves dispatch_sheet.csv as a file).
function csvUrl(rows: DispatchSheet['csv']) {
  const cols = Object.keys(rows[0] ?? {})
  const cell = (v: unknown) => {
    const s = v == null ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s
  }
  const body = [cols.join(','), ...rows.map(r => cols.map(c => cell(r[c as keyof typeof r])).join(','))].join('\n')
  return URL.createObjectURL(new Blob([body + '\n'], { type: 'text/csv' }))
}

function Dispatch({ sheet, runId }: { sheet: DispatchSheet; runId: string }) {
  const [href, setHref] = useState('')
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    const u = csvUrl(sheet.csv)
    setHref(u)
    return () => URL.revokeObjectURL(u)
  }, [sheet])
  const copy = () => navigator.clipboard.writeText(sheet.text).then(() => {
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  })

  return (
    <section>
      <div className="section-head">
        <h2>Dispatch sheet <span className="caption">{sheet.csv.length} lines, priority order</span></h2>
        <a className="button" href={href} download={`${runId}__dispatch_sheet.csv`}>Download CSV</a>
      </div>
      <div className="scroll">
        <table className="dispatch">
          <thead><tr>
            <th>#</th><th>Vehicle</th><th>Trip</th><th>Depart</th><th>Destination</th><th>Batch</th>
            <th>Commodity</th><th className="n">kg</th><th className="n">Slack h</th><th className="n">Arrive by h</th>
          </tr></thead>
          <tbody>
            {sheet.csv.map(r => (
              <tr key={`${r.trip_id}|${r.batch_id}|${r.priority_rank}`}>
                <td className="n">{r.priority_rank}</td><td>{r.vehicle_id}</td><td>{r.trip_id}</td>
                <td>{r.depart_clock}</td><td>{r.dest_name}</td><td>{r.batch_id}</td><td>{r.commodity}</td>
                <td className="n">{num(r.kg)}</td><td className="n">{num(r.slack_h)}</td>
                <td className="n">{num(r.arrive_by_h)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="section-head">
        <h3>Driver message</h3>
        <button onClick={copy}>{copied ? 'Copied' : 'Copy text'}</button>
      </div>
      <pre className="whatsapp">{sheet.text}</pre>
    </section>
  )
}

export function Plan({ runId }: { run: RunDetail; runId: string }) {
  const [sheet, setSheet] = useState<DispatchSheet | null | undefined>(undefined)
  const [error, setError] = useState('')

  useEffect(() => {
    setSheet(undefined); setError('')
    api.dispatchSheet(runId).then(setSheet).catch(e => setError(String(e.message ?? e)))
  }, [runId])

  if (error) return <p className="banner error">Cannot load dispatch sheet: {error}</p>
  if (sheet === undefined) return <p className="placeholder">Loading…</p>
  return sheet ? <Dispatch sheet={sheet} runId={runId} /> : <p className="placeholder">No dispatch sheet for this run.</p>
}
