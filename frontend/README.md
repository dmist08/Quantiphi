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

```powershell
npm run build
npm run lint
```

All calculations, repository ordering, filtering, and pagination belong to the API. The UI renders server-provided values. User content is rendered as text.
