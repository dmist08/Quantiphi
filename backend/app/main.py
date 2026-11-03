"""FastAPI application factory.

Run with:  uvicorn app.main:create_app --factory --reload --port 8000
"""
from fastapi import FastAPI

from .config import Settings, get_settings
from .db import init_db
from .errors import register_error_handlers
from .routers import dashboard as dashboard_router
from .routers import settings as settings_router
from .services.cache_service import CacheService
from .services.github_client import GitHubClient


def create_app(settings: Settings | None = None, github_client: GitHubClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    init_db(settings.database_path)

    app = FastAPI(title="GitHub Developer Portfolio API", version="1.0.0")
    app.state.settings = settings
    app.state.cache = CacheService(settings, github_client or GitHubClient(settings))
    register_error_handlers(app)

    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {
            "status": "ok",
            "github_token_configured": bool(settings.github_token),
            "llm_configured": bool(settings.llm_api_key),
        }

    app.include_router(dashboard_router.router)
    app.include_router(settings_router.router)
    return app
