import { expect, test, type Page } from '@playwright/test'
import dashboard from '../src/api/fixtures/dashboard.json' with { type: 'json' }
import { repositoryFixtures } from '../src/api/fixtures/repositories'
import { noKeywordsCoachFixture, noKeywordsFixture, zeroMatchFixture } from '../src/api/fixtures/career'
import { chatFixtures } from '../src/api/fixtures/chat'

test.beforeEach(async ({ page }) => {
  page.on('pageerror', error => console.error(`Browser error: ${error.message}`))
})

async function serveApi(page: Page, options: { theme?: string; defaultUsername?: string | null; stale?: boolean; empty?: boolean } = {}) {
  await page.route('https://fonts.googleapis.com/**', route => route.abort())
  await page.route('https://avatars.githubusercontent.com/**', route => route.abort())
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    if (!url.pathname.startsWith('/api/')) return route.continue()
    if (url.pathname === '/api/settings') return route.fulfill({ json: { default_username: options.defaultUsername === undefined ? 'octocat' : options.defaultUsername, theme: options.theme ?? 'light' } })
    if (url.pathname.endsWith('/dashboard')) {
      const data = structuredClone(dashboard)
      if (options.stale) data.meta = { ...data.meta, stale: true, warning: 'Rate limit reached. Showing cached data.', error_code: 'rate_limited' }
      if (options.empty) { data.languages = []; data.contributions.weeks = []; data.contributions.months = [] }
      return route.fulfill({ json: data })
    }
    if (url.pathname.endsWith('/repositories')) {
      const key = `${url.searchParams.get('sort')}|${url.searchParams.get('language')}|${url.searchParams.get('include_forks')}|${url.searchParams.get('page')}`
      return route.fulfill({ json: repositoryFixtures[key] ?? repositoryFixtures['stars||false|1'] })
    }
    return route.fulfill({ status: 404, json: { error: { code: 'http_error', message: 'No fixture for this request.' } } })
  })
}

test('loads default username, server stats, language percentages, and seven-row heatmap', async ({ page }) => {
  await serveApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'The Octocat' })).toBeVisible()
  await expect(page.getByLabel('GitHub username', { exact: true })).toHaveValue('octocat')
  await expect(page.getByText('48%', { exact: true })).toBeVisible()
  await expect(page.getByText('32%', { exact: true })).toBeVisible()
  await expect(page.locator('.recharts-pie-sector')).toHaveCount(3)
  await expect(page.getByLabel('2025-11-02: 0 contributions')).toBeVisible()
  await expect(page.locator('.calendar-week').first().locator('button, .calendar-padding')).toHaveCount(7)
  await page.getByLabel('2025-11-02: 0 contributions').focus()
  await expect(page.getByRole('tooltip', { name: '0 contributions on 2025-11-02' })).toBeVisible()
  await expect(page.locator('.match-badge')).toContainText('Your next chapter awaits')
  await expect(page.getByText('Preview mode')).toHaveCount(0)
  await page.getByRole('heading', { name: 'Your code. Your story.' }).click()
  await page.screenshot({ path: 'test-results/desktop.png', fullPage: true })
})

test('sends sort, language, fork, and pagination state to the repositories API', async ({ page }) => {
  await serveApi(page)
  await page.goto('/')
  const repos = page.locator('#repositories')
  await expect(repos.getByRole('link', { name: 'data-tools' })).toBeVisible()
  let request = page.waitForRequest(req => req.url().includes('/repositories?') && new URL(req.url()).searchParams.get('page') === '2')
  await repos.getByRole('button', { name: 'Next', exact: true }).click()
  await request
  await expect(repos.getByText('Page 2 of 2', { exact: false })).toBeVisible()
  request = page.waitForRequest(req => req.url().includes('/repositories?') && new URL(req.url()).searchParams.get('sort') === 'name')
  await page.getByLabel('Sort repositories').selectOption('name')
  const sorted = await request
  expect(new URL(sorted.url()).searchParams.get('page')).toBe('1')
  await expect(repos.getByRole('button', { name: 'Next', exact: true })).toBeEnabled()
  await page.getByLabel('Filter by language').selectOption('Python')
  await expect(repos.getByText('3 repositories', { exact: true })).toBeVisible()
  await expect(repos.getByRole('link', { name: 'ui-toolkit' })).toHaveCount(0)
  request = page.waitForRequest(req => req.url().includes('/repositories?') && new URL(req.url()).searchParams.get('include_forks') === 'true')
  await page.getByLabel('Include forks').check()
  const forks = await request
  expect(new URL(forks.url()).searchParams.get('language')).toBe('Python')
  expect(new URL(forks.url()).searchParams.get('page_size')).toBe('4')
})

