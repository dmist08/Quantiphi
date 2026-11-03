"""User settings persisted in the SQLite `settings` table."""
from fastapi import APIRouter, Request

from ..db import get_conn, transaction
from ..schemas import SettingsIn, SettingsOut, validate_username

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULTS = {"default_username": None, "theme": "system"}


def _read(db_path: str) -> SettingsOut:
    with get_conn(db_path) as conn:
        rows = conn.execute("SELECT key, value FROM settings WHERE key IN (?, ?)", tuple(DEFAULTS)).fetchall()
    values = {**DEFAULTS, **{row["key"]: row["value"] for row in rows}}
    return SettingsOut(**values)


@router.get("", response_model=SettingsOut)
def get_settings(request: Request) -> SettingsOut:
    return _read(request.app.state.settings.database_path)


@router.put("", response_model=SettingsOut)
def put_settings(body: SettingsIn, request: Request) -> SettingsOut:
    username = (body.default_username or "").strip() or None
    if username is not None:
        validate_username(username)
    db_path = request.app.state.settings.database_path
    with get_conn(db_path) as conn, transaction(conn):
        for key, value in (("default_username", username), ("theme", body.theme)):
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
    return _read(db_path)
