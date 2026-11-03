import dashboardJson from './dashboard.json'
import type { Dashboard, Settings } from '../../types/api'
import { ApiError } from '../client'

export const dashboardFixture: Dashboard = dashboardJson
let settings: Settings = { default_username: 'octocat', theme: 'system' }

export async function mockRequest<T>(path: string, init?: RequestInit): Promise<T> {
  await new Promise<void>((resolve, reject) => {
    if (init?.signal?.aborted) return reject(new DOMException('Aborted', 'AbortError'))
    const timer = setTimeout(resolve, 350)
    init?.signal?.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')) }, { once: true })
  })
  if (path === '/settings') {
    if (init?.method === 'PUT') settings = JSON.parse(String(init.body)) as Settings
    return structuredClone(settings) as T
  }
  const url = new URL(path, 'http://fixture.local')
  const username = decodeURIComponent(url.pathname.split('/')[2] ?? '')
  if (!/^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/.test(username)) throw new ApiError({ code: 'invalid_input', message: 'Enter a valid GitHub username.', field: 'username' }, 422)
  if (username === 'not-found') throw new ApiError({ code: 'user_not_found', message: 'No GitHub user found. Check the username and try again.' }, 404)
  if (url.pathname.endsWith('/dashboard')) {
    const data = structuredClone(dashboardFixture)
    data.profile.login = username
    if (username === 'stale') data.meta = { ...data.meta, stale: true, warning: 'GitHub is temporarily unavailable. Showing the last saved portfolio.', error_code: 'github_unavailable' }
    if (username === 'empty') {
      data.languages = []
      data.contributions = { total: 0, start_date: null, end_date: null, weeks: [], months: [] }
      data.stats = { total_stars: 0, public_repos: 0, forked_repos: 0, archived_repos: 0, total_contributions: 0, current_streak: 0, longest_streak: 0, active_days: 0, best_day: null }
    }
    return data as T
  }
  throw new ApiError({ code: 'http_error', message: 'This preview endpoint is not available yet.' }, 404)
}
