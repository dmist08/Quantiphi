"""Runtime configuration read from the backend environment.

Values are read on every call (not cached at import time) so tests can
override them with monkeypatch and the GitHub token never leaves the backend.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env into the process environment if it exists. Existing
# environment variables win, so tests and shells can override it.
load_dotenv(BACKEND_DIR / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    github_token: str | None
    llm_api_key: str | None
    llm_model: str
    database_path: str
    cache_ttl_seconds: int
    refresh_min_interval_seconds: int
    github_graphql_url: str = "https://api.github.com/graphql"
    github_timeout_seconds: float = 10.0
    max_repo_pages: int = 5


def get_settings() -> Settings:
    db_path = os.getenv("DATABASE_PATH", "portfolio_cache.db")
    if not os.path.isabs(db_path):
        db_path = str(BACKEND_DIR / db_path)
    return Settings(
        github_token=os.getenv("GITHUB_TOKEN") or None,
        llm_api_key=os.getenv("LLM_API_KEY") or None,
        llm_model=os.getenv("LLM_MODEL", "claude-haiku-5-5"),
        database_path=db_path,
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
        refresh_min_interval_seconds=int(os.getenv("REFRESH_MIN_INTERVAL_SECONDS", "60")),
    )
