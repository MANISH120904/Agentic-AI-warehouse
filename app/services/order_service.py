"""Order lookup and customer history."""

from __future__ import annotations

from typing import Any, Optional

from app.repositories.json_repository import JsonRepository


class OrderService:
    def __init__(self, repo: Optional[JsonRepository] = None) -> None:
        self.repo = repo or JsonRepository()

    def list_orders(self) -> list[dict[str, Any]]:
        return self.repo.read_list("orders")

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        order_id = (order_id or "").strip().upper()
        if not order_id:
            return {"ok": False, "error": "order_id is required", "is_simulated": True}

        order = self.repo.find_one(
            "orders",
            lambda row: str(row.get("order_id", "")).upper() == order_id,
        )
        if not order:
            return {
                "ok": False,
                "error": f"Unknown order_id: {order_id}",
                "order_id": order_id,
                "is_simulated": True,
            }

        shipment = self.repo.find_one(
            "shipments",
            lambda row: str(row.get("shipment_id", "")) == order.get("shipment_id"),
        )
        return {
            "ok": True,
            "order": order,
            "shipment": shipment,
            "is_simulated": True,
        }

    def get_customer_order_history(self, customer_id: str) -> dict[str, Any]:
        customer_id = (customer_id or "").strip().upper()
        if not customer_id:
            return {
                "ok": False,
                "error": "customer_id is required",
                "is_simulated": True,
            }

        orders = self.repo.find_many(
            "orders",
            lambda row: str(row.get("customer_id", "")).upper() == customer_id,
        )
        if not orders:
            return {
                "ok": False,
                "error": f"No orders for customer_id: {customer_id}",
                "customer_id": customer_id,
                "orders": [],
                "is_simulated": True,
            }
        return {
            "ok": True,
            "customer_id": customer_id,
            "count": len(orders),
            "orders": orders,
            "is_simulated": True,
        }