test('renders validation, null match, real zero match, and gap coach from server responses', async ({ page }) => {
  await serveApi(page)
  await page.route('**/api/users/*/match', async route => {
    const text = route.request().postDataJSON().job_description
    if (!text) return route.fulfill({ status: 422, json: { error: { code: 'invalid_input', message: 'Job description is required.', field: 'job_description', details: [{ field: 'job_description', message: 'Cannot be blank.' }] } } })
    return route.fulfill({ json: { match: text === 'Java' ? zeroMatchFixture : noKeywordsFixture, job_description: text, meta: dashboard.meta } })
  })
  await page.route('**/api/users/*/gap-coach', route => route.fulfill({ json: noKeywordsCoachFixture }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Analyze match' }).click()
  await expect(page.getByRole('alert')).toContainText('Job description is required.')
  await expect(page.getByRole('alert')).toContainText('Cannot be blank.')
  await page.getByLabel('Job description', { exact: true }).fill('AWS Kubernetes')
  await page.getByRole('button', { name: 'Analyze match' }).click()
  await expect(page.locator('.match-badge')).toContainText('Not enough assessable keywords')
  await expect(page.locator('.match-score')).toHaveCount(0)
  await page.getByRole('button', { name: 'Get gap coaching' }).click()
  await expect(page.getByRole('heading', { name: 'Your gap coach' })).toBeVisible()
  await expect(page.locator('.coach-score')).toContainText('Not enough assessable keywords')
  await page.getByLabel('Job description', { exact: true }).fill('Java')
  await page.getByRole('button', { name: 'Analyze match' }).click()
  await expect(page.locator('.match-badge')).toContainText('0% match')
  await expect(page.locator('.match-score')).toHaveText('0%')
})

test('Portfolio Assistant sends history, renders evidence as text, and retries failures', async ({ page }) => {
  await serveApi(page)
  const bodies: { message: string; history: { role: string; content: string }[] }[] = []
  let fail = true
  await page.route('**/api/users/*/chat', async route => {
    const body = route.request().postDataJSON()
    bodies.push(body)
    if (body.message === 'fail' && fail) { fail = false; return route.fulfill({ status: 503, json: { error: { code: 'github_unavailable', message: 'Temporary assistant failure.' } } }) }
    return route.fulfill({ json: body.message === 'What are my top languages?' ? chatFixtures[body.message] : { intent: 'unknown', answer: '<b>Plain text answer</b>', evidence: [{ label: '<img src=x>', value: 'Evidence as text', url: null }], suggestions: ['Which are my best repos?'] } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'What are my top languages?' }).click()
  await expect(page.getByRole('log')).toContainText('Python (48%)')
  await page.getByText('View supporting evidence', { exact: true }).click()
  await expect(page.getByRole('log')).toContainText('48% · 120000 bytes')
  await page.getByLabel('Ask Portfolio Assistant').fill('fail')
  await page.getByRole('button', { name: 'Send message' }).click()
  await expect(page.getByRole('alert')).toContainText('Temporary assistant failure.')
  await page.getByRole('button', { name: 'Try again', exact: true }).click()
  await expect(page.getByRole('log')).toContainText('<b>Plain text answer</b>')
  expect(bodies[1].history).toHaveLength(2)
  expect(bodies[2].history).toEqual(bodies[1].history)
  await expect(page.locator('.chat-message.user')).toHaveCount(2)
  await expect(page.locator('.chat-message b')).toHaveCount(0)
  await page.getByRole('button', { name: 'Clear conversation' }).click()
  await expect(page.locator('.chat-message')).toHaveCount(0)
})

test('saves both settings fields, applies theme, and supports keyboard dismissal', async ({ page }) => {
  await serveApi(page)
  await page.route('**/api/settings', route => route.fulfill({ json: route.request().method() === 'PUT' ? route.request().postDataJSON() : { default_username: 'octocat', theme: 'light' } }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Open settings' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByLabel('Default GitHub username').fill('new-default')
  await page.getByRole('radio', { name: 'Dark', exact: true }).check()
  const request = page.waitForRequest(req => req.url().endsWith('/api/settings') && req.method() === 'PUT')
  await page.getByRole('button', { name: 'Save preferences' }).click()
  expect((await request).postDataJSON()).toEqual({ default_username: 'new-default', theme: 'dark' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await page.screenshot({ path: 'test-results/dark.png', fullPage: true })
  await page.getByRole('button', { name: 'Open settings' }).click()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
})

test('shows stale and empty states with no page overflow on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await serveApi(page, { stale: true, empty: true })
  await page.goto('/')
  await expect(page.getByText('Rate limit reached. Showing cached data.')).toBeVisible()
  await expect(page.getByText('No public language data yet.')).toBeVisible()
  await expect(page.getByText('No contribution activity to display yet.')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.getByRole('button', { name: 'Open settings' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
})

test('starts with search when no default exists and reports server username errors', async ({ page }) => {
  await serveApi(page, { defaultUsername: null })
  await page.route('**/api/users/missing/dashboard?*', route => route.fulfill({ status: 404, json: { error: { code: 'user_not_found', message: 'This GitHub user does not exist.' } } }))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Your portfolio starts here' })).toBeVisible()
  await page.getByLabel('GitHub username', { exact: true }).fill('missing')
  await page.getByRole('button', { name: 'Load GitHub portfolio' }).click()
  await expect(page.getByRole('alert')).toContainText('This GitHub user does not exist.')
  await expect(page.locator('.profile-panel')).toHaveCount(0)
})

test('keeps the full heatmap scrollable inside a narrow mobile layout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await serveApi(page)
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'The Octocat' })).toBeVisible()
  const calendar = page.getByRole('region', { name: 'Contribution calendar. Scroll horizontally to explore all weeks.' })
  expect(await calendar.evaluate(element => element.scrollWidth > element.clientWidth)).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/mobile.png', fullPage: true })
  await page.setViewportSize({ width: 320, height: 740 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})
