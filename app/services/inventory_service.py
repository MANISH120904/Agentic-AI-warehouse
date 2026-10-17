"""Inventory lookup."""

from __future__ import annotations

from typing import Any, Optional

from app.db import get_repository
from app.repositories.sqlite_repository import SqliteRepository


class InventoryService:
    def __init__(self, repo: Optional[SqliteRepository] = None) -> None:
        self.repo = repo or get_repository()

    def list_inventory(self) -> list[dict[str, Any]]:
        return self.repo.read_list("inventory")

    def get_inventory(self, product_id: str) -> dict[str, Any]:
        product_id = (product_id or "").strip().upper()
        if not product_id:
            return {
                "ok": False,
                "error": "product_id is required",
                "is_simulated": True,
            }

        item = self.repo.find_one(
            "inventory",
            lambda row: str(row.get("product_id", "")).upper() == product_id,
        )
        if not item:
            return {
                "ok": False,
                "error": f"Unknown product_id: {product_id}",
                "product_id": product_id,
                "is_simulated": True,
            }

        quantity = int(item.get("quantity_available", 0))
        threshold = int(item.get("reorder_threshold", 0))
        return {
            "ok": True,
            "product": item,
            "is_low": quantity <= threshold,
            "is_simulated": True,
        }
