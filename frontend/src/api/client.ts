import type { ApiErrorBody, ChatMessage, ChatResponse, Dashboard, GapCoach, MatchResponse, Repositories, RepoQuery, Settings } from '../types/api'

export const useMocks = import.meta.env.VITE_USE_MOCKS === 'true'

export class ApiError extends Error {
  readonly info: ApiErrorBody
  readonly status: number
  constructor(info: ApiErrorBody, status = 0) {
    super(info.message)
    this.name = 'ApiError'
    this.info = info
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (useMocks) {
    const { mockRequest } = await import('./fixtures/mock')
    return mockRequest<T>(path, init)
  }
  let response: Response
  try {
    response = await fetch(`/api${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError({ code: 'network_error', message: 'Could not reach the portfolio service. Check that the backend is running and try again.' })
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: ApiErrorBody } | null
    throw new ApiError(body?.error ?? { code: 'http_error', message: `Request failed (${response.status}). Please try again.` }, response.status)
  }
  return response.json() as Promise<T>
}

const userPath = (username: string) => `/users/${encodeURIComponent(username)}`
const post = (body: unknown, signal?: AbortSignal): RequestInit => ({ method: 'POST', body: JSON.stringify(body), signal })

export const api = {
  settings: (signal?: AbortSignal) => request<Settings>('/settings', { signal }),
  saveSettings: (settings: Settings, signal?: AbortSignal) => request<Settings>('/settings', { method: 'PUT', body: JSON.stringify(settings), signal }),
  dashboard: (username: string, refresh = false, signal?: AbortSignal) => request<Dashboard>(`${userPath(username)}/dashboard?refresh=${refresh}`, { signal }),
  repositories: (username: string, query: RepoQuery, signal?: AbortSignal) => {
    const params = new URLSearchParams({ sort: query.sort, language: query.language, include_forks: String(query.include_forks), page: String(query.page), page_size: String(query.page_size) })
    return request<Repositories>(`${userPath(username)}/repositories?${params}`, { signal })
  },
  match: (username: string, job_description: string, signal?: AbortSignal) => request<MatchResponse>(`${userPath(username)}/match`, post({ job_description }, signal)),
  coach: (username: string, job_description: string, signal?: AbortSignal) => request<GapCoach>(`${userPath(username)}/gap-coach`, post({ job_description }, signal)),
  chat: (username: string, message: string, history: ChatMessage[], signal?: AbortSignal) => request<ChatResponse>(`${userPath(username)}/chat`, post({ message, history }, signal)),
}
