"""Customer feedback persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.repositories.json_repository import JsonRepository


class FeedbackService:
    def __init__(self, repo: Optional[JsonRepository] = None) -> None:
        self.repo = repo or JsonRepository()

    def list_feedback(self) -> list[dict[str, Any]]:
        rows = self.repo.read_list("feedback")
        return sorted(rows, key=lambda row: row.get("created_at", ""), reverse=True)

    def record_customer_feedback(
        self,
        call_id: Optional[str],
        rating: int,
        feedback: str,
        customer_id: Optional[str] = None,
    ) -> dict[str, Any]:
        if rating < 1 or rating > 5:
            return {
                "ok": False,
                "error": "rating must be an integer from 1 to 5",
                "is_simulated": True,
            }
        text = (feedback or "").strip()
        if not text:
            return {
                "ok": False,
                "error": "feedback text is required",
                "is_simulated": True,
            }

        if call_id:
            call = self.repo.find_one(
                "calls",
                lambda row: str(row.get("call_id", "")) == call_id
                or str(row.get("conversation_id", "")) == call_id,
            )
            if call is None:
                return {
                    "ok": False,
                    "error": f"Unknown call_id: {call_id}",
                    "is_simulated": True,
                }

        record = {
            "feedback_id": f"FB-{uuid4().hex[:10]}",
            "call_id": call_id,
            "rating": int(rating),
            "feedback": text,
            "customer_id": customer_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_simulated": True,
        }
        self.repo.append("feedback", record)
        return {"ok": True, "feedback": record, "is_simulated": True}

    def average_rating(self) -> Optional[float]:
        rows = self.list_feedback()
        if not rows:
            return None
        total = sum(int(row.get("rating", 0)) for row in rows)
        return round(total / len(rows), 2)
