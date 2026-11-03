# Gitfolio frontend

React, Vite, TypeScript, and Recharts. Requires Node.js 20.19+ or 22.12+.

```powershell
cd frontend
npm install
npm run dev
```

The default is the real API. Vite proxies `/api` to `http://127.0.0.1:8000`.
Keep the backend running on port 8000. No token belongs in the frontend.

For an isolated fixture preview in PowerShell:

```powershell
$env:VITE_USE_MOCKS = "true"
npm run dev
```

Only the exact string `true` enables fixtures. To return to the real API, remove that environment variable and restart Vite. Sample usernames `empty`, `stale`, and `not-found` exercise the corresponding states. Fixtures are separate from production components in `src/api/fixtures/` and never supply fallback data for real API failures.

Fixture career results are fixed snapshots: enter `AWS Kubernetes` for no assessable keywords, `Java` for a real 0% result, or another nonempty description for the sample 67% result. Repository query combinations have prewritten response snapshots. Suggested Portfolio Assistant questions have prewritten answers; `error` exercises chat failure. Mock settings and saved descriptions last for the current browser session until a page reload. No matching, ranking, or answer generation runs in production components or fixture adapters.

```powershell
npm run build
npm run lint
npm run test:e2e
```

All calculations, repository ordering, filtering, and pagination belong to the API. The UI renders server-provided values. User content is rendered as text.

Browser tests use Microsoft Edge, start Vite on port 4173 with mocks disabled, and intercept only HTTP API endpoints with contract-shaped responses. They cover default loading, contribution labels, query parameters, server validation, null versus zero scores, coaching, chat history and retry, plain-text rendering, settings, and mobile scrolling. A listening backend is required for a live integration check.
