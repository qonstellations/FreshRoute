// Trust tab (ARCHITECTURE §16): assumptions, cost-model coefficients (GET /api/config), run_manifest.json.
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { ConfigConstants, RunDetail } from '../types'

const show = (v: unknown) => (typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v))

export function Trust({ run }: { run: RunDetail }) {
  const [config, setConfig] = useState<ConfigConstants | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.config().then(setConfig).catch(e => setError(String(e.message ?? e))) }, [])
  const m = run.manifest

  return (
    <>
      <section>
        <h3>Assumptions</h3>
        <p>Every modelling assumption (A-01, A-02, …) and its status (confirm / team) is logged in{' '}
          <code>docs/ARCHITECTURE.md §20</code> (Assumption log). Team-chosen constants below are tagged there and in{' '}
          <code>§19</code>.</p>
      </section>

      <section>
        <h3>Coefficients (<code>config.py</code>)</h3>
        <p className="caption">Served verbatim by <code>GET /api/config</code>. Per-commodity prices, costs and
          shelf lives come from the scenario tables, not from code.</p>
        {error && <p className="placeholder">Cannot load config: {error}</p>}
        {config && (
          <table>
            <thead><tr><th>constant</th><th>value</th></tr></thead>
            <tbody>
              {Object.entries(config).map(([k, v]) => <tr key={k}><td><code>{k}</code></td><td>{show(v)}</td></tr>)}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h3>Run manifest</h3>
        {!m ? <p className="placeholder">No run_manifest.json for this run.</p> : (
          <>
            <table>
              <tbody>
                {([['run_id', m.run_id], ['seed', m.seed], ['realization', m.realization], ['policy', m.policy],
                  ['flags', m.flags], ['git SHA', m.git_sha], ['scenario', m.scenario],
                  ['scenario sha256', m.scenario_sha256], ['timestamp (UTC)', m.timestamp_utc],
                  ['solver status', m.solver?.status ?? 'n/a (no solver)'], ['MIP gap', m.solver?.mip_gap ?? 'n/a'],
                  ['solve seconds', m.solver?.solve_seconds ?? 'n/a'], ['fallback used', m.solver?.fallback_used ?? 'n/a'],
                  ['slack usage', m.solver?.slack_usage ?? 'n/a'],
                ] as [string, unknown][]).map(([k, v]) => <tr key={k}><th>{k}</th><td>{show(v)}</td></tr>)}
              </tbody>
            </table>
            <h4>Package versions</h4>
            <table>
              <tbody>
                {Object.entries(m.package_versions ?? {}).map(([k, v]) => <tr key={k}><th>{k}</th><td>{v}</td></tr>)}
              </tbody>
            </table>
          </>
        )}
      </section>
    </>
  )
}
