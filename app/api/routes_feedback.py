"""Feedback and dashboard summary routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import DashboardSummary, FeedbackCreate, FeedbackRecord
from app.services.call_service import CallService
from app.services.feedback_service import FeedbackService
from app.services.order_service import OrderService
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api", tags=["feedback"])

feedback_service = FeedbackService()
call_service = CallService()
order_service = OrderService()
prediction_service = PredictionService()


@router.post("/feedback", response_model=FeedbackRecord)
def create_feedback(body: FeedbackCreate) -> FeedbackRecord:
    result = feedback_service.record_customer_feedback(
        call_id=body.call_id,
        rating=body.rating,
        feedback=body.feedback,
        customer_id=body.customer_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return FeedbackRecord(**result["feedback"])


@router.get("/feedback", response_model=list[FeedbackRecord])
def list_feedback() -> list[FeedbackRecord]:
    return [FeedbackRecord(**row) for row in feedback_service.list_feedback()]


@router.post("/tools/record_customer_feedback")
def tool_record_feedback(payload: dict) -> dict:
    return feedback_service.record_customer_feedback(
        call_id=payload.get("call_id"),
        rating=int(payload.get("rating", 0) or 0),
        feedback=str(payload.get("feedback") or ""),
        customer_id=payload.get("customer_id"),
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary() -> DashboardSummary:
    calls = call_service.list_calls()
    completed = sum(
        1
        for call in calls
        if str(call.get("status", "")).lower() in {"completed", "complete"}
    )
    failed = sum(
        1 for call in calls if str(call.get("status", "")).lower() in {"failed", "fail"}
    )
    return DashboardSummary(
        total_orders=len(order_service.list_orders()),
        high_risk_shipments=prediction_service.count_high_risk_shipments(),
        calls_completed=completed,
        calls_failed=failed,
        feedback_count=len(feedback_service.list_feedback()),
        recent_calls=calls[:8],
        average_rating=feedback_service.average_rating(),
    )
