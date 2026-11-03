"""GitHub GraphQL client.

Fetches a user's profile, contribution calendar and public owned repositories
and returns them as plain, normalized dicts. All failure modes are mapped to
the GitHubError subclasses in app.errors.
"""
from datetime import datetime, timezone

import httpx

from ..config import Settings
from ..errors import (
    TOKEN_SETUP_MESSAGE,
    GitHubAuthError,
    GitHubUnavailableError,
    RateLimitedError,
    UserNotFoundError,
)

REPO_FIELDS = """
  totalCount
  pageInfo { hasNextPage endCursor }
  nodes {
    name
    url
    description
    stargazerCount
    forkCount
    isFork
    isArchived
    pushedAt
    primaryLanguage { name color }
    languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
      edges { size node { name color } }
    }
  }
"""

REPO_ARGS = (
    "first: 100, after: $cursor, privacy: PUBLIC, ownerAffiliations: OWNER, "
    "orderBy: {field: STARGAZERS, direction: DESC}"
)

# `repositoryOwner` lets us tell an organization apart from a missing user.
PROFILE_QUERY = f"""
query($login: String!, $cursor: String) {{
  rateLimit {{ remaining resetAt }}
  repositoryOwner(login: $login) {{
    __typename
    ... on User {{
      login
      name
      avatarUrl
      bio
      url
      followers {{ totalCount }}
      contributionsCollection {{
        contributionCalendar {{
          totalContributions
          weeks {{ contributionDays {{ date contributionCount contributionLevel }} }}
        }}
      }}
      repositories({REPO_ARGS}) {{ {REPO_FIELDS} }}
    }}
  }}
}}
"""

REPOS_PAGE_QUERY = f"""
query($login: String!, $cursor: String) {{
  rateLimit {{ remaining resetAt }}
  user(login: $login) {{
    repositories({REPO_ARGS}) {{ {REPO_FIELDS} }}
  }}
}}
"""

CONTRIBUTION_LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


class GitHubClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings = settings
        self._transport = transport  # injectable for tests

    async def fetch_user(self, login: str) -> dict:
        if not self._settings.github_token:
            raise GitHubAuthError(TOKEN_SETUP_MESSAGE)

        async with httpx.AsyncClient(
            timeout=self._settings.github_timeout_seconds,
            transport=self._transport,
            headers={
                "Authorization": f"Bearer {self._settings.github_token}",
                "User-Agent": "github-portfolio-dashboard",
            },
        ) as http:
            data = await self._query(http, PROFILE_QUERY, {"login": login, "cursor": None})
            owner = data.get("repositoryOwner")
            if owner is None:
                raise UserNotFoundError(f"GitHub user '{login}' was not found.")
            if owner.get("__typename") != "User":
                raise UserNotFoundError(f"'{login}' is an organization, not a user. Enter a personal account.")

            rate_limit = data.get("rateLimit") or {}
            repo_conn = owner["repositories"]
            repos = list(repo_conn["nodes"])
            pages = 1
            while repo_conn["pageInfo"]["hasNextPage"] and pages < self._settings.max_repo_pages:
                page = await self._query(
                    http, REPOS_PAGE_QUERY, {"login": login, "cursor": repo_conn["pageInfo"]["endCursor"]}
                )
                rate_limit = page.get("rateLimit") or rate_limit
                repo_conn = page["user"]["repositories"]
                repos.extend(repo_conn["nodes"])
                pages += 1
            truncated = bool(repo_conn["pageInfo"]["hasNextPage"])

        return _normalize(owner, repos, truncated, rate_limit)

    async def _query(self, http: httpx.AsyncClient, query: str, variables: dict) -> dict:
        response = await self._post_with_retry(http, {"query": query, "variables": variables})
        _raise_for_http_status(response)
        try:
            body = response.json()
        except ValueError as exc:
            raise GitHubUnavailableError("GitHub returned an invalid response.") from exc

        # GraphQL reports many failures as HTTP 200 with an `errors` array.
        errors = body.get("errors") or []
        if errors:
            _raise_for_graphql_errors(errors, body.get("data"))
        if not body.get("data"):
            raise GitHubUnavailableError("GitHub returned no data.")
        return body["data"]

    async def _post_with_retry(self, http: httpx.AsyncClient, payload: dict) -> httpx.Response:
        """POST once, retrying a single time on network errors or 5xx. 4xx is never retried."""
        url = self._settings.github_graphql_url
        for attempt in range(2):
            try:
                response = await http.post(url, json=payload)
            except httpx.TransportError as exc:  # includes timeouts and connection errors
                if attempt == 1:
                    raise GitHubUnavailableError("GitHub could not be reached (network error or timeout).") from exc
                continue
            if response.status_code >= 500 and attempt == 0:
                continue
            return response
        raise AssertionError("unreachable")


