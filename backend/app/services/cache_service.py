"""SQLite-backed cache in front of the GitHub client.

Rules:
- Cache key is the lowercase username; GitHub's original casing is stored for display.
- Data younger than the TTL (1 hour) is served without calling GitHub.
- refresh=True bypasses the TTL, but only if the last successful fetch is at
  least `refresh_min_interval_seconds` old; otherwise cached data is returned
  with a notice explaining why.
- One asyncio.Lock per username prevents duplicate concurrent fetches.
- A user's data is replaced inside a single transaction, so repos deleted on
  GitHub disappear and a failed refresh leaves the old data intact.
- If a refresh fails and cached data exists, it is returned with stale=True.
"""
import asyncio
import math
import time
from datetime import datetime, timezone
from typing import Callable

from ..config import Settings
from ..db import get_conn, transaction
from ..errors import GitHubError, NotCachedError, UserNotFoundError
from ..schemas import normalize_username
from .github_client import GitHubClient


def iso_from_epoch(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")


class CacheService:
    def __init__(self, settings: Settings, client: GitHubClient, clock: Callable[[], float] = time.time):
        self._settings = settings
        self._client = client
        self._clock = clock
        self._locks: dict[str, asyncio.Lock] = {}

    @property
    def db_path(self) -> str:
        return self._settings.database_path

    async def get_user_data(self, username: str, refresh: bool = False) -> dict:
        key = normalize_username(username)
        ttl = self._settings.cache_ttl_seconds
        min_interval = self._settings.refresh_min_interval_seconds

        cached = self.load(key)
        if cached is not None:
            age = self._clock() - cached["fetched_epoch"]
            if not refresh and age < ttl:
                return self._with_meta(cached)
            if refresh and age < min_interval:
                wait = math.ceil(min_interval - age)
                notice = (
                    f"Data was refreshed {int(age)}s ago. Refresh is allowed once every "
                    f"{min_interval}s; try again in {wait}s. Showing cached data."
                )
                return self._with_meta(cached, notice=notice)

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            # Another request may have refreshed while we waited for the lock.
            cached = self.load(key)
            if cached is not None:
                age = self._clock() - cached["fetched_epoch"]
                if age < (min_interval if refresh else ttl):
                    return self._with_meta(cached)

            try:
                fresh = await self._client.fetch_user(username)
            except UserNotFoundError:
                raise
            except GitHubError as exc:
                if cached is None:
                    raise
                warning = f"GitHub refresh failed ({exc.message}). Showing cached data from {iso_from_epoch(cached['fetched_epoch'])}."
                return self._with_meta(cached, stale=True, warning=warning, error_code=exc.code)

            self.save(key, fresh)
            return self._with_meta(self.load(key))

    def require_cached(self, username: str) -> dict:
        """Cached data only, never calling GitHub (used by the chatbot)."""
        cached = self.load(normalize_username(username))
        if cached is None:
            raise NotCachedError(f"No cached data for '{username}'. Load the dashboard first.")
        return self._with_meta(cached)

    def save_job_description(self, username: str, job_description: str) -> None:
        """Keep only the latest JD per user."""
        with get_conn(self.db_path) as conn:
            conn.execute(
                "INSERT INTO jd_inputs (username_key, job_description, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(username_key) DO UPDATE SET "
                "job_description = excluded.job_description, updated_at = excluded.updated_at",
                (normalize_username(username), job_description, self._clock()),
            )

    def load_job_description(self, username: str) -> str | None:
        with get_conn(self.db_path) as conn:
            row = conn.execute(
                "SELECT job_description FROM jd_inputs WHERE username_key = ?", (normalize_username(username),)
            ).fetchone()
        return row["job_description"] if row else None

    def save(self, key: str, data: dict) -> None:
        profile = data["profile"]
        now = self._clock()
        with get_conn(self.db_path) as conn, transaction(conn):
            conn.execute(
                """
                INSERT INTO users (username_key, login, name, avatar_url, bio, url, followers,
                                   total_contributions, truncated, rate_limit_remaining,
                                   rate_limit_reset_at, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username_key) DO UPDATE SET
                    login = excluded.login, name = excluded.name, avatar_url = excluded.avatar_url,
                    bio = excluded.bio, url = excluded.url, followers = excluded.followers,
                    total_contributions = excluded.total_contributions, truncated = excluded.truncated,
                    rate_limit_remaining = excluded.rate_limit_remaining,
                    rate_limit_reset_at = excluded.rate_limit_reset_at, fetched_at = excluded.fetched_at
                """,
                (
                    key, profile["login"], profile.get("name"), profile.get("avatar_url"), profile.get("bio"),
                    profile.get("url"), profile.get("followers", 0), data.get("total_contributions", 0),
                    int(data.get("truncated", False)), data["rate_limit"].get("remaining"),
                    data["rate_limit"].get("reset_at"), now,
                ),
            )
            # Full replace: repos removed on GitHub disappear (languages cascade).
            conn.execute("DELETE FROM repositories WHERE username_key = ?", (key,))
            conn.execute("DELETE FROM contribution_days WHERE username_key = ?", (key,))
            for repo in data["repositories"]:
                cur = conn.execute(
                    """
                    INSERT INTO repositories (username_key, name, url, description, stars, forks, is_fork,
                                              is_archived, pushed_at, primary_language, primary_language_color)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key, repo["name"], repo["url"], repo.get("description"), repo.get("stars", 0),
                        repo.get("forks", 0), int(repo.get("is_fork", False)), int(repo.get("is_archived", False)),
                        repo.get("pushed_at"), repo.get("primary_language"), repo.get("primary_language_color"),
                    ),
                )
                conn.executemany(
                    "INSERT INTO repo_languages (repo_id, language, color, size) VALUES (?, ?, ?, ?)",
                    [(cur.lastrowid, lang["name"], lang.get("color"), lang.get("size", 0)) for lang in repo.get("languages", [])],
                )
            conn.executemany(
                "INSERT INTO contribution_days (username_key, date, count, level) VALUES (?, ?, ?, ?)",
                [(key, day["date"], day["count"], day["level"]) for day in data["days"]],
            )

    def load(self, key: str) -> dict | None:
        with get_conn(self.db_path) as conn:
            user = conn.execute("SELECT * FROM users WHERE username_key = ?", (key,)).fetchone()
            if user is None:
                return None
            repo_rows = conn.execute(
                "SELECT * FROM repositories WHERE username_key = ? ORDER BY stars DESC, name COLLATE NOCASE",
                (key,),
            ).fetchall()
            lang_rows = conn.execute(
                """
                SELECT rl.repo_id, rl.language, rl.color, rl.size
                FROM repo_languages rl JOIN repositories r ON r.id = rl.repo_id
                WHERE r.username_key = ? ORDER BY rl.size DESC
                """,
                (key,),
            ).fetchall()
            day_rows = conn.execute(
                "SELECT date, count, level FROM contribution_days WHERE username_key = ? ORDER BY date",
                (key,),
            ).fetchall()

        languages_by_repo: dict[int, list[dict]] = {}
        for row in lang_rows:
            languages_by_repo.setdefault(row["repo_id"], []).append(
                {"name": row["language"], "color": row["color"], "size": row["size"]}
            )
        repos = [
            {
                "name": r["name"],
                "url": r["url"],
                "description": r["description"],
                "stars": r["stars"],
                "forks": r["forks"],
                "is_fork": bool(r["is_fork"]),
                "is_archived": bool(r["is_archived"]),
                "pushed_at": r["pushed_at"],
                "primary_language": r["primary_language"],
                "primary_language_color": r["primary_language_color"],
                "languages": languages_by_repo.get(r["id"], []),
            }
            for r in repo_rows
        ]
        return {
            "username_key": key,
            "profile": {
                "login": user["login"],
                "name": user["name"],
                "avatar_url": user["avatar_url"],
                "bio": user["bio"],
                "url": user["url"],
                "followers": user["followers"],
            },
            "total_contributions": user["total_contributions"],
            "days": [dict(row) for row in day_rows],
            "repositories": repos,
            "truncated": bool(user["truncated"]),
            "rate_limit": {"remaining": user["rate_limit_remaining"], "reset_at": user["rate_limit_reset_at"]},
            "fetched_epoch": user["fetched_at"],
        }

    def _with_meta(self, cached: dict, stale: bool = False, warning: str | None = None,
                   notice: str | None = None, error_code: str | None = None) -> dict:
        meta = {
            "fetched_at": iso_from_epoch(cached["fetched_epoch"]),
            "stale": stale,
            "warning": warning,
            "notice": notice,
            "error_code": error_code,
            "truncated": cached["truncated"],
            "rate_limit": cached["rate_limit"],
        }
        return {**cached, "meta": meta}
