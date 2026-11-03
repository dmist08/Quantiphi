"""Request models and shared input validation."""
import re
from typing import Literal

from pydantic import BaseModel, Field

from .errors import InvalidInputError, PayloadTooLargeError

USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")
MAX_JD_CHARS = 20_000
MAX_CHAT_CHARS = 2_000

Theme = Literal["light", "dark", "system"]


def validate_username(username: str) -> str:
    """Return the username unchanged if it is a valid GitHub login, else raise 422."""
    if not isinstance(username, str) or not USERNAME_RE.fullmatch(username):
        raise InvalidInputError(
            "Invalid GitHub username. Use 1-39 letters, digits or single hyphens, "
            "not starting or ending with a hyphen.",
            field="username",
        )
    return username


def normalize_username(username: str) -> str:
    """Validated, lowercase cache key."""
    return validate_username(username).lower()


def clean_text(text: str, field: str, max_chars: int) -> str:
    """Trim text; 422 if empty, 413 if longer than max_chars."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise InvalidInputError(f"{field} must not be empty.", field=field)
    if len(cleaned) > max_chars:
        raise PayloadTooLargeError(
            f"{field} is {len(cleaned)} characters; the limit is {max_chars}.",
            field=field,
            max_chars=max_chars,
        )
    return cleaned


class JobDescriptionIn(BaseModel):
    job_description: str


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4_000)


class ChatIn(BaseModel):
    message: str
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class SettingsIn(BaseModel):
    default_username: str | None = None
    theme: Theme = "system"


class SettingsOut(BaseModel):
    default_username: str | None
    theme: Theme
