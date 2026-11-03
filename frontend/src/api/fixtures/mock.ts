import dashboardJson from './dashboard.json'
import type { Dashboard, MatchResponse, Settings } from '../../types/api'
import { ApiError } from '../client'
import { repositoryFixtures } from './repositories'
import { coachFixture, matchFixture, noKeywordsCoachFixture, noKeywordsFixture, zeroCoachFixture, zeroMatchFixture } from './career'

export const dashboardFixture: Dashboard = dashboardJson
let settings: Settings = { default_username: 'octocat', theme: 'system' }
const savedMatches: Record<string, MatchResponse> = {}

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
    if (savedMatches[username]) { data.match = savedMatches[username].match; data.job_description = savedMatches[username].job_description }
    if (username === 'stale') data.meta = { ...data.meta, stale: true, warning: 'GitHub is temporarily unavailable. Showing the last saved portfolio.', error_code: 'github_unavailable' }
    if (username === 'empty') {
      data.languages = []
      data.contributions = { total: 0, start_date: null, end_date: null, weeks: [], months: [] }
      data.stats = { total_stars: 0, public_repos: 0, forked_repos: 0, archived_repos: 0, total_contributions: 0, current_streak: 0, longest_streak: 0, active_days: 0, best_day: null }
    }
    return data as T
  }
  if (url.pathname.endsWith('/repositories')) {
    const key = `${url.searchParams.get('sort')}|${url.searchParams.get('language')}|${url.searchParams.get('include_forks')}|${url.searchParams.get('page')}`
    const data = structuredClone(repositoryFixtures[key] ?? repositoryFixtures['stars||false|1'])
    if (username === 'empty') { data.items = []; data.total = 0; data.total_pages = 0; data.available_languages = [] }
    if (username === 'stale') data.meta = { ...data.meta, stale: true, warning: 'GitHub is temporarily unavailable. Showing saved repositories.', error_code: 'github_unavailable' }
    return data as T
  }
  if (url.pathname.endsWith('/match') || url.pathname.endsWith('/gap-coach')) {
    const { job_description } = JSON.parse(String(init?.body)) as { job_description: string }
    const text = job_description.trim()
    if (!text) throw new ApiError({ code: 'invalid_input', message: 'Enter a job description before continuing.', field: 'job_description' }, 422)
    if (text.length > 20000) throw new ApiError({ code: 'payload_too_large', message: 'Job description must contain at most 20,000 characters.', field: 'job_description', max_chars: 20000 }, 413)
    const cases = { 'AWS Kubernetes': { match: noKeywordsFixture, coach: noKeywordsCoachFixture }, 'Java': { match: zeroMatchFixture, coach: zeroCoachFixture } }
    const fixture = cases[text as keyof typeof cases] ?? { match: matchFixture, coach: coachFixture }
    if (url.pathname.endsWith('/gap-coach')) return structuredClone(fixture.coach) as T
    const result: MatchResponse = { match: structuredClone(fixture.match), job_description: text, meta: structuredClone(dashboardFixture.meta) }
    savedMatches[username] = result
    return result as T
  }
  throw new ApiError({ code: 'http_error', message: 'This preview endpoint is not available yet.' }, 404)
}
