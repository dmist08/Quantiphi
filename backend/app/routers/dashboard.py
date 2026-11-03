"""Dashboard, repository listing and portfolio health endpoints."""
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from ..schemas import validate_username
from ..services import matcher, portfolio_health, stats
from ..services.cache_service import CacheService

router = APIRouter(prefix="/api/users/{username}", tags=["dashboard"])


def get_cache(request: Request) -> CacheService:
    return request.app.state.cache


def get_today() -> date:
    """Current UTC date; overridden in tests via app.dependency_overrides."""
    return datetime.now(timezone.utc).date()


@router.get("/dashboard")
async def dashboard(username: str, request: Request, refresh: bool = False) -> dict:
    cache = get_cache(request)
    data = await cache.get_user_data(username, refresh=refresh)
    # The badge is recomputed from the saved JD on every response, so it always
    # reflects the current cached repositories.
    job_description = cache.load_job_description(username)
    match = matcher.analyze(job_description, data["repositories"]) if job_description else None
    return {
        "profile": data["profile"],
        "stats": stats.summary_stats(data),
        "languages": stats.language_breakdown(data["repositories"]),
        "contributions": {"total": data["total_contributions"], **stats.contribution_grid(data["days"])},
        "match": match,
        "job_description": job_description,
        "meta": data["meta"],
    }


@router.get("/repositories")
async def repositories(
    username: str,
    request: Request,
    sort: Literal["stars", "forks", "updated", "name"] = "stars",
    language: str = Query("", max_length=100),
    include_forks: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
) -> dict:
    data = await get_cache(request).get_user_data(username)
    result = stats.list_repositories(
        data["repositories"], sort=sort, language=language,
        include_forks=include_forks, page=page, page_size=page_size,
    )
    return {**result, "meta": data["meta"]}


@router.get("/portfolio-health")
def portfolio_health_endpoint(username: str, request: Request, today: date = Depends(get_today)) -> dict:
    validate_username(username)
    data = get_cache(request).require_cached(username)  # cached data only
    return {**portfolio_health.evaluate(data, today), "meta": data["meta"]}
