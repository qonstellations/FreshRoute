// Dashboard shell (ARCHITECTURE §16): sidebar (run picker, run form) + five tabs. Renders API JSON verbatim.
import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client'
import { StatusBanner, SyntheticBanner } from './components/Banners'
import { RunButton } from './components/RunButton'
import { RunPicker } from './components/RunPicker'
import { Plan } from './tabs/Plan'
import { Replan } from './tabs/Replan'
import { Robustness } from './tabs/Robustness'
import { Scoreboard } from './tabs/Scoreboard'
import { Trust } from './tabs/Trust'
import type { RunDetail, RunsList, ScenarioInfo } from './types'

const TABS = { Scoreboard, Plan, Robustness, Replan, Trust }
type TabName = keyof typeof TABS
const POLICIES = ['fifo', 'fefo', 'last_day_50', 'milp', 'milp_markdown']
// ponytail: run_id of backend/tests/fixtures/metrics_example.json, used when /api/runs is empty + fixture
const FIXTURE_RUN_ID = 'EXAMPLE-SYNTHETIC'

export default function App() {
  const [tab, setTab] = useState<TabName>('Scoreboard')
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [runs, setRuns] = useState<RunsList>({ runs: [], fixture: false })
  const [runId, setRunId] = useState<string | null>(null)
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState('')
  const [scenario, setScenario] = useState('')
  const [policy, setPolicy] = useState('milp_markdown')
  const [seed, setSeed] = useState(42)
  const [markdown, setMarkdown] = useState(true)
  const [newsvendor, setNewsvendor] = useState(false)

  const loadRuns = useCallback(async (select?: string) => {
    try {
      const r = await api.runs()
      setRuns(r)
      setRunId(select ?? r.runs[0]?.run_id ?? (r.fixture ? FIXTURE_RUN_ID : null))
    } catch (e) { setError(`Cannot list runs: ${e instanceof Error ? e.message : e}`) }
  }, [])

  useEffect(() => {
    api.scenarios().then(s => { setScenarios(s); setScenario(v => v || s[0]?.name || '') })
      .catch(e => setError(`Cannot list scenarios: ${e.message}`))
    loadRuns()
  }, [loadRuns])

  useEffect(() => {
    if (!runId) return setRun(null)
    api.run(runId).then(setRun).catch(e => setError(`Cannot load run ${runId}: ${e.message}`))
  }, [runId])

  const fixture = runs.fixture || !!run?.fixture
  const info = run && scenarios.find(s => s.name === run.scenario || run.scenario.endsWith(`/${s.name}`))
  const Tab = TABS[tab]

  return (
    <div className="layout">
      <aside>
        <h1>FreshRoute</h1>
        <RunPicker runs={runs.runs} value={runId} onChange={setRunId} />
        <hr />
        <label>Scenario
          <select value={scenario} onChange={e => setScenario(e.target.value)}>
            {scenarios.map(s => <option key={s.name} value={s.name}>{s.name} ({s.source})</option>)}
          </select>
        </label>
        <label>Policy
          <select value={policy} onChange={e => setPolicy(e.target.value)}>
            {POLICIES.map(p => <option key={p}>{p}</option>)}
          </select>
        </label>
        <label>Seed
          <input type="number" value={seed} onChange={e => setSeed(Number(e.target.value))} />
        </label>
        <label className="check">
          <input type="checkbox" checked={markdown} onChange={e => setMarkdown(e.target.checked)} /> markdown
        </label>
        <label className="check">
          <input type="checkbox" checked={newsvendor} onChange={e => setNewsvendor(e.target.checked)} /> newsvendor
        </label>
        <RunButton
          request={{ scenario: scenario && `data/scenarios/${scenario}`, policy, seed, flags: { markdown, newsvendor } }}
          onDone={id => loadRuns(id)} onError={setError} />
      </aside>
      <main>
        {/* shown unless the run's scenario is a listed one with a non-synthetic source (§16.1) */}
        <SyntheticBanner show={fixture || (!!run && (!info || info.source === 'synthetic'))} />
        <StatusBanner fixture={fixture} manifest={run?.manifest ?? null} error={error} />
        <nav className="tabs">
          {(Object.keys(TABS) as TabName[]).map(t =>
            <button key={t} className={t === tab ? 'active' : ''} onClick={() => setTab(t)}>{t}</button>)}
        </nav>
        {run ? <Tab run={run} /> : <p className="placeholder">No run loaded.</p>}
      </main>
    </div>
  )
}
