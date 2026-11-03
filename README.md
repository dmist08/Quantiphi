# GitHub Developer Portfolio

A local dashboard that turns a GitHub account into a personal branding page: profile header with a Top
Languages chart, a contribution heatmap with streaks, repository cards, a **Tech Stack Compatibility** score
against a job description, a JD gap coach, a Portfolio Health check and the Portfolio Assistant, a rule-based
chatbot.

All business logic (statistics, streaks, language percentages, scoring, validation, sorting, filtering and
pagination) runs on the server. The React frontend only renders what the API returns.

> Screenshots: _placeholder — add `docs/screenshots/dashboard.png`, `docs/screenshots/jd-panel.png` and
> `docs/screenshots/chat.png` here._

---

## Architecture

```
Browser (React + Vite + TypeScript + Recharts)
   │  relative calls to /api/...
   ▼
Vite dev server :5173 ── proxy /api ──► FastAPI :8000
                                          │
                     routers/  (HTTP only: parse, validate, call services)
                       dashboard.py  dashboard, repositories, portfolio-health
                       match.py      match, gap-coach
                       chat.py       chatbot
                       settings.py   settings
                                          │
                     services/ (all logic, mostly pure functions)
                       github_client.py   GraphQL fetch + error mapping
                       cache_service.py   SQLite cache, TTL, locks, stale fallback
                       stats.py           streaks, languages, heatmap grid, repo listing
                       matcher.py         keyword taxonomy + score
                       gap_coach.py       deterministic JD advice
                       portfolio_health.py presentation/activity checks
                       chatbot.py         keyword-intent answers
                                          │
                     SQLite (WAL)  ◄──────┘        GitHub GraphQL API
```

```
backend/
  app/main.py        app factory (create_app), router registration, /api/health
  app/config.py      settings from the environment (backend/.env)
  app/db.py          schema, connections, BEGIN IMMEDIATE transactions
  app/schemas.py     request models, username/text validation
  app/errors.py      error classes + handlers for the {"error": {...}} shape
  app/routers/       thin HTTP layer
  app/services/      business logic
  tests/             pytest suite (GitHub is always mocked)
frontend/src/        api client, components, shared types
docs/API_CONTRACT.md the exact request/response contract between the two halves
```

**Design choices**

- **GraphQL, one round-trip per page.** Profile, contribution calendar, repositories (with top 10 languages each)
  and rate limit come back in a single query; extra repo pages reuse a smaller query.
- **Pure service functions.** `stats`, `matcher`, `gap_coach`, `portfolio_health` and `chatbot` take plain dicts
  and return plain dicts, so they're tested without HTTP or a database.
- **Dependency injection for tests.** `create_app(settings, github_client)` accepts a fake GitHub client; the cache
  takes an injectable clock; portfolio health takes an injectable `today`.

---

## Setup

Requirements: Python 3.11+, Node.js 18+ and a GitHub personal access token (public read access is enough).

### Backend

```bash
cd backend
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example .env        # then set GITHUB_TOKEN in backend/.env
uvicorn app.main:create_app --factory --reload --port 8000
```

`backend/.env` is git-ignored. Without a token the API still starts and serves anything already cached, and
uncached users return a 401 that explains how to set the token.

