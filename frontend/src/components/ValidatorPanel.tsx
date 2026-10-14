// Independent validator output (validation.json, DATABASE §5.8), shown verbatim.
import type { Validation } from '../types'

export function ValidatorPanel({ validation }: { validation: Validation | null }) {
  return (
    <section>
      <h3>Independent validator</h3>
      {!validation ? <p>No validation.json for this run.</p> : (
        <>
          <p>Violation total: <strong>{validation.violation_total}</strong></p>
          {Object.keys(validation.counts ?? {}).length > 0 && (
            <table>
              <thead><tr><th>code</th><th>count</th></tr></thead>
              <tbody>
                {Object.entries(validation.counts).sort(([a], [b]) => a.localeCompare(b)).map(([c, n]) =>
                  <tr key={c}><td>{c}</td><td>{n}</td></tr>)}
              </tbody>
            </table>
          )}
          {(validation.warnings ?? []).length > 0 && (
            <>
              <h4>Warnings</h4>
              <table>
                <thead><tr><th>code</th><th>detail</th></tr></thead>
                <tbody>
                  {validation.warnings.map((w, i) => <tr key={i}><td>{w.code}</td><td>{w.detail}</td></tr>)}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </section>
  )
}
