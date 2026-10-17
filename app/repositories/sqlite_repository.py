"""Local SQLite persistence for warehouse data.

Collections are stored as JSON documents in a single local file so FastAPI,
Streamlit, and the ADK voice agent all share the same on-disk database.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Callable, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DATA_DIR / "warehouse.db"
SEED_COLLECTIONS = ("orders", "inventory", "shipments", "calls", "feedback")


class SqliteRepository:
    """Thread-safe local SQLite repository with a JsonRepository-compatible API."""

    _lock = threading.RLock()

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        *,
        seed_dir: Optional[Path] = None,
        auto_seed: bool = True,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.seed_dir = Path(seed_dir) if seed_dir else DATA_DIR
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
        if auto_seed:
            self._seed_if_empty()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS collections (
                        name TEXT PRIMARY KEY,
                        payload TEXT NOT NULL
                    )
                    """
                )
                conn.commit()

    def _seed_if_empty(self) -> None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(*) AS c FROM collections").fetchone()
                if row and int(row["c"]) > 0:
                    return
            for name in SEED_COLLECTIONS:
                seed_path = self.seed_dir / f"{name}.json"
                if seed_path.exists():
                    with seed_path.open("r", encoding="utf-8") as handle:
                        payload = json.load(handle)
                    if not isinstance(payload, list):
                        raise ValueError(f"Seed file {seed_path.name} must be a JSON array")
                    self.write_list(name, payload)
                else:
                    self.write_list(name, [])

    def read_list(self, name: str) -> list[dict[str, Any]]:
        key = name.removesuffix(".json")
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT payload FROM collections WHERE name = ?",
                    (key,),
                ).fetchone()
        if row is None:
            return []
        try:
            payload = json.loads(row["payload"])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in SQLite collection '{key}': {exc}") from exc
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON array for collection '{key}'")
        return payload

    def write_list(self, name: str, rows: list[dict[str, Any]]) -> None:
        key = name.removesuffix(".json")
        payload = json.dumps(rows, ensure_ascii=False)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO collections(name, payload) VALUES (?, ?)
                    ON CONFLICT(name) DO UPDATE SET payload = excluded.payload
                    """,
                    (key, payload),
                )
                conn.commit()

    def find_one(
        self,
        name: str,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> Optional[dict[str, Any]]:
        for row in self.read_list(name):
            if predicate(row):
                return row
        return None

    def find_many(
        self,
        name: str,
        predicate: Callable[[dict[str, Any]], bool],
    ) -> list[dict[str, Any]]:
        return [row for row in self.read_list(name) if predicate(row)]

    def append(self, name: str, row: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            rows = self.read_list(name)
            rows.append(row)
            self.write_list(name, rows)
        return row

    def update_one(
        self,
        name: str,
        predicate: Callable[[dict[str, Any]], bool],
        updater: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        with self._lock:
            rows = self.read_list(name)
            updated: Optional[dict[str, Any]] = None
            for index, row in enumerate(rows):
                if predicate(row):
                    updated = updater(dict(row))
                    rows[index] = updated
                    break
            if updated is not None:
                self.write_list(name, rows)
            return updated

    def db_info(self) -> dict[str, Any]:
        counts = {name: len(self.read_list(name)) for name in SEED_COLLECTIONS}
        return {
            "db_path": str(self.db_path.resolve()),
            "exists": self.db_path.exists(),
            "counts": counts,
            "backend": "sqlite",
            "local": True,
        }


# Backwards-compatible alias used across the app.
JsonRepository = SqliteRepository
