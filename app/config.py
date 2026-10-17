"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.repositories.sqlite_repository import DEFAULT_DB_PATH


class Settings(BaseSettings):
    """Runtime configuration for WarehouseVoiceAI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    mock_mode: bool = Field(default=True, alias="MOCK_MODE")
    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8765, alias="API_PORT")
    http_timeout_seconds: float = Field(default=30.0, alias="HTTP_TIMEOUT_SECONDS")
    warehouse_db_path: str = Field(
        default=str(DEFAULT_DB_PATH),
        alias="WAREHOUSE_DB_PATH",
    )

    edesy_api_key: str = Field(default="", alias="EDESY_API_KEY")
    edesy_api_base_url: str = Field(
        default="https://voice-agent.edesy.in/api/v1",
        alias="EDESY_API_BASE_URL",
    )
    edesy_agent_id: Optional[int] = Field(default=None, alias="EDESY_AGENT_ID")
    edesy_from_number: str = Field(default="", alias="EDESY_FROM_NUMBER")
    edesy_phone_number: str = Field(default="", alias="EDESY_PHONE_NUMBER")

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_genai_use_enterprise: str = Field(
        default="FALSE",
        alias="GOOGLE_GENAI_USE_ENTERPRISE",
    )
    adk_model: str = Field(
        default="gemini-2.5-flash-native-audio-preview-09-2025",
        alias="ADK_MODEL",
    )

    @field_validator("edesy_agent_id", mode="before")
    @classmethod
    def empty_agent_id_to_none(cls, value: object) -> object:
        if value is None or value == "":
            return None
        return value

    @property
    def local_db_path(self) -> Path:
        return Path(self.warehouse_db_path).expanduser().resolve()

    @property
    def edesy_configured(self) -> bool:
        return bool(self.edesy_api_key.strip())

    @property
    def google_configured(self) -> bool:
        return bool(self.google_api_key.strip())

    @property
    def telephony_ready(self) -> bool:
        return (
            not self.mock_mode
            and self.edesy_configured
            and self.edesy_agent_id is not None
        )

    def mask_secret(self, value: str, visible: int = 4) -> str:
        text = (value or "").strip()
        if not text:
            return "(not set)"
        if len(text) <= visible * 2:
            return "*" * len(text)
        return f"{text[:visible]}…{text[-visible:]}"

    def validate_for_live_calls(self) -> list[str]:
        """Return actionable errors when live telephony is requested."""
        errors: list[str] = []
        if self.mock_mode:
            errors.append(
                "MOCK_MODE=true. Set MOCK_MODE=false to place real Edesy calls."
            )
        if not self.edesy_api_key.strip():
            errors.append(
                "EDESY_API_KEY is missing. Create a key in Edesy → Settings → API Keys."
            )
        if self.edesy_agent_id is None:
            errors.append(
                "EDESY_AGENT_ID is missing. Create or list an agent via GET /api/v1/agents."
            )
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
