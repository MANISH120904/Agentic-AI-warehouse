"""Request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Order(BaseModel):
    order_id: str
    customer_id: str
    customer_name: str
    phone: str
    status: str
    warehouse: str
    estimated_delivery: str
    shipment_id: str
    product_ids: list[str] = Field(default_factory=list)
    is_simulated: bool = True


class Shipment(BaseModel):
    shipment_id: str
    order_id: str
    current_status: str
    last_updated: str
    delay_risk: str
    delay_reason: str = ""
    weather_risk: str = "none"
    is_simulated: bool = True


class InventoryItem(BaseModel):
    product_id: str
    product_name: str
    warehouse: str
    quantity_available: int
    reorder_threshold: int
    is_simulated: bool = True

    @property
    def is_low(self) -> bool:
        return self.quantity_available <= self.reorder_threshold


class DelayRiskResult(BaseModel):
    order_id: str
    risk: Literal["low", "medium", "high"]
    risk_score: int
    reasons: list[str]
    is_simulated: bool = True


class CallRecord(BaseModel):
    call_id: str
    provider_call_id: Optional[str] = None
    conversation_id: Optional[str] = None
    phone_number: str
    order_id: Optional[str] = None
    purpose: str = ""
    status: str
    duration: Optional[int] = None
    outcome: Optional[str] = None
    transcript: Optional[str] = None
    is_mock: bool = False
    idempotency_key: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackCreate(BaseModel):
    call_id: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    feedback: str = Field(min_length=1, max_length=2000)
    customer_id: Optional[str] = None


class FeedbackRecord(FeedbackCreate):
    feedback_id: str
    created_at: str
    is_simulated: bool = True


class OutboundCallRequest(BaseModel):
    phone_number: str
    order_id: Optional[str] = None
    purpose: str = Field(default="order_status", min_length=1, max_length=200)
    confirm: bool = False
    idempotency_key: Optional[str] = None
    customer_name: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if not cleaned:
            raise ValueError("phone_number is required")
        digits = cleaned[1:] if cleaned.startswith("+") else cleaned
        if not digits.isdigit() or len(digits) < 10:
            raise ValueError(
                "phone_number must be E.164 or at least 10 digits (e.g. +919876543210)"
            )
        return cleaned if cleaned.startswith("+") else f"+{cleaned}"


class OutboundCallResponse(BaseModel):
    call: CallRecord
    message: str
    is_mock: bool


class HealthResponse(BaseModel):
    status: str
    app_env: str
    mock_mode: bool
    edesy_configured: bool
    google_configured: bool
    telephony_ready: bool
    version: str


class DashboardSummary(BaseModel):
    total_orders: int
    high_risk_shipments: int
    calls_completed: int
    calls_failed: int
    feedback_count: int
    recent_calls: list[CallRecord]
    average_rating: Optional[float] = None


class SettingsPublic(BaseModel):
    app_env: str
    mock_mode: bool
    edesy_configured: bool
    google_configured: bool
    telephony_ready: bool
    edesy_api_base_url: str
    edesy_agent_id: Optional[int]
    edesy_api_key_masked: str
    google_api_key_masked: str
    public_base_url: str
    adk_model: str
    local_db: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
