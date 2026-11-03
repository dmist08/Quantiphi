import { expect, test } from '@playwright/test'
import type { ChatResponse, Dashboard, MatchResponse, PortfolioHealth } from '../src/types/api'

test('LIVE SMOKE: dmist08 dashboard, repositories, JD match, chat, and Portfolio Health', async ({ page, request }) => {
  // All /api requests reach the real backend through the Vite proxy.
  const initial = await request.get('/api/users/dmist08/dashboard')
  expect(initial.status()).toBe(200)
  const original: Dashboard = await initial.json()
  await page.goto('/')
  await page.getByLabel('GitHub username', { exact: true }).fill('dmist08')
  const dashboardResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/users/dmist08/dashboard')
  await page.getByRole('button', { name: 'Load GitHub portfolio' }).click()
  expect((await dashboardResponse).status()).toBe(200)
  await expect(page.locator('.handle')).toHaveText('@dmist08')
  await expect(page.locator('#profile-name')).toHaveText(original.profile.name ?? original.profile.login)
  await expect(page.getByLabel('Sort repositories')).toBeEnabled()
  expect(await page.locator('.repo-card').count()).toBeGreaterThan(0)
  await expect(page.locator('.repo-title a').first()).toHaveAttribute('href', /https:\/\/github.com\/dmist08\//)
  await expect(page.locator('.preview-banner')).toHaveCount(0)
  expect(await page.evaluate(async () => (await import('/src/api/client.ts')).useMocks)).toBe(false)
  try {
    await page.getByLabel('Job description', { exact: true }).fill('Python TypeScript')
    const matchResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/users/dmist08/match')
    await page.getByRole('button', { name: 'Analyze match' }).click()
    const response = await matchResponse
    expect(response.status()).toBe(200)
    const match: MatchResponse = await response.json()
    await expect(page.locator('.match-badge')).toContainText(`${match.match.score}% match`)
    await expect(page.locator('.score-explanation')).toHaveText(match.match.explanation)
    const chatResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/users/dmist08/chat')
    await page.getByRole('button', { name: 'How can I improve my portfolio?' }).click()
    const chat = await chatResponse
    expect(chat.status()).toBe(200)
    const answer: ChatResponse = await chat.json()
    expect(answer.intent).toBe('portfolio_health')
    await expect(page.locator('.chat-message.assistant').last().locator('p')).toHaveText(answer.answer)
    const healthResponse = await request.get('/api/users/dmist08/portfolio-health')
    expect(healthResponse.status()).toBe(200)
    const health: PortfolioHealth = await healthResponse.json()
    const panel = page.locator('#portfolio-health')
    await expect(panel.getByLabel(`Portfolio health: ${health.score} out of ${health.max_score}`, { exact: true })).toBeVisible()
    await expect(panel.locator('.health-check h3')).toHaveText(health.checks.map(check => check.label))
    await expect(panel.locator('.health-actions li span')).toHaveText(health.top_actions)
    await expect(panel.locator('.health-limitation')).toHaveText(health.limitation)
  } finally {
    if (original.job_description !== null) {
      const restored = await request.post('/api/users/dmist08/match', { data: { job_description: original.job_description } })
      expect(restored.status()).toBe(200)
    }
  }
})
