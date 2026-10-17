"""Order and inventory and delay-risk routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import DelayRiskResult, InventoryItem, Order
from app.services.inventory_service import InventoryService
from app.services.order_service import OrderService
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api", tags=["orders"])

order_service = OrderService()
inventory_service = InventoryService()
prediction_service = PredictionService()


@router.get("/orders", response_model=list[Order])
def list_orders() -> list[Order]:
    return [Order(**row) for row in order_service.list_orders()]


@router.get("/orders/{order_id}")
def get_order(order_id: str) -> dict:
    result = order_service.get_order_status(order_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/orders/{order_id}/delay-risk", response_model=DelayRiskResult)
def get_delay_risk(order_id: str) -> DelayRiskResult:
    result = prediction_service.predict_delivery_delay(order_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return DelayRiskResult(**result)


@router.get("/inventory")
def list_inventory() -> list[InventoryItem]:
    return [InventoryItem(**row) for row in inventory_service.list_inventory()]


@router.get("/inventory/{product_id}")
def get_inventory(product_id: str) -> dict:
    result = inventory_service.get_inventory(product_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/customers/{customer_id}/orders")
def customer_orders(customer_id: str) -> dict:
    result = order_service.get_customer_order_history(customer_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


# Tool-shaped endpoints for Edesy HTTP functions (POST body with placeholders)
@router.post("/tools/get_order_status")
def tool_get_order_status(payload: dict) -> dict:
    order_id = payload.get("order_id") or payload.get("orderId")
    return order_service.get_order_status(str(order_id or ""))


@router.post("/tools/get_inventory")
def tool_get_inventory(payload: dict) -> dict:
    product_id = payload.get("product_id") or payload.get("productId")
    return inventory_service.get_inventory(str(product_id or ""))


@router.post("/tools/predict_delivery_delay")
def tool_predict_delivery_delay(payload: dict) -> dict:
    order_id = payload.get("order_id") or payload.get("orderId")
    return prediction_service.predict_delivery_delay(str(order_id or ""))


@router.post("/tools/get_customer_order_history")
def tool_customer_history(payload: dict) -> dict:
    customer_id = payload.get("customer_id") or payload.get("customerId")
    return order_service.get_customer_order_history(str(customer_id or ""))
