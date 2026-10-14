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
  // a 404 with a specific detail = not on disk yet (the UI shows the CLI hint)
  stress: (scenario: string, seed: number) =>
    req<StressResponse>(`/stress?scenario=${e(scenario)}&seed=${seed}`),
  postStress: (body: PostStressRequest) => req<PostRunResponse>('/stress', post(body)),
  sensitivity: (scenario: string, seed: number) =>
    req<SensitivityResponse>(`/sensitivity?scenario=${e(scenario)}&seed=${seed}`),
  postReplan: (body: PostReplanRequest) => req<PostReplanResponse>('/replan', post(body)),
  replanResult: (runId: string, eventId: string) =>
    req<ReplanResult>(`/runs/${e(runId)}/replan/${e(eventId)}`),
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
    const s = await api.status(`${runId}__replan__${eventId}`).catch(() => null)
    if (s?.state === 'error') throw new Error(`replan ${eventId} failed: ${s.error ?? 'unknown error'}`)
    try { return await api.replanResult(runId, eventId) } catch (err) { if (!notOnDisk(err)) throw err }
  }
  throw new Error(`replan ${eventId}: no result after ${POLL_MAX} polls`)
}
