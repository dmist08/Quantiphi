import type { PortfolioHealth } from '../../types/api'
import dashboard from './dashboard.json' with { type: 'json' }

export const healthFixture: PortfolioHealth = {
  status: 'ok', score: 100, max_score: 100,
  checks: [
    { key: 'descriptions', label: 'Repository descriptions', score: 25, max_score: 25, detail: '7 of 7 active original repos have a description.', suggestion: null },
    { key: 'recent_projects', label: 'Recently updated projects', score: 25, max_score: 25, detail: '7 of 7 active original repos were pushed in the last 180 days.', suggestion: null },
    { key: 'consistency', label: 'Contribution consistency', score: 25, max_score: 25, detail: '254 active contribution days in the last year (100 earns full points).', suggestion: null },
    { key: 'profile', label: 'Profile completeness', score: 25, max_score: 25, detail: 'Bio present; 8 original repos (3 needed).', suggestion: null },
  ],
  top_actions: [],
  limitation: 'This measures how your public profile is presented and how active it is, not code quality or skill.',
  as_of: '2026-11-03', meta: dashboard.meta,
}

export const noReposHealthFixture: PortfolioHealth = {
  status: 'no_repos', score: null, max_score: 100, checks: [],
  top_actions: ['Publish an original (non-fork) public repository so there is something to evaluate.'],
  limitation: healthFixture.limitation, as_of: '2026-11-03', meta: dashboard.meta,
}
