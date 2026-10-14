// Thin fetch wrappers for DATABASE.md §11.2. Errors surface the API's {"detail"} text.
import type {
  DispatchSheet, GeoRecord, Health, Ladder, PostRunRequest, PostRunResponse, ReasonCards,
  RunDetail, RunsList, ScenarioInfo, StatusResponse, Table, TableName,
} from '../types'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, init)
  if (!r.ok) {
    const body = await r.json().catch(() => null)
    throw new Error(body?.detail ?? `${r.status} ${r.statusText}`)
  }
  return r.json() as Promise<T>
}

const e = encodeURIComponent

export const api = {
  health: () => req<Health>('/health'),
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
  postRun: (body: PostRunRequest) => req<PostRunResponse>('/runs', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }),
  status: (id: string) => req<StatusResponse>(`/runs/${e(id)}/status`),
}
