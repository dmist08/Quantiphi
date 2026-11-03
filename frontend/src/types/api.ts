export interface ApiErrorBody {
  code: string
  message: string
  field?: string
  details?: { field: string; message: string }[]
  reset_at?: string | null
  max_chars?: number
}

export interface Meta {
  fetched_at: string
  stale: boolean
  warning: string | null
  notice: string | null
  error_code: string | null
  truncated: boolean
  rate_limit: { remaining: number | null; reset_at: string | null }
}

export interface Evidence { repo: string; url: string; language: string }
export interface MatchResult {
  status: 'ok' | 'no_assessable_keywords'
  score: number | null
  matched_count: number
  assessable_count: number
  matched: { name: string; accepted_languages: string[]; evidence: Evidence[] }[]
  missing: { name: string; accepted_languages: string[] }[]
  unassessable: string[]
  explanation: string
}
export interface ContributionDay { date: string; count: number; level: number }
export interface Dashboard {
  profile: {
    login: string; name: string | null; avatar_url: string | null
    bio: string | null; url: string | null; followers: number
  }
  stats: {
    total_stars: number; public_repos: number; forked_repos: number
    archived_repos: number; total_contributions: number; current_streak: number
    longest_streak: number; active_days: number; best_day: { date: string; count: number } | null
  }
  languages: { name: string; color: string | null; bytes: number; percent: number }[]
  contributions: {
    total: number; start_date: string | null; end_date: string | null
    weeks: (ContributionDay | null)[][]
    months: { label: string; week_index: number }[]
  }
  match: MatchResult | null
  job_description: string | null
  meta: Meta
}
export type RepoSort = 'stars' | 'forks' | 'updated' | 'name'
export interface RepoQuery { sort: RepoSort; language: string; include_forks: boolean; page: number; page_size: number }
export interface Repository {
  name: string; url: string; description: string | null; stars: number; forks: number
  language: string | null; language_color: string | null; is_fork: boolean
  is_archived: boolean; pushed_at: string | null
}
export interface Repositories {
  items: Repository[]; page: number; page_size: number; total: number; total_pages: number
  sort: RepoSort; language: string | null; include_forks: boolean; available_languages: string[]; meta: Meta
}
export interface MatchResponse { match: MatchResult; job_description: string; meta: Meta }
export interface GapCoach {
  status: MatchResult['status']; score: number | null
  strengths: { name: string; summary: string; evidence: Evidence[] }[]
  missing: string[]
  highlight_repos: { name: string; url: string; stars: number; matched_languages: string[]; reason: string }[]
  unassessable: string[]; pitch: string[]; disclaimer: string
}
export interface ChatMessage { role: 'user' | 'assistant'; content: string }
export interface ChatResponse {
  intent: string; answer: string
  evidence: { label: string; value: string; url: string | null }[]
  suggestions: string[]
}
export interface Settings { default_username: string | null; theme: 'light' | 'dark' | 'system' }
