# API Contract

Source of truth between the FastAPI backend and the React frontend.

- Backend: `http://127.0.0.1:8000` (`uvicorn app.main:create_app --factory --port 8000`)
- Frontend: Vite dev server proxies every request under **`/api`** to `http://127.0.0.1:8000`.
  The frontend always calls relative paths such as `/api/users/octocat/dashboard`.
- All bodies are JSON (`Content-Type: application/json`). Timestamps are ISO-8601 strings (UTC for
  `fetched_at`; GitHub's format for `pushed_at` / `reset_at`). Dates are `YYYY-MM-DD`.
- All calculations (stats, streaks, language %, scores, sorting, filtering, pagination) happen on the server.
  The frontend only renders.
- "nullable" means the key is always present and its value may be `null`.

---

## Error shape (every non-2xx response)

```json
{
  "error": {
    "code": "rate_limited",
    "message": "GitHub API rate limit exceeded.",
    "reset_at": "2026-11-03T12:00:00Z"
  }
}
```

`code` and `message` are always present. Extra keys depend on the code.

| HTTP | `code`               | When                                                                 | Extra keys |
|------|----------------------|----------------------------------------------------------------------|------------|
| 422  | `invalid_input`      | Bad username, empty text, bad query/body value                       | `field` (string, optional), `details` (array of `{field, message}`, optional – body/query validation) |
| 413  | `payload_too_large`  | `job_description` > 20000 chars, chat `message` > 2000 chars (after trim) | `field`, `max_chars` |
| 404  | `user_not_found`     | GitHub user does not exist, or the login is an organization          | – |
| 404  | `not_cached`         | Chat asked about a user whose dashboard has never been loaded        | – |
| 401  | `github_auth`        | `GITHUB_TOKEN` missing/invalid/insufficient; message explains setup  | – |
| 429  | `rate_limited`       | GitHub rate limit hit and no cached data exists                      | `reset_at` (string, nullable) |
| 503  | `github_unavailable` | GitHub down / network error / timeout / GraphQL error, and no cache  | – |
| 4xx  | `http_error`         | Unknown route or method                                              | – |

Note: when cached data exists, GitHub failures (401/429/503) do **not** produce an error; the cached data is
returned with `meta.stale = true` (see `Meta`). `user_not_found` is always an error.

Username rule (path parameter `{username}`): `^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$`, otherwise 422
with `field: "username"`. Usernames are case-insensitive; responses use GitHub's original casing.

---

## Shared objects

### Meta
Returned by the dashboard, repositories and match endpoints.

```json
{
  "fetched_at": "2026-11-03T09:40:12+00:00",
  "stale": false,
  "warning": null,
  "notice": null,
  "error_code": null,
  "truncated": false,
  "rate_limit": { "remaining": 4990, "reset_at": "2026-11-03T10:40:00Z" }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `fetched_at` | string | Time of the last **successful** GitHub fetch. |
| `stale` | boolean | `true` when a refresh failed and cached data is being shown. |
| `warning` | string, nullable | Human-readable reason for `stale`. Non-null iff `stale` is true. |
| `notice` | string, nullable | Informational, e.g. "refresh too soon, try again in 42s". Data is not stale. |
| `error_code` | string, nullable | Error code of the failed refresh when `stale` (e.g. `rate_limited`). |
| `truncated` | boolean | `true` if the user has more than 500 public repos and only the top 500 by stars were fetched. |
| `rate_limit.remaining` | integer, nullable | From GitHub at last fetch. |
| `rate_limit.reset_at` | string, nullable | From GitHub at last fetch. |

### MatchResult

```json
{
  "status": "ok",
  "score": 67,
  "matched_count": 2,
  "assessable_count": 3,
  "matched": [
    {
      "name": "Python",
      "accepted_languages": ["Python", "Jupyter Notebook"],
      "evidence": [
        { "repo": "data-tools", "url": "https://github.com/octocat/data-tools", "language": "Python" }
      ]
    }
  ],
  "missing": [
    { "name": "Rust", "accepted_languages": ["Rust"] }
  ],
  "unassessable": ["AWS", "Kubernetes"],
  "explanation": "Matched 2 of 3 assessable technologies: score = round(100 × 2 / 3) = 67%. ..."
}
```

| Field | Type | Notes |
|-------|------|-------|
| `status` | `"ok"` \| `"no_assessable_keywords"` | `no_assessable_keywords` when the JD contains no technology that can be checked against repo languages. |
| `score` | integer 0–100, nullable | `null` iff `status == "no_assessable_keywords"`. Never `0` in that case. |
| `matched_count`, `assessable_count` | integer | `score = round(100 * matched_count / assessable_count)` |
| `matched[]` | array | Technologies found in the JD **and** in the user's non-fork repos. Ordered by first appearance in the JD. |
| `matched[].evidence[]` | array (1–3 items) | Non-fork repos that contain an accepted language, largest byte count first. |
| `missing[]` | array | Assessable technologies in the JD with no supporting repo. |
| `unassessable` | string[] | Recognized technologies that cannot be verified from languages (AWS, Kubernetes, ...). Excluded from the score. |
| `explanation` | string | Plain-text explanation of the formula and result. |

Each technology appears at most once in `matched` + `missing` combined, however many times the JD repeats it.

---

## Endpoints

### `GET /api/health`

```json
{ "status": "ok", "github_token_configured": true, "llm_configured": false }
```

---

### `GET /api/users/{username}/dashboard`

| Query | Type | Default | Notes |
|-------|------|---------|-------|
| `refresh` | boolean | `false` | Bypass the 1-hour cache TTL. Ignored (with a `meta.notice`) if the last successful fetch was < 60 s ago. |

**200**

```json
{
  "profile": {
    "login": "Octocat",
    "name": "The Octocat",
    "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
    "bio": null,
    "url": "https://github.com/octocat",
    "followers": 1200
  },
  "stats": {
    "total_stars": 345,
    "public_repos": 8,
    "forked_repos": 2,
    "archived_repos": 1,
    "total_contributions": 412,
    "current_streak": 5,
    "longest_streak": 21,
    "active_days": 130,
    "best_day": { "date": "2026-05-14", "count": 17 }
  },
  "languages": [
    { "name": "Python", "color": "#3572A5", "bytes": 120000, "percent": 48 },
    { "name": "TypeScript", "color": "#3178c6", "bytes": 80000, "percent": 32 },
    { "name": "Other", "color": null, "bytes": 50000, "percent": 20 }
  ],
  "contributions": {
    "total": 412,
    "start_date": "2025-11-02",
    "end_date": "2026-11-03",
    "weeks": [
      [null, null, { "date": "2025-11-02", "count": 0, "level": 0 }, "... 7 entries per week"]
    ],
    "months": [ { "label": "Nov", "week_index": 0 }, { "label": "Dec", "week_index": 4 } ]
  },
  "match": null,
  "job_description": null,
  "meta": { "...": "see Meta" }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `profile.name`, `profile.bio`, `profile.avatar_url`, `profile.url` | string, nullable | |
| `profile.login` | string | GitHub's original casing. |
| `stats.total_stars` | integer | Sum of stars of owned **non-fork** repos (archived included). |
| `stats.public_repos` | integer | Owned non-fork repos. `forked_repos` = forks; `archived_repos` = archived non-forks. |
| `stats.current_streak` | integer | Consecutive days with ≥1 contribution ending on the most recent day; if the most recent day has 0, counting starts from the previous day. |
| `stats.longest_streak`, `stats.active_days` | integer | `active_days` = days with ≥1 contribution. |
| `stats.best_day` | object, nullable | `null` when there are no contributions. |
| `languages[]` | array (0–6 items) | Bytes across owned non-fork repos. Top 5 by bytes plus `"Other"` (only if more languages exist). `percent` are integers summing to exactly 100. Empty array when no language data. `color` nullable. |
| `contributions.weeks` | array of arrays | Each inner array has exactly **7** entries, index 0 = Sunday … 6 = Saturday. Entries are `null` for padding before the first / after the last day. |
| `contributions.weeks[][].level` | integer 0–4 | From GitHub's `contributionLevel` (NONE=0 … FOURTH_QUARTILE=4). Use it directly for color. |
| `contributions.start_date`, `end_date` | string, nullable | `null` if there are no days. |
| `contributions.months[]` | array | Month label for the first week that contains the 1st day of that month (or the first week). |
| `match` | MatchResult, nullable | Recomputed from the user's saved JD on every dashboard response; `null` if no JD saved. |
| `job_description` | string, nullable | Latest saved JD. Render as plain text only. |

Errors: 422 `invalid_input`, 404 `user_not_found`, 401 `github_auth`, 429 `rate_limited`, 503 `github_unavailable`
(the last three only when nothing is cached).

---

### `GET /api/users/{username}/repositories`

| Query | Type | Default | Allowed |
|-------|------|---------|---------|
| `sort` | string | `stars` | `stars` (desc), `forks` (desc), `updated` (pushed_at desc, nulls last), `name` (A→Z, case-insensitive) |
| `language` | string | empty | Case-insensitive match on the repo's primary language. Empty = all. |
| `include_forks` | boolean | `false` | Forks are listed only when `true`. |
| `page` | integer | `1` | ≥ 1. Pages past the end return `items: []`. |
| `page_size` | integer | `12` | 1–50 |

Ties are broken by name (A→Z). Uses cached data (fetches from GitHub only if the cache is missing or expired).

**200**

```json
{
  "items": [
    {
      "name": "data-tools",
      "url": "https://github.com/octocat/data-tools",
      "description": null,
      "stars": 120,
      "forks": 8,
      "language": "Python",
      "language_color": "#3572A5",
      "is_fork": false,
      "is_archived": true,
      "pushed_at": "2026-10-30T12:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 12,
  "total": 1,
  "total_pages": 1,
  "sort": "stars",
  "language": "python",
  "include_forks": false,
  "available_languages": ["Python", "TypeScript"],
  "meta": { "...": "see Meta" }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `items[].description`, `language`, `language_color`, `pushed_at` | nullable | |
| `total` | integer | Count after filtering. `total_pages` = `ceil(total / page_size)`, `0` when `total` is 0. |
| `language` | string, nullable | Echo of the filter (`null` when not filtering). |
| `available_languages` | string[] | Sorted distinct primary languages of repos in scope (respects `include_forks`, ignores `language`). For the filter dropdown. |

Errors: as dashboard, plus 422 for bad `sort` / `page` / `page_size`.

---

### `POST /api/users/{username}/match`

Request:
```json
{ "job_description": "We need a Python/Go backend developer with AWS experience." }
```

The text is trimmed. Empty → 422 `invalid_input`; longer than 20000 characters → 413 `payload_too_large`.
On success the JD is saved as the user's **only** saved JD (replacing any previous one).

**200**
```json
{
  "match": { "...": "MatchResult" },
  "job_description": "We need a Python/Go backend developer with AWS experience.",
  "meta": { "...": "see Meta" }
}
```

Errors: 422, 413, plus the dashboard errors (the user's repo data is loaded through the cache).

---

### `POST /api/users/{username}/gap-coach`

Request: same as `/match`, same validation. Does **not** save the JD. Deterministic: the same data and JD
always produce the same output.

**200**
```json
{
  "status": "ok",
  "score": 67,
  "strengths": [
    {
      "name": "Python",
      "summary": "Python appears in 4 of your public repos (largest: data-tools).",
      "evidence": [ { "repo": "data-tools", "url": "https://github.com/octocat/data-tools", "language": "Python" } ]
    }
  ],
  "missing": ["Rust"],
  "highlight_repos": [
    {
      "name": "data-tools",
      "url": "https://github.com/octocat/data-tools",
      "stars": 120,
      "matched_languages": ["Python"],
      "reason": "Uses Python; 120 stars."
    }
  ],
  "unassessable": ["AWS"],
  "pitch": [
    "My public GitHub shows work in Python and Go, 2 of the 3 technologies this role lists that can be checked.",
    "The clearest examples are data-tools and api-server.",
    "I don't have public work in Rust yet and would be upfront about that."
  ],
  "disclaimer": "Language coverage shows that code in a language exists in public repositories; it does not prove proficiency."
}
```

| Field | Type | Notes |
|-------|------|-------|
| `status`, `score` | as MatchResult | |
| `strengths[]` | array | One per matched technology. |
| `missing`, `unassessable` | string[] | |
| `highlight_repos[]` | array (0–3) | Non-fork repos ranked by number of matched languages, then stars, then most recently pushed, then name. Only repos with ≥1 matched language. |
| `pitch` | string[] | Exactly 3 lines, plain text. Never claims a technology without repo evidence. |
| `disclaimer` | string | Always present. |

---

### `POST /api/users/{username}/chat`

Request:
```json
{
  "message": "What are my top languages?",
  "history": [ { "role": "user", "content": "hi" }, { "role": "assistant", "content": "..." } ]
}
```

| Field | Rules |
|-------|-------|
| `message` | Trimmed. Empty → 422; > 2000 chars → 413. |
| `history` | Optional, ≤ 20 items, `role` ∈ `user` \| `assistant`, `content` ≤ 4000 chars. Used only as LLM context. |

Answers come **only from cached data** (no GitHub call). If the user has never been loaded → 404 `not_cached`.

**200**
```json
{
  "intent": "top_languages",
  "answer": "Your top languages by code size are Python (48%), TypeScript (32%) and Other (20%).",
  "evidence": [
    { "label": "Python", "value": "48% · 120000 bytes", "url": null }
  ],
  "suggestions": ["What are my top languages?", "Which are my best repos?", "What is my current streak?"],
  "llm_used": false
}
```

| Field | Type | Notes |
|-------|------|-------|
| `intent` | string | One of `top_languages`, `best_repos`, `repos_by_language`, `streaks`, `stars`, `followers`, `profile_summary`, `match_score`, `gaps`, `unknown`. |
| `answer` | string | Plain text. Render as text (no HTML). |
| `evidence[]` | array of `{label: string, value: string, url: string \| null}` | Facts the answer is built from. |
| `suggestions` | string[] | Example questions the bot can answer. |
| `llm_used` | boolean | `true` only if the optional LLM rewrite succeeded. |

---

### `GET /api/settings`

**200**
```json
{ "default_username": null, "theme": "system" }
```

`default_username`: string, nullable. `theme`: `"light"` \| `"dark"` \| `"system"`.

### `PUT /api/settings`

Request (both fields optional; omitted `theme` resets to `"system"`, omitted/empty `default_username` clears it):
```json
{ "default_username": "octocat", "theme": "dark" }
```

**200**: the saved settings, same shape as GET.
Errors: 422 `invalid_input` for an invalid username or theme.
