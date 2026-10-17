"""ADK-callable warehouse tools wrapping local services."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure repo root is importable when ADK loads this package directly.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services.feedback_service import FeedbackService
from app.services.inventory_service import InventoryService
from app.services.order_service import OrderService
from app.services.prediction_service import PredictionService

_order_service = OrderService()
_inventory_service = InventoryService()
_prediction_service = PredictionService()
_feedback_service = FeedbackService()


def get_order_status(order_id: str) -> dict[str, Any]:
    """Look up order status and linked shipment by order ID (e.g. ORD-1001)."""
    try:
        return _order_service.get_order_status(order_id)
    except Exception as exc:  # noqa: BLE001 — surface tool errors to the model
        return {"ok": False, "error": f"Tool error: {exc}", "is_simulated": True}


def get_inventory(product_id: str) -> dict[str, Any]:
    """Look up inventory for a product ID (e.g. SKU-A100)."""
    try:
        return _inventory_service.get_inventory(product_id)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Tool error: {exc}", "is_simulated": True}


def predict_delivery_delay(order_id: str) -> dict[str, Any]:
    """Estimate simulated delivery delay risk for an order using heuristics."""
    try:
        return _prediction_service.predict_delivery_delay(order_id)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Tool error: {exc}", "is_simulated": True}


def record_customer_feedback(
    call_id: str,
    rating: int,
    feedback: str,
) -> dict[str, Any]:
    """Persist customer feedback linked to a call id when possible."""
    try:
        return _feedback_service.record_customer_feedback(
            call_id=call_id or None,
            rating=int(rating),
            feedback=feedback,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Tool error: {exc}", "is_simulated": True}


def get_customer_order_history(customer_id: str) -> dict[str, Any]:
    """Return simulated order history for a customer ID (e.g. CUST-501)."""
    try:
        return _order_service.get_customer_order_history(customer_id)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Tool error: {exc}", "is_simulated": True}


WAREHOUSE_TOOLS = [
    get_order_status,
    get_inventory,
    predict_delivery_delay,
    record_customer_feedback,
    get_customer_order_history,
]
