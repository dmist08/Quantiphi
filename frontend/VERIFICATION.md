# Phase 4B verification — 2026-11-03

Scope was reduced to a five-minute finish: required changes, build/lint, fixture E2E tests, and one real-backend `dmist08` smoke test. No API responses were mocked or intercepted in the live smoke test. The live Vite server unsets `VITE_USE_MOCKS`, disables environment-file loading, and proxies `/api` to `http://127.0.0.1:8000`.

| Check | Result | Evidence / limit |
|---|---|---|
| Build | PASS | `npm run build` |
| Lint | PASS | `npm run lint` |
| Fixture E2E suite | PASS after targeted fix | Full run: 10 passed, new health error/retry test failed because its fixture counted an aborted Strict Mode request. Corrected fixture; targeted rerun: 1 passed. An initial JSON import failure was also fixed. No additional full run after those fixes. |
| Real dashboard / username search | PASS | Live browser loaded `dmist08` through the proxy; HTTP 200 and rendered name/handle matched the backend. |
| Real repo cards | PASS | Live cards and GitHub links rendered for `dmist08`. |
| Real JD match / badge | PASS | Submitted `Python TypeScript`; HTTP 200, badge and explanation matched the response. Original saved JD restored afterward with HTTP 200. |
| Real chat / improvement suggestion | PASS | Clicked “How can I improve my portfolio?”; HTTP 200, `portfolio_health` intent, exact server answer rendered. |
| Real Portfolio Health | PASS | HTTP 200; score, checks, top actions, and limitation matched the real backend. |
| Unset mock flag | PASS | Live browser imported the API client and asserted `useMocks === false`; no preview banner. |
| Health loading, API error/retry, no_repos, null score | PASS — fixtures only | No score calculation or null-to-zero coercion. These states were NOT RUN live. |
| Zero-percent language hiding | PASS — fixtures only | Pie and legend omit 0%; remaining 48% and 32% stay unchanged. NOT RUN against live language data. |
| Report/build metadata tracking | PASS | `test-results/`, `playwright-report/`, and `*.tsbuildinfo` are ignored. None tracked or staged. No source files removed. |
| Business-logic / plain-text source review | PASS | No frontend score, streak, percentage calculation, repository sorting/filtering, data pagination, or answer generation found. The sole data filter hides server-provided 0% languages as explicitly requested. No `dangerouslySetInnerHTML`. |
| Other live checks from the original checklist | NOT RUN | Invalid/unknown usernames, loading/retry, default loading/persistence, pie/heatmap/tooltips/labels/mobile scroll, repo controls/nulls/markers, JD empty/oversized/null/coach, typed/unknown chat/evidence/errors, stale warnings, theme persistence, keyboard, phone/desktop layouts, and adversarial text rendering were not exercised against the live backend in this smoke run. Existing fixture coverage does not count as a live pass. |

Known gaps: the broader live checklist above remains untested under the time limit. The previous dependency audit reported 12 moderate development-tooling advisories; audit was NOT RUN again in this phase. The live test restores an existing saved JD; if rerun on an account with no saved JD, the contract offers no endpoint for clearing the test JD.
