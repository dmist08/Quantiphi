"""Dashboard and repository listing endpoints."""
from typing import Literal

from fastapi import APIRouter, Query, Request

from ..services import stats
from ..services.cache_service import CacheService

router = APIRouter(prefix="/api/users/{username}", tags=["dashboard"])


def get_cache(request: Request) -> CacheService:
    return request.app.state.cache


@router.get("/dashboard")
async def dashboard(username: str, request: Request, refresh: bool = False) -> dict:
    cache = get_cache(request)
    data = await cache.get_user_data(username, refresh=refresh)
    return {
        "profile": data["profile"],
        "stats": stats.summary_stats(data),
        "languages": stats.language_breakdown(data["repositories"]),
        "contributions": {"total": data["total_contributions"], **stats.contribution_grid(data["days"])},
        "match": None,
        "job_description": None,
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
