"""Transparent heuristic delay-risk estimator (not a trained model)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from app.db import get_repository
from app.repositories.sqlite_repository import SqliteRepository
from app.services.order_service import OrderService


class PredictionService:
    WEATHER_SCORES = {
        "none": 0,
        "fog": 10,
        "light_rain": 15,
        "heavy_rain": 30,
        "storm": 40,
    }

    STATUS_SCORES = {
        "delivered": 0,
        "out_for_delivery": 5,
        "in_transit": 10,
        "at_hub": 15,
        "packed": 12,
        "processing": 10,
        "awaiting_pickup": 18,
        "delayed": 35,
        "cancelled": 0,
    }

    def __init__(
        self,
        repo: Optional[SqliteRepository] = None,
        order_service: Optional[OrderService] = None,
    ) -> None:
        self.repo = repo or get_repository()
        self.order_service = order_service or OrderService(self.repo)

    def predict_delivery_delay(self, order_id: str) -> dict[str, Any]:
        lookup = self.order_service.get_order_status(order_id)
        if not lookup.get("ok"):
            return {
                "ok": False,
                "order_id": (order_id or "").strip().upper(),
                "error": lookup.get("error", "Order not found"),
                "risk": "low",
                "risk_score": 0,
                "reasons": [],
                "is_simulated": True,
            }

        order = lookup["order"]
        shipment = lookup.get("shipment") or {}
        score = 0
        reasons: list[str] = []

        status = str(shipment.get("current_status") or order.get("status") or "").lower()
        status_score = self.STATUS_SCORES.get(status, 10)
        score += status_score
        if status == "delayed":
            reasons.append("Shipment status is already marked delayed.")
        elif status_score >= 15:
            reasons.append(f"Shipment status '{status}' adds operational risk.")

        indicated = str(shipment.get("delay_risk", "low")).lower()
        if indicated == "high":
            score += 30
            reasons.append("Simulated shipment record flags high delay risk.")
        elif indicated == "medium":
            score += 15
            reasons.append("Simulated shipment record flags medium delay risk.")

        delay_reason = str(shipment.get("delay_reason") or "").strip()
        if delay_reason:
            score += 10
            reasons.append(delay_reason)

        weather = str(shipment.get("weather_risk", "none")).lower()
        weather_score = self.WEATHER_SCORES.get(weather, 0)
        if weather_score:
            score += weather_score
            reasons.append(f"Weather risk in simulated data: {weather}.")

        eta_penalty = self._eta_penalty(str(order.get("estimated_delivery", "")))
        score += eta_penalty
        if eta_penalty >= 20:
            reasons.append("Estimated delivery date is already overdue in sample data.")
        elif eta_penalty >= 10:
            reasons.append("Estimated delivery is within one day.")

        score = max(0, min(100, score))
        if score >= 55:
            risk = "high"
        elif score >= 30:
            risk = "medium"
        else:
            risk = "low"

        if not reasons:
            reasons.append("No elevated delay indicators in simulated data.")

        return {
            "ok": True,
            "order_id": order["order_id"],
            "risk": risk,
            "risk_score": score,
            "reasons": reasons,
            "is_simulated": True,
            "disclaimer": (
                "Heuristic estimate from local sample data — not a trained predictive model "
                "and not a live carrier ETA."
            ),
        }

    def _eta_penalty(self, estimated_delivery: str) -> int:
        if not estimated_delivery:
            return 5
        try:
            eta = date.fromisoformat(estimated_delivery[:10])
        except ValueError:
            return 5
        today = datetime.utcnow().date()
        delta = (eta - today).days
        if delta < 0:
            return 25
        if delta <= 1:
            return 12
        return 0

    def count_high_risk_shipments(self) -> int:
        count = 0
        for shipment in self.repo.read_list("shipments"):
            order_id = str(shipment.get("order_id", ""))
            result = self.predict_delivery_delay(order_id)
            if result.get("risk") == "high":
                count += 1
        return count
