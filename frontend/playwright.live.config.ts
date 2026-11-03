import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.live.spec.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 10000 },
  outputDir: 'test-results/live',
  reporter: [['list'], ['json', { outputFile: 'test-results/live-report.json' }]],
  use: {
    baseURL: 'http://127.0.0.1:4174', browserName: 'chromium', channel: 'msedge',
    viewport: { width: 1440, height: 1000 }, trace: 'retain-on-failure',
  },
  webServer: {
    command: 'node tests/start-live-server.mjs', url: 'http://127.0.0.1:4174',
    reuseExistingServer: false, timeout: 30000,
  },
})
