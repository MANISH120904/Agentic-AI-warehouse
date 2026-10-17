"""Helpers for ADK / configuration status (no secrets exposed)."""

from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings


class AgentService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def public_status(self) -> dict[str, Any]:
        from app.db import get_repository

        notes: list[str] = []
        db_info = get_repository().db_info()
        notes.append(
            f"Local SQLite DB at {db_info['db_path']} — FastAPI, dashboard, and ADK "
            "voice tools all read/write this file."
        )
        if self.settings.mock_mode:
            notes.append("MOCK_MODE is on — outbound phone calls are simulated.")
        if not self.settings.edesy_configured:
            notes.append("Edesy API key not configured (phone outbound optional).")
        elif self.settings.edesy_agent_id is None:
            notes.append("EDESY_AGENT_ID missing — live outbound calls will fail.")
        if not self.settings.google_configured:
            notes.append(
                "GOOGLE_API_KEY not configured — set it to talk to the local ADK voice agent."
            )
        else:
            notes.append(
                "Local voice path: run `adk web` from the app/ folder; the agent uses "
                "local SQLite tools (orders, inventory, delay risk, feedback)."
            )
        if not self.settings.public_base_url:
            notes.append(
                "PUBLIC_BASE_URL empty — hosted Edesy phone agent cannot call this API "
                "over the internet (local ADK does not need it)."
            )
        notes.append(
            "Local ADK browser voice is the supported way to speak with local DB data. "
            "Edesy PSTN audio is a separate hosted path."
        )
        return {
            "app_env": self.settings.app_env,
            "mock_mode": self.settings.mock_mode,
            "edesy_configured": self.settings.edesy_configured,
            "google_configured": self.settings.google_configured,
            "telephony_ready": self.settings.telephony_ready,
            "edesy_api_base_url": self.settings.edesy_api_base_url,
            "edesy_agent_id": self.settings.edesy_agent_id,
            "edesy_api_key_masked": self.settings.mask_secret(self.settings.edesy_api_key),
            "google_api_key_masked": self.settings.mask_secret(self.settings.google_api_key),
            "public_base_url": self.settings.public_base_url or "(not set)",
            "adk_model": self.settings.adk_model,
            "local_db": db_info,
            "notes": notes,
        }