def _raise_for_http_status(response: httpx.Response) -> None:
    status = response.status_code
    if status == 401:
        raise GitHubAuthError(TOKEN_SETUP_MESSAGE)
    if status in (403, 429):
        if status == 429 or response.headers.get("x-ratelimit-remaining") == "0" or "rate limit" in response.text.lower():
            raise RateLimitedError("GitHub API rate limit exceeded.", reset_at=_reset_from_headers(response))
        raise GitHubAuthError("GitHub refused the request (403). " + TOKEN_SETUP_MESSAGE)
    if status >= 500:
        raise GitHubUnavailableError(f"GitHub is unavailable (HTTP {status}).")
    if status >= 400:
        raise GitHubUnavailableError(f"Unexpected GitHub response (HTTP {status}).")


def _raise_for_graphql_errors(errors: list[dict], data: dict | None) -> None:
    types = {err.get("type") for err in errors}
    messages = "; ".join(err.get("message", "") for err in errors)
    if "RATE_LIMITED" in types:
        reset_at = ((data or {}).get("rateLimit") or {}).get("resetAt")
        raise RateLimitedError("GitHub API rate limit exceeded.", reset_at=reset_at)
    if "NOT_FOUND" in types:
        raise UserNotFoundError("GitHub user was not found.")
    if "FORBIDDEN" in types or "INSUFFICIENT_SCOPES" in types:
        raise GitHubAuthError("GitHub token lacks access: " + messages)
    raise GitHubUnavailableError("GitHub GraphQL error: " + messages)


def _reset_from_headers(response: httpx.Response) -> str | None:
    reset = response.headers.get("x-ratelimit-reset")
    if reset and reset.isdigit():
        return datetime.fromtimestamp(int(reset), tz=timezone.utc).isoformat()
    return None


def _normalize(owner: dict, repos: list[dict], truncated: bool, rate_limit: dict) -> dict:
    calendar = owner["contributionsCollection"]["contributionCalendar"]
    days = [
        {
            "date": day["date"],
            "count": day["contributionCount"],
            "level": CONTRIBUTION_LEVELS.get(day["contributionLevel"], 0),
        }
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    ]
    return {
        "profile": {
            "login": owner["login"],
            "name": owner.get("name"),
            "avatar_url": owner.get("avatarUrl"),
            "bio": owner.get("bio"),
            "url": owner.get("url"),
            "followers": (owner.get("followers") or {}).get("totalCount", 0),
        },
        "total_contributions": calendar["totalContributions"],
        "days": days,
        "repositories": [_normalize_repo(repo) for repo in repos],
        "truncated": truncated,
        "rate_limit": {"remaining": rate_limit.get("remaining"), "reset_at": rate_limit.get("resetAt")},
    }


def _normalize_repo(repo: dict) -> dict:
    primary = repo.get("primaryLanguage") or {}
    edges = (repo.get("languages") or {}).get("edges") or []
    return {
        "name": repo["name"],
        "url": repo["url"],
        "description": repo.get("description"),
        "stars": repo.get("stargazerCount", 0),
        "forks": repo.get("forkCount", 0),
        "is_fork": bool(repo.get("isFork")),
        "is_archived": bool(repo.get("isArchived")),
        "pushed_at": repo.get("pushedAt"),
        "primary_language": primary.get("name"),
        "primary_language_color": primary.get("color"),
        "languages": [
            {"name": edge["node"]["name"], "color": edge["node"].get("color"), "size": edge.get("size", 0)}
            for edge in edges
        ],
    }
