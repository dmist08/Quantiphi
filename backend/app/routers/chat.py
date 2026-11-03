"""Rule-based portfolio chatbot endpoint (cached data only)."""
from fastapi import APIRouter, Request

from ..schemas import MAX_CHAT_CHARS, ChatIn, clean_text, validate_username
from ..services import chatbot
from .dashboard import get_cache

router = APIRouter(prefix="/api/users/{username}", tags=["chat"])


@router.post("/chat")
def chat(username: str, body: ChatIn, request: Request) -> dict:
    validate_username(username)
    message = clean_text(body.message, "message", MAX_CHAT_CHARS)
    cache = get_cache(request)
    data = cache.require_cached(username)  # never calls GitHub
    return chatbot.respond(message, data, cache.load_job_description(username))
