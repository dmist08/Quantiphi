"""Application errors and the handlers that turn them into consistent JSON.

Every error response has the shape:
    {"error": {"code": "...", "message": "...", ...extra}}
"""
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, **extra: Any):
        super().__init__(message)
        self.message = message
        self.extra = extra

    def to_body(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, **self.extra}}


class InvalidInputError(AppError):
    status_code = 422
    code = "invalid_input"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


class GitHubError(AppError):
    """Base class for failures talking to GitHub."""


class UserNotFoundError(GitHubError):
    status_code = 404
    code = "user_not_found"


class GitHubAuthError(GitHubError):
    status_code = 401
    code = "github_auth"


class RateLimitedError(GitHubError):
    status_code = 429
    code = "rate_limited"


class GitHubUnavailableError(GitHubError):
    status_code = 503
    code = "github_unavailable"


TOKEN_SETUP_MESSAGE = (
    "GITHUB_TOKEN is missing or invalid. Create a GitHub personal access token "
    "and set GITHUB_TOKEN in backend/.env (see .env.example), then restart the backend."
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_body())

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        body = {"error": {"code": "invalid_input", "message": "Request validation failed.", "details": details}}
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        body = {"error": {"code": "http_error", "message": str(exc.detail)}}
        return JSONResponse(status_code=exc.status_code, content=body)
