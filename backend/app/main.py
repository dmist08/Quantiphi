"""FastAPI application factory.

Run with:  uvicorn app.main:create_app --factory --reload
"""
from fastapi import FastAPI

from .config import Settings, get_settings
from .db import init_db
from .errors import register_error_handlers
from .routers import settings as settings_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    init_db(settings.database_path)

    app = FastAPI(title="GitHub Developer Portfolio API", version="1.0.0")
    app.state.settings = settings
    register_error_handlers(app)

    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "github_token_configured": bool(settings.github_token)}

    app.include_router(settings_router.router)
    return app
