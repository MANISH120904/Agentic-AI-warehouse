"""Thread-safe JSON file repository for simulated warehouse data."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class JsonRepository:
    """Load and persist list-based JSON datasets with a process-wide lock."""

    _lock = threading.RLock()

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        if not name.endswith(".json"):
            name = f"{name}.json"
        return self.data_dir / name

    def read_list(self, name: str) -> list[dict[str, Any]]:
        path = self._path(name)
        with self._lock:
            try:
                if not path.exists():
                    return []
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path.name}: {exc}") from exc
            except OSError as exc:
                raise RuntimeError(f"Unable to read {path.name}: {exc}") from exc
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON array in {path.name}")
        return payload

    def write_list(self, name: str, rows: list[dict[str, Any]]) -> None:
        path = self._path(name)
        with self._lock:
            try:
                tmp = path.with_suffix(".tmp")
                with tmp.open("w", encoding="utf-8") as handle:
                    json.dump(rows, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                tmp.replace(path)
            except OSError as exc:
                raise RuntimeError(f"Unable to write {path.name}: {exc}") from exc

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