| Variable | Default | Purpose |
|----------|---------|---------|
| `GITHUB_TOKEN` | — | Required to fetch data from GitHub |
| `DATABASE_PATH` | `portfolio_cache.db` | SQLite file (relative to `backend/`) |
| `CACHE_TTL_SECONDS` | `3600` | Cache lifetime |
| `REFRESH_MIN_INTERVAL_SECONDS` | `60` | Minimum time between forced refreshes |

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to http://127.0.0.1:8000
```

`npm run build` type-checks and builds; `npm run lint` runs ESLint; `npm run test:e2e` runs the Playwright
tests (they start their own Vite server on port 4173).

### Tests

```bash
cd backend
python -m pytest -q
```

---

## API

Full request/response shapes, nullability and error codes: **[docs/API_CONTRACT.md](docs/API_CONTRACT.md)**.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness + whether a GitHub token is configured |
| GET | `/api/users/{username}/dashboard?refresh=false` | Profile, stats, streaks, languages, heatmap, saved JD match, cache meta |
| GET | `/api/users/{username}/repositories?sort=stars\|forks\|updated\|name&language=&include_forks=false&page=1&page_size=12` | Server-side sorted/filtered/paginated repo cards |
| POST | `/api/users/{username}/match` | `{job_description}` → match score; saves it as the user's latest JD |
| POST | `/api/users/{username}/gap-coach` | `{job_description}` → strengths, gaps, repos to highlight, honest pitch |
| GET | `/api/users/{username}/portfolio-health` | Presentation/activity score with suggestions (cached data only) |
| POST | `/api/users/{username}/chat` | `{message, history}` → `{intent, answer, evidence, suggestions}` (cached data only) |
| GET / PUT | `/api/settings` | `default_username` and `theme` (`light` / `dark` / `system`) |

Every error has the same shape:

```json
{ "error": { "code": "rate_limited", "message": "GitHub API rate limit exceeded.", "reset_at": "..." } }
```

| Status | Code | When |
|--------|------|------|
| 422 | `invalid_input` | Invalid username (`^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$`), empty text, bad query |
| 413 | `payload_too_large` | JD over 20,000 characters, chat message over 2,000 (after trimming) |
| 404 | `user_not_found` | No such user, or the login is an organization |
| 404 | `not_cached` | Chat/portfolio-health for a user whose dashboard was never loaded |
| 401 | `github_auth` | `GITHUB_TOKEN` missing or rejected (message explains the setup) |
| 429 | `rate_limited` | GitHub rate limit and nothing cached (includes `reset_at`) |
| 503 | `github_unavailable` | GitHub down, timeout, or GraphQL error, and nothing cached |

---

## Scoring

### Tech Stack Compatibility (match badge)

1. The JD is trimmed (empty → 422, over 20,000 characters → 413).
2. A **transparent taxonomy** in `services/matcher.py` maps each keyword and alias to the GitHub languages that count
   as evidence, for example `python/py → Python or Jupyter Notebook`, `react/next.js/vue/node.js → JavaScript or
   TypeScript`, `angular → TypeScript`, `spring → Java`, `c#/.net → C#`, `golang → Go`, `terraform → HCL`,
   `docker → Dockerfile`, `sql → SQL or PLpgSQL`.
3. Each technology counts **once**, however often it is repeated.
4. A technology is **matched** when at least one owned, non-fork repo contains code in an accepted language. The
   evidence is up to 3 such repos, largest byte count first.
5. Recognized technologies that languages can't prove (AWS, Azure, GCP, Kubernetes, Kafka, Redis, Linux, Git,
   CI/CD, PostgreSQL, ...) are listed as **unassessable** and excluded from the score.

```
score = round(100 × matched assessable technologies / total assessable technologies)
```

If the JD has no assessable technology, the result is `score = null` with `status = "no_assessable_keywords"`,
never 0%. Only the latest JD per user is stored, and the dashboard recomputes the badge from it on every
response, so it always reflects the current cached repositories.

**Keyword boundaries** (all covered by tests):

| Input | Result |
|-------|--------|
| `JavaScript` | JavaScript only, not Java |
| `scalable` | not Scala |
| `C, C++ and C#` / `C/C++` | three / two distinct technologies |
| `R&D` | not R |
| `C-level`, `C-suite` | not C |
| `go above and beyond` | not Go. `Go` counts only as `golang`, or capitalized next to a list comma, slash, parenthesis, sentence end, `and/or <Capitalized>`, or words like *developer, programming, language, backend* |
| `Python/Java` | split into Python and Java |

### Statistics

- **Total stars, top languages and matching exclude forks.** Forks appear in the repo list only with
  `include_forks=true`.
- **Top languages**: total bytes per language across owned non-fork repos. Top 5 plus `Other`. Integer
  percentages use the largest-remainder method, so they always sum to exactly 100.
- **Contribution levels**: GitHub's `contributionLevel` maps to 0–4 (`NONE`=0 … `FOURTH_QUARTILE`=4). The
  server groups days into Sunday-first weeks of 7 slots, with `null` padding.
- **Streaks**: the longest run of days with at least one contribution. The current streak ends at the most
  recent day; if that day has 0 contributions (the user may not have committed *yet* today), counting starts
  from the previous day. Active days and the best day are also returned.

### Portfolio health (0–100)

Four checks worth 25 points each. "Original" means owned and not a fork; "active" means original and not
archived.

| Check | Points |
|-------|--------|
| Descriptions | 25 × share of active original repos with a non-empty description |
| Recent projects | 25 × share of active original repos pushed in the last 180 days (inclusive) |
| Consistency | 25 × min(active contribution days / 100, 1) |
| Profile | 12.5 for a non-empty bio + 12.5 for at least 3 original repos |

The response includes per-check details, a suggestion for each check below full points, and up to 3 top
actions (largest deficit first). With no original repos the score is `null` (`status = "no_repos"`). If every
original repo is archived, the two repo checks score 0, with no division by zero. It measures public profile
presentation and activity, **not code quality or skill**, and says so in every response.

---

## Cache behavior

- **SQLite tables**: `users`, `repositories`, `repo_languages`, `contribution_days`, `settings` and `jd_inputs`.
  WAL mode, foreign keys on, parameterized SQL only.
