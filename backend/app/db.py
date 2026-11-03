"""SQLite connection helper and schema.

All statements elsewhere use `?` placeholders; no SQL is built from user input.
"""
import sqlite3
from contextlib import contextmanager
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username_key     TEXT PRIMARY KEY,          -- lowercase login, used as cache key
    login            TEXT NOT NULL,             -- GitHub's original casing, for display
    name             TEXT,
    avatar_url       TEXT,
    bio              TEXT,
    url              TEXT,
    followers        INTEGER NOT NULL DEFAULT 0,
    total_contributions INTEGER NOT NULL DEFAULT 0,
    truncated        INTEGER NOT NULL DEFAULT 0,
    rate_limit_remaining INTEGER,
    rate_limit_reset_at  TEXT,
    fetched_at       REAL NOT NULL              -- unix epoch of last successful fetch
);

CREATE TABLE IF NOT EXISTS repositories (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    username_key     TEXT NOT NULL REFERENCES users(username_key) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    url              TEXT NOT NULL,
    description      TEXT,
    stars            INTEGER NOT NULL DEFAULT 0,
    forks            INTEGER NOT NULL DEFAULT 0,
    is_fork          INTEGER NOT NULL DEFAULT 0,
    is_archived      INTEGER NOT NULL DEFAULT 0,
    pushed_at        TEXT,
    primary_language TEXT,
    primary_language_color TEXT,
    UNIQUE (username_key, name)
);

CREATE TABLE IF NOT EXISTS repo_languages (
    repo_id   INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    language  TEXT NOT NULL,
    color     TEXT,
    size      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (repo_id, language)
);

CREATE TABLE IF NOT EXISTS contribution_days (
    username_key TEXT NOT NULL REFERENCES users(username_key) ON DELETE CASCADE,
    date         TEXT NOT NULL,
    count        INTEGER NOT NULL DEFAULT 0,
    level        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (username_key, date)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS jd_inputs (
    username_key    TEXT PRIMARY KEY,
    job_description TEXT NOT NULL,
    updated_at      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_repos_user ON repositories(username_key);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)  # autocommit; explicit BEGIN for transactions
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
    finally:
        conn.close()


@contextmanager
def get_conn(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE ... COMMIT, rolling back on any exception."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
