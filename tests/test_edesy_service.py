from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.services.call_service import CallService
from app.services.edesy_service import EdesyError, EdesyService


def _mock_transport(handler):
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://voice-agent.edesy.in/api/v1",
    )


def test_auth_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "success": False,
                "error": "Invalid API key",
                "code": "INVALID_API_KEY",
            },
        )

    settings = Settings(
        EDESY_API_KEY="vp_live_fake",
        EDESY_AGENT_ID=1,
        MOCK_MODE=False,
    )
    with EdesyService(settings=settings, client=_mock_transport(handler)) as edesy:
        with pytest.raises(EdesyError) as exc:
            edesy.verify_connectivity()
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_API_KEY"


def test_insufficient_balance():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            402,
            json={
                "success": False,
                "error": "Insufficient credits",
                "code": "CALL_FAILED",
                "details": {"balance": 0},
            },
        )

    settings = Settings(
        EDESY_API_KEY="vp_live_fake",
        EDESY_AGENT_ID=42,
        MOCK_MODE=False,
    )
    with EdesyService(settings=settings, client=_mock_transport(handler)) as edesy:
        with pytest.raises(EdesyError) as exc:
            edesy.create_call(phone_number="+919876543210")
    assert exc.value.status_code == 402


def test_missing_configuration_blocks_live_calls(repo, monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("EDESY_API_KEY", "")
    monkeypatch.setenv("EDESY_AGENT_ID", "")
    from app.config import reset_settings_cache

    reset_settings_cache()
    service = CallService(repo=repo, settings=Settings(MOCK_MODE=False, EDESY_API_KEY=""))
    result = service.create_outbound_call(
        phone_number="+919876543210",
        confirm=True,
    )
    assert result["ok"] is True
    assert result["is_mock"] is True


def test_mock_outbound_call(client):
    response = client.post(
        "/api/calls/outbound",
        json={
            "phone_number": "+919811122233",
            "order_id": "ORD-1002",
            "purpose": "order_status",
            "confirm": True,
            "idempotency_key": "mock-call-1",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_mock"] is True
    assert body["call"]["is_mock"] is True
    assert body["call"]["status"] == "completed"


def test_duplicate_call_prevention(client):
    payload = {
        "phone_number": "+919811122244",
        "order_id": "ORD-1001",
        "purpose": "order_status",
        "confirm": True,
        "idempotency_key": "dup-key-99",
    }
    first = client.post("/api/calls/outbound", json=payload)
    second = client.post("/api/calls/outbound", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["call"]["call_id"] == second.json()["call"]["call_id"]


def test_confirmation_required(client):
    response = client.post(
        "/api/calls/outbound",
        json={"phone_number": "+919811122255", "confirm": False},
    )
    assert response.status_code == 400


def test_create_call_not_retried_on_timeout():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        raise httpx.TimeoutException("timeout")

    settings = Settings(EDESY_API_KEY="vp_live_fake", EDESY_AGENT_ID=1, MOCK_MODE=False)
    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://voice-agent.edesy.in/api/v1",
        timeout=0.1,
    )
    # MockTransport can't raise TimeoutException easily through request path when
    # using raise in handler — use a stub client instead.
    class TimeoutClient:
        def request(self, *args, **kwargs):
            attempts["count"] += 1
            raise httpx.TimeoutException("timeout")

        def close(self):
            return None

    with EdesyService(settings=settings, client=TimeoutClient()) as edesy:  # type: ignore[arg-type]
        with pytest.raises(EdesyError) as exc:
            edesy.create_call(phone_number="+919876543210")
    assert attempts["count"] == 1
    assert exc.value.code == "TIMEOUT"