- **Keys**: usernames are validated, then lowercased for the cache key. The display uses GitHub's original
  casing (`OctoCat` and `octocat` share one cache entry).
- **TTL**: data younger than 1 hour is served without calling GitHub.
- **`refresh=true`** bypasses the TTL only if the last successful fetch is at least 60 seconds old. Otherwise
  cached data is returned with `meta.notice` explaining when the next refresh is allowed.
- **No duplicate fetches**: a per-username `asyncio.Lock` makes concurrent requests for the same user wait for
  one fetch. The cache is re-checked after acquiring the lock.
- **Atomic replace**: a refresh deletes and re-inserts the user's repos, languages and days inside one
  `BEGIN IMMEDIATE` transaction. Repos deleted on GitHub disappear, and a failed refresh leaves the old data
  untouched.
- **Stale fallback**: if a refresh fails (network, 5xx, GraphQL error, rate limit, token problem) and cached
  data exists, it is returned with `meta.stale = true`, `meta.fetched_at`, `meta.warning` and
  `meta.error_code`. Without cached data the error is returned (401/429/503). "User not found" is never masked
  by the cache.
- **GitHub client**: 10-second timeout and one retry for network errors or 5xx. 401/403/429 are never retried.
  An HTTP 200 response with a GraphQL `errors` array is always treated as a failure. Repositories:
  `privacy: PUBLIC`, `ownerAffiliations: OWNER`, ordered by stars, 100 per page, capped at 5 pages; if more
  exist, `meta.truncated = true`.
- **Cached-only features**: the chatbot and portfolio health never call GitHub.

---

## Edge cases handled

- No repositories, forks only, or every repo archived.
- Null descriptions, null primary language, repos with no language data.
- Zero contributions all year (streaks 0, `best_day` null), and a zero-contribution "today".
- Organization logins and unknown users (404), invalid usernames (422, no GitHub call).
- GraphQL errors inside HTTP 200 responses, timeouts, 5xx, rate limits (with `reset_at`) and a missing or
  invalid token.
- Users with more than 500 repos (`truncated`).
- JD with only unassessable technologies, or none at all (`score: null`). Empty or oversized JD and chat input.
- A page past the end of the repo list returns `items: []` with the correct `total`.
- Untrusted text (bios, repo descriptions, the JD) is returned as data and rendered as plain text. The frontend
  never uses `dangerouslySetInnerHTML`.

---

## Extra features

### 1. Portfolio Assistant (chatbot)

A free, offline-capable, intent-based assistant that answers from cached GitHub data. It needs no AI API key and
calls no external service; GitHub data still requires `GITHUB_TOKEN` when it isn't cached yet. Keyword rules, in
priority order, map a question to one of these intents: `top_languages`, `best_repos`, `repos_by_language`,
`streaks`, `stars`, `followers`, `profile_summary`, `match_score`, `gaps`, `portfolio_health`, or `unknown`.
Every answer comes with `evidence`: the facts and repo links it was built from. Unknown questions get a list of
what the bot can answer, plus suggested questions.

### 2. JD gap coach

Deterministic: the same data and JD always give the same output. It returns:

- **Strengths**: matched technologies, with supporting repos.
- **Missing technologies**.
- **Up to 3 repos to highlight**: ranked by number of matched languages, then stars, recency and name.
- **Unassessable items**.
- **A 3-line honest pitch**.

It never claims a technology without repo evidence, and it always states that language coverage does not prove
proficiency.

### 3. Portfolio health

See [Scoring](#portfolio-health-0100). It is also available through the chatbot ("How can I improve my
portfolio?").

---

## Limitations

- **Language coverage is not skill.** A repo containing TypeScript shows the language was used, not how well.
  Frameworks (React, Django, ...) are inferred from their language, not detected in code.
- **Keyword matching is heuristic.** Unusual phrasing can be missed (e.g. "Spring" alone, without "Boot",
  "Framework" or a list separator), and rare false positives are possible (e.g. "Go, team!").
- **Bytes favor some files.** Jupyter Notebook output and vendored code inflate language bytes. Tiny languages
  can round to 0%. The API still lists them; the chart hides 0% slices.
- **Public, owned repos only.** Private work, organization repos and contributions to other people's repos
  aren't counted as repos (contributions still count toward the calendar).
- **At most 500 repos** (5 pages × 100, by stars) and the top 10 languages per repo.
- **Contribution calendar** covers GitHub's default last-year window, and dates follow GitHub's calendar.
- **Single-process app.** The per-username locks are in-memory, and SQLite calls are synchronous. Both are fine
  for a local, single-user dashboard, not for multi-worker deployment.
- **The chatbot is rule-based.** It answers a fixed set of intents and doesn't hold multi-turn context
  (`history` is accepted but not used).
