"""Tech Stack Compatibility match and JD gap coach endpoints."""
from fastapi import APIRouter, Request

from ..schemas import MAX_JD_CHARS, JobDescriptionIn, clean_text, validate_username
from ..services import gap_coach, matcher
from .dashboard import get_cache

router = APIRouter(prefix="/api/users/{username}", tags=["match"])


@router.post("/match")
async def match(username: str, body: JobDescriptionIn, request: Request) -> dict:
    validate_username(username)
    jd = clean_text(body.job_description, "job_description", MAX_JD_CHARS)
    cache = get_cache(request)
    data = await cache.get_user_data(username)
    result = matcher.analyze(jd, data["repositories"])
    cache.save_job_description(username, jd)
    return {"match": result, "job_description": jd, "meta": data["meta"]}


@router.post("/gap-coach")
async def gap_coach_endpoint(username: str, body: JobDescriptionIn, request: Request) -> dict:
    validate_username(username)
    jd = clean_text(body.job_description, "job_description", MAX_JD_CHARS)
    data = await get_cache(request).get_user_data(username)
    result = matcher.analyze(jd, data["repositories"])
    return gap_coach.coach(result, data["repositories"])
