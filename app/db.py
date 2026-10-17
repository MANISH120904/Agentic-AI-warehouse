"""Shared local database accessor."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.repositories.sqlite_repository import SqliteRepository


@lru_cache
def get_repository() -> SqliteRepository:
    settings = get_settings()
    return SqliteRepository(db_path=settings.local_db_path, auto_seed=True)


def reset_repository_cache() -> None:
    get_repository.cache_clear()
