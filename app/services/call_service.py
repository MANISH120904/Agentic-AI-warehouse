"""Outbound call orchestration with mock mode and duplicate prevention."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.config import Settings, get_settings
from app.repositories.json_repository import JsonRepository
from app.services.edesy_service import EdesyError, EdesyService
from app.services.order_service import OrderService


class CallService:
    def __init__(
        self,
        repo: Optional[JsonRepository] = None,
        settings: Optional[Settings] = None,
        edesy: Optional[EdesyService] = None,
        order_service: Optional[OrderService] = None,
    ) -> None:
        self.repo = repo or JsonRepository()
        self.settings = settings or get_settings()
        self.edesy = edesy or EdesyService(self.settings)
        self.order_service = order_service or OrderService(self.repo)

    def list_calls(self) -> list[dict[str, Any]]:
        rows = self.repo.read_list("calls")
        return sorted(rows, key=lambda row: row.get("created_at", ""), reverse=True)

    def get_call(self, call_id: str) -> Optional[dict[str, Any]]:
        return self.repo.find_one(
            "calls",
            lambda row: str(row.get("call_id", "")) == call_id
            or str(row.get("conversation_id", "")) == call_id
            or str(row.get("provider_call_id", "")) == call_id,
        )

    def create_outbound_call(
        self,
        *,
        phone_number: str,
        order_id: Optional[str] = None,
        purpose: str = "order_status",
        confirm: bool = False,
        idempotency_key: Optional[str] = None,
        customer_name: Optional[str] = None,
    ) -> dict[str, Any]:
        if not confirm:
            return {
                "ok": False,
                "error": "Set confirm=true after reviewing the call preview.",
                "code": "CONFIRMATION_REQUIRED",
            }

        if idempotency_key:
            existing = self.repo.find_one(
                "calls",
                lambda row: str(row.get("idempotency_key", "")) == idempotency_key,
            )
            if existing:
                return {
                    "ok": True,
                    "call": existing,
                    "message": "Duplicate submission ignored; returning existing call.",
                    "is_mock": bool(existing.get("is_mock")),
                    "duplicate": True,
                }

        variables: dict[str, Any] = {}
        if order_id:
            lookup = self.order_service.get_order_status(order_id)
            if lookup.get("ok"):
                order = lookup["order"]
                variables["order_id"] = order["order_id"]
                variables["customer_name"] = customer_name or order.get("customer_name")
            else:
                variables["order_id"] = order_id
                if customer_name:
                    variables["customer_name"] = customer_name
        elif customer_name:
            variables["customer_name"] = customer_name

        now = datetime.now(timezone.utc).isoformat()
        local_id = f"CALL-{uuid4().hex[:12]}"

        use_mock = self.settings.mock_mode or not self.settings.telephony_ready
        if use_mock:
            record = {
                "call_id": local_id,
                "provider_call_id": f"MOCK-{uuid4().hex[:10]}",
                "conversation_id": f"mock-conv-{uuid4().hex[:8]}",
                "phone_number": phone_number,
                "order_id": order_id,
                "purpose": purpose,
                "status": "completed",
                "duration": 42,
                "outcome": "SIMULATED_SUCCESS",
                "transcript": (
                    "Agent: Hello, this is a simulated warehouse support call.\n"
                    f"User: Checking order {order_id or 'N/A'}.\n"
                    "Agent: This is MOCK_MODE — no real phone call was placed."
                ),
                "is_mock": True,
                "idempotency_key": idempotency_key,
                "error": None,
                "created_at": now,
                "updated_at": now,
                "metadata": {
                    "purpose": purpose,
                    "variables": variables,
                    "mock_reason": (
                        "MOCK_MODE enabled"
                        if self.settings.mock_mode
                        else "Edesy not fully configured"
                    ),
                },
            }
            self.repo.append("calls", record)
            return {
                "ok": True,
                "call": record,
                "message": "Simulated call recorded. No real telephony was used.",
                "is_mock": True,
                "duplicate": False,
            }

        config_errors = self.settings.validate_for_live_calls()
        if config_errors:
            return {
                "ok": False,
                "error": "; ".join(config_errors),
                "code": "MISSING_CONFIGURATION",
            }

        callback_url = None
        if self.settings.public_base_url:
            callback_url = (
                f"{self.settings.public_base_url.rstrip('/')}/api/calls/callback"
            )

        try:
            placed = self.edesy.create_call(
                phone_number=phone_number,
                variables=variables or None,
                metadata={
                    "local_call_id": local_id,
                    "purpose": purpose,
                    "idempotency_key": idempotency_key,
                },
                callback_url=callback_url,
            )
        except EdesyError as exc:
            failed = {
                "call_id": local_id,
                "provider_call_id": None,
                "conversation_id": None,
                "phone_number": phone_number,
                "order_id": order_id,
                "purpose": purpose,
                "status": "failed",
                "duration": None,
                "outcome": exc.code or "PROVIDER_ERROR",
                "transcript": None,
                "is_mock": False,
                "idempotency_key": idempotency_key,
                "error": exc.message,
                "created_at": now,
                "updated_at": now,
                "metadata": {"variables": variables},
            }
            self.repo.append("calls", failed)
            return {
                "ok": False,
                "call": failed,
                "error": exc.message,
                "code": exc.code,
                "status_code": exc.status_code,
                "is_mock": False,
            }

        record = {
            "call_id": local_id,
            "provider_call_id": placed.get("call_sid"),
            "conversation_id": placed.get("conversation_id"),
            "phone_number": phone_number,
            "order_id": order_id,
            "purpose": purpose,
            "status": placed.get("status") or "initiated",
            "duration": None,
            "outcome": None,
            "transcript": None,
            "is_mock": False,
            "idempotency_key": idempotency_key,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "metadata": {"variables": variables, "provider": "edesy_voice_agent"},
        }
        self.repo.append("calls", record)
        return {
            "ok": True,
            "call": record,
            "message": "Outbound call requested via Edesy hosted Voice Agent API.",
            "is_mock": False,
            "duplicate": False,
        }

    def refresh_call_from_provider(self, call_id: str) -> dict[str, Any]:
        local = self.get_call(call_id)
        if not local:
            return {"ok": False, "error": f"Unknown call_id: {call_id}"}
        if local.get("is_mock"):
            return {"ok": True, "call": local, "message": "Mock call; no provider refresh."}
        conversation_id = local.get("conversation_id")
        if not conversation_id:
            return {"ok": False, "error": "Call has no provider conversation id", "call": local}

        try:
            remote = self.edesy.get_call(conversation_id)
            transcript = remote.get("full_text")
            if not transcript:
                try:
                    transcript_payload = self.edesy.get_transcript(conversation_id)
                    transcript = transcript_payload.get("full_text")
                except EdesyError:
                    transcript = local.get("transcript")
        except EdesyError as exc:
            return {"ok": False, "error": exc.message, "code": exc.code, "call": local}

        updated = self.repo.update_one(
            "calls",
            lambda row: str(row.get("call_id", "")) == local["call_id"],
            lambda row: {
                **row,
                "status": remote.get("status") or row.get("status"),
                "duration": remote.get("duration"),
                "outcome": remote.get("disposition") or row.get("outcome"),
                "transcript": transcript or row.get("transcript"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    **(row.get("metadata") or {}),
                    "summary": remote.get("summary"),
                },
            },
        )
        return {"ok": True, "call": updated, "message": "Call refreshed from Edesy."}
