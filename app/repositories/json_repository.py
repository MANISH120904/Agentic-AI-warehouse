"""Compatibility export — persistence is local SQLite."""

from app.repositories.sqlite_repository import (  # noqa: F401
    DEFAULT_DB_PATH,
    SqliteRepository,
    SqliteRepository as JsonRepository,
)

__all__ = ["DEFAULT_DB_PATH", "JsonRepository", "SqliteRepository"]
