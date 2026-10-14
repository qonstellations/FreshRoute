// Thin fetch wrappers for DATABASE.md §11.2. Errors surface the API's {"detail"} text.
import type {
  ConfigConstants, DispatchSheet, GeoRecord, Health, Ladder, PostReplanRequest, PostReplanResponse, PostRunRequest,
  PostRunResponse, PostStressRequest, ReasonCards, ReplanResult, RunDetail, RunsList, ScenarioInfo, SensitivityResponse,
  StatusResponse, StressResponse, Table, TableName,
} from '../types'

/** Non-2xx response; `detail` is the API's {"detail"} text when it sent one. */
export class HttpError extends Error {
  constructor(readonly status: number, readonly detail: string | undefined, statusText: string) {
    super(detail ?? `${status} ${statusText}`)
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, init)
  if (!r.ok) {
    const body = await r.json().catch(() => null)
    throw new HttpError(r.status, typeof body?.detail === 'string' ? body.detail : undefined, r.statusText)
  }
  return r.json() as Promise<T>
}

const e = encodeURIComponent
const post = (body: unknown): RequestInit => ({
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
})

export const api = {
  health: () => req<Health>('/health'),
  config: () => req<ConfigConstants>('/config'),
  scenarios: () => req<ScenarioInfo[]>('/scenarios'),
  geo: (name: string) => req<GeoRecord[]>(`/scenarios/${e(name)}/geo`),
  runs: () => req<RunsList>('/runs'),
  run: (id: string) => req<RunDetail>(`/runs/${e(id)}`),
  table: (id: string, t: TableName) => req<Table>(`/runs/${e(id)}/tables/${t}`),
  tableCsvUrl: (id: string, t: TableName) => `/api/runs/${e(id)}/tables/${t}?format=csv`,
  reasonCards: (id: string) => req<ReasonCards>(`/runs/${e(id)}/reason-cards`),
  dispatchSheet: (id: string) => req<DispatchSheet | null>(`/runs/${e(id)}/dispatch-sheet`),
  ladder: (scenario: string, seed: number) =>
    req<Ladder>(`/ladder?scenario=${e(scenario)}&seed=${seed}`),
  postRun: (body: PostRunRequest) => req<PostRunResponse>('/runs', post(body)),
  status: (id: string) => req<StatusResponse>(`/runs/${e(id)}/status`),
  // AD-05 / AD-06: a 404 with a specific detail = not on disk yet (the UI shows the CLI hint)
  stress: (scenario: string, seed: number) => orExample(
    req<StressResponse>(`/stress?scenario=${e(scenario)}&seed=${seed}`), exampleStress),
  postStress: (body: PostStressRequest) => req<PostRunResponse>('/stress', post(body)),
  sensitivity: (scenario: string, seed: number) => orExample(
    req<SensitivityResponse>(`/sensitivity?scenario=${e(scenario)}&seed=${seed}`), exampleSensitivity),
  postReplan: (body: PostReplanRequest) => orExample(
    req<PostReplanResponse>('/replan', post(body)),
    () => ({ run_id: body.run_id, event_id: body.event.event_id, status: 'running' as const })),
  replanResult: (runId: string, eventId: string) => orExample(
    req<ReplanResult>(`/runs/${e(runId)}/replan/${e(eventId)}`), exampleReplan),
}

/** True when the error is "no such file on disk" (a live endpoint's 404), as opposed to a transport failure. */
export const notOnDisk = (err: unknown) => err instanceof HttpError && err.status === 404

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))
// ponytail: fixed 1 s poll like RunButton; 10 min ceiling so a dead worker cannot spin forever
const POLL_MS = 1000, POLL_MAX = 600

/** Poll GET /api/runs/{id}/status until done; throws the job's error. */
export async function waitDone(runId: string): Promise<void> {
  for (let i = 0; i < POLL_MAX; i++) {
    await sleep(POLL_MS)
    const s = await api.status(runId)
    if (s.state === 'done') return
    if (s.state === 'error') throw new Error(`${runId} failed: ${s.error ?? 'unknown error'}`)
  }
  throw new Error(`${runId}: still running after ${POLL_MAX} polls`)
}

/** Poll a replan: the job status for errors, the result endpoint (404 until written) for the diff. */
export async function waitReplan(runId: string, eventId: string): Promise<ReplanResult> {
  for (let i = 0; i < POLL_MAX; i++) {
    await sleep(POLL_MS)
    const s = await api.status(runId).catch(() => null)
    if (s?.state === 'error') throw new Error(`replan ${eventId} failed: ${s.error ?? 'unknown error'}`)
    try { return await api.replanResult(runId, eventId) } catch (err) { if (!notOnDisk(err)) throw err }
  }
  throw new Error(`replan ${eventId}: no result after ${POLL_MAX} polls`)
}

// ---- STUB (AD-05/AD-06 dev only) -------------------------------------------------------------
// The stress / sensitivity / replan endpoints do not exist yet. When the ROUTE itself is missing
// (FastAPI's generic 404/405, or the SPA's static 404, i.e. no specific detail) these calls fall back
// to the committed format-example fixtures, marked `example: true` so the tabs show the
// "format example, not measured" banner. Delete this block and the `orExample(...)` wrappers above
// once the live endpoints land. Numbers come verbatim from the fixture files.
import stressJson from '../../../backend/tests/fixtures/stress_summary_example.json?raw'
import sensitivityCsv from '../../../backend/tests/fixtures/sensitivity_example.csv?raw'
import diffJson from '../../../backend/tests/fixtures/diff_example.json?raw'

const missingRoute = (err: unknown) => err instanceof HttpError && (err.status === 404 || err.status === 405)
  && (err.detail === undefined || err.detail === 'Not Found' || err.detail === 'Method Not Allowed')

async function orExample<T>(p: Promise<T>, example: () => T): Promise<T> {
  try { return await p } catch (err) { if (missingRoute(err)) return example(); throw err }
}

function exampleStress(): StressResponse {
  return { summary: JSON.parse(stressJson), rows: null, example: true }
}

function exampleSensitivity(): SensitivityResponse {
  const [head, ...lines] = sensitivityCsv.trim().split(/\r?\n/)
  const cols = head.split(',')
  const records = lines.map(l => Object.fromEntries(l.split(',').map((v, i) =>
    [cols[i], cols[i] === 'parameter' || cols[i] === 'policy' ? v : Number(v)])))
  return { records: records as unknown as SensitivityResponse['records'], example: true }
}

function exampleReplan(): ReplanResult {
  return {
    diff: JSON.parse(diffJson), example: true,
    narration: 'Format example: the server narrates diff.json here (narrator.template_narration) once POST /api/replan lands.',
  }
}
// ---- end STUB ----------------------------------------------------------------------------------
