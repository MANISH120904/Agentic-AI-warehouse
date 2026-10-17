"""Call management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.models.schemas import CallRecord, OutboundCallRequest, OutboundCallResponse
from app.services.call_service import CallService

router = APIRouter(prefix="/api", tags=["calls"])
call_service = CallService()


@router.get("/calls", response_model=list[CallRecord])
def list_calls() -> list[CallRecord]:
    return [CallRecord(**row) for row in call_service.list_calls()]


@router.get("/calls/{call_id}", response_model=CallRecord)
def get_call(call_id: str) -> CallRecord:
    row = call_service.get_call(call_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Unknown call_id: {call_id}")
    return CallRecord(**row)


@router.post("/calls/{call_id}/refresh", response_model=CallRecord)
def refresh_call(call_id: str) -> CallRecord:
    result = call_service.refresh_call_from_provider(call_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return CallRecord(**result["call"])


@router.post("/calls/outbound", response_model=OutboundCallResponse)
def outbound_call(body: OutboundCallRequest) -> OutboundCallResponse:
    result = call_service.create_outbound_call(
        phone_number=body.phone_number,
        order_id=body.order_id,
        purpose=body.purpose,
        confirm=body.confirm,
        idempotency_key=body.idempotency_key,
        customer_name=body.customer_name,
    )
    if not result.get("ok"):
        status = 400
        if result.get("status_code") == 402:
            status = 402
        elif result.get("code") in {"MISSING_CONFIGURATION", "AUTH_ERROR"}:
            status = 503
        raise HTTPException(
            status_code=status,
            detail={
                "error": result.get("error"),
                "code": result.get("code"),
                "call": result.get("call"),
            },
        )
    return OutboundCallResponse(
        call=CallRecord(**result["call"]),
        message=result["message"],
        is_mock=bool(result.get("is_mock")),
    )


@router.post("/calls/callback")
def call_ended_callback(payload: dict[str, Any]) -> dict[str, Any]:
    """Unsigned Edesy call-ended notification. Always re-fetch for truth."""
    data = payload.get("data") or {}
    conversation_id = data.get("conversation_id") or data.get("conversationId")
    if not conversation_id:
        return {"ok": False, "error": "missing conversation_id"}
    result = call_service.refresh_call_from_provider(str(conversation_id))
    return {
        "ok": bool(result.get("ok")),
        "event": payload.get("event"),
        "message": "Callback accepted; provider record refreshed when possible.",
        "call": result.get("call"),
        "error": result.get("error"),
    }
