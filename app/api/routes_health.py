"""Health and settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import get_settings
from app.models.schemas import HealthResponse, SettingsPublic
from app.services.agent_service import AgentService
from app.services.edesy_service import EdesyError, EdesyService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        mock_mode=settings.mock_mode,
        edesy_configured=settings.edesy_configured,
        google_configured=settings.google_configured,
        telephony_ready=settings.telephony_ready,
        version=__version__,
    )


@router.get("/api/local/db")
def local_db_status() -> dict:
    from app.db import get_repository

    info = get_repository().db_info()
    return {"ok": True, **info}


@router.get("/api/metrics/execution")
def execution_metrics() -> dict:
    """Recent request latency summary (target: sub-500ms tool/API paths)."""
    from app.services.timing_service import timing_service

    summary = timing_service.summary()
    return {"ok": True, "low_execution_time": True, **summary}


@router.get("/api/settings", response_model=SettingsPublic)
def settings_public() -> SettingsPublic:
    return SettingsPublic(**AgentService().public_status())


@router.get("/api/edesy/status")
def edesy_status() -> dict:
    settings = get_settings()
    if not settings.edesy_configured:
        return {
            "ok": False,
            "configured": False,
            "error": "EDESY_API_KEY is not set",
        }
    try:
        with EdesyService(settings) as edesy:
            result = edesy.verify_connectivity()
        return result
    except EdesyError as exc:
        return {
            "ok": False,
            "configured": True,
            "error": exc.message,
            "code": exc.code,
            "status_code": exc.status_code,
        }
