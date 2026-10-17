"""Edesy Hosted Voice Agent API client (voice-agent.edesy.in)."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EdesyError(Exception):
    """Normalized provider error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        details: Optional[Any] = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        self.retryable = retryable


class EdesyService:
    """Thin client for the hosted Voice Agent REST API.

    Uses Authorization Bearer / X-API-Key with vp_live_ / vp_test_ keys.
    Does not mix with the SIP trunk API at voice-api.edesy.in.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.settings.edesy_api_base_url.rstrip("/"),
                timeout=self.settings.http_timeout_seconds,
                headers={
                    "Authorization": f"Bearer {self.settings.edesy_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "EdesyService":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        allow_retry_once: bool = False,
    ) -> dict[str, Any]:
        if not self.settings.edesy_api_key.strip():
            raise EdesyError(
                "EDESY_API_KEY is not configured",
                code="MISSING_CONFIGURATION",
                status_code=503,
            )

        client = self._get_client()
        url = path if path.startswith("/") else f"/{path}"
        attempt = 0
        while True:
            attempt += 1
            try:
                response = client.request(method, url, json=json, params=params)
            except httpx.TimeoutException as exc:
                # Never retry mutating call creation after timeout.
                raise EdesyError(
                    "Edesy request timed out. Do not assume the call was placed; "
                    "check call history before retrying outbound calls.",
                    code="TIMEOUT",
                    retryable=False,
                ) from exc
            except httpx.HTTPError as exc:
                if allow_retry_once and attempt == 1:
                    logger.warning("Transient Edesy transport error; retrying once")
                    continue
                raise EdesyError(
                    "Unable to reach Edesy API",
                    code="TRANSPORT_ERROR",
                    retryable=True,
                ) from exc

            request_id = response.headers.get("x-request-id") or response.headers.get(
                "X-Request-Id"
            )
            if request_id:
                logger.info("Edesy %s %s request_id=%s status=%s", method, url, request_id, response.status_code)

            payload: dict[str, Any]
            try:
                payload = response.json()
            except ValueError:
                payload = {"success": False, "error": response.text, "code": "INVALID_JSON"}

            if response.status_code == 429:
                raise EdesyError(
                    payload.get("error") or "Rate limit exceeded",
                    status_code=429,
                    code=payload.get("code") or "RATE_LIMIT_EXCEEDED",
                    details=payload.get("details"),
                    retryable=True,
                )

            if response.status_code == 402 or payload.get("code") in {
                "INSUFFICIENT_BALANCE",
                "CALL_FAILED",
            } and response.status_code == 402:
                raise EdesyError(
                    payload.get("error")
                    or "Insufficient Edesy credits / balance for this call",
                    status_code=402,
                    code=payload.get("code") or "INSUFFICIENT_BALANCE",
                    details=payload.get("details") or payload.get("data"),
                    retryable=False,
                )

            if response.status_code in {401, 403}:
                raise EdesyError(
                    payload.get("error") or "Edesy authentication or scope failure",
                    status_code=response.status_code,
                    code=payload.get("code") or "AUTH_ERROR",
                    details=payload.get("details"),
                    retryable=False,
                )

            if response.status_code >= 500:
                if allow_retry_once and attempt == 1 and response.status_code in {503, 504}:
                    continue
                raise EdesyError(
                    payload.get("error") or "Edesy server error",
                    status_code=response.status_code,
                    code=payload.get("code") or "SERVER_ERROR",
                    details=payload.get("details"),
                    retryable=response.status_code in {503, 504},
                )

            if response.status_code >= 400 or payload.get("success") is False:
                raise EdesyError(
                    payload.get("error") or f"Edesy request failed ({response.status_code})",
                    status_code=response.status_code,
                    code=payload.get("code") or "REQUEST_FAILED",
                    details=payload.get("details"),
                    retryable=False,
                )

            data = payload.get("data", payload)
            if isinstance(data, dict):
                return data
            return {"data": data}

    def verify_connectivity(self) -> dict[str, Any]:
        """Probe API auth by listing agents (read-only)."""
        data = self._request("GET", "/agents", params={"limit": 1}, allow_retry_once=True)
        agents = data.get("agents", data if isinstance(data, list) else [])
        return {
            "ok": True,
            "configured": True,
            "agent_count": data.get("total", len(agents) if isinstance(agents, list) else 0),
            "base_url": self.settings.edesy_api_base_url,
        }

    def list_agents(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return self._request(
            "GET",
            "/agents",
            params={"limit": limit, "offset": offset},
            allow_retry_once=True,
        )

    def get_agent(self, agent_id: int) -> dict[str, Any]:
        return self._request("GET", f"/agents/{agent_id}", allow_retry_once=True)

    def create_call(
        self,
        *,
        phone_number: str,
        agent_id: Optional[int] = None,
        variables: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        callback_url: Optional[str] = None,
        from_number: Optional[str] = None,
    ) -> dict[str, Any]:
        """Place an outbound call. Never automatically retried on timeout."""
        resolved_agent = agent_id if agent_id is not None else self.settings.edesy_agent_id
        if resolved_agent is None:
            raise EdesyError(
                "EDESY_AGENT_ID is required to place a call",
                code="MISSING_AGENT_ID",
                status_code=400,
            )

        body: dict[str, Any] = {
            "agentId": int(resolved_agent),
            "phoneNumber": phone_number,
        }
        if variables:
            body["variables"] = variables
        if metadata:
            body["metadata"] = metadata
        if callback_url:
            body["callbackUrl"] = callback_url
        caller = from_number or self.settings.edesy_from_number
        if caller:
            body["fromNumber"] = caller

        # Critical: allow_retry_once=False so timeouts never double-dial.
        data = self._request("POST", "/calls", json=body, allow_retry_once=False)
        return {
            "conversation_id": data.get("conversationId") or data.get("conversation_id"),
            "call_sid": data.get("callSid") or data.get("call_sid"),
            "status": data.get("status", "initiated"),
            "raw": data,
        }

    def get_call(self, conversation_id: str) -> dict[str, Any]:
        data = self._request(
            "GET",
            f"/calls/{conversation_id}",
            allow_retry_once=True,
        )
        return self._normalize_call(data)

    def list_calls(
        self,
        *,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
        phone_number: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if agent_id is not None:
            params["agentId"] = agent_id
        if status:
            params["status"] = status
        if phone_number:
            params["phoneNumber"] = phone_number
        data = self._request("GET", "/calls", params=params, allow_retry_once=True)
        calls = data.get("calls", [])
        return {
            "calls": [self._normalize_call(item) for item in calls],
            "total": data.get("total", len(calls)),
            "limit": data.get("limit", limit),
            "offset": data.get("offset", offset),
        }

    def get_transcript(self, conversation_id: str) -> dict[str, Any]:
        data = self._request(
            "GET",
            f"/calls/{conversation_id}/transcript",
            allow_retry_once=True,
        )
        return {
            "conversation_id": data.get("conversationId") or conversation_id,
            "transcript": data.get("transcript", []),
            "full_text": data.get("fullText") or data.get("full_text"),
            "raw": data,
        }

    def register_http_function(
        self,
        *,
        agent_id: int,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        required_params: list[str],
        http_method: str,
        http_url: str,
        http_body: str,
        http_headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Register an HTTP tool on a hosted Edesy agent (requires public URL)."""
        body = {
            "agentId": agent_id,
            "name": name,
            "description": description,
            "parametersSchema": parameters_schema,
            "requiredParams": required_params,
            "httpMethod": http_method,
            "httpUrl": http_url,
            "httpHeaders": http_headers or {"Content-Type": "application/json"},
            "httpBody": http_body,
            "isActive": True,
        }
        return self._request("POST", "/functions", json=body, allow_retry_once=False)

    def _normalize_call(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "conversation_id": data.get("conversationId") or data.get("conversation_id"),
            "call_sid": data.get("callSid") or data.get("call_sid"),
            "agent_id": data.get("agentId") or data.get("agent_id"),
            "agent_name": data.get("agentName") or data.get("agent_name"),
            "phone_number": data.get("phoneNumber") or data.get("phone_number"),
            "status": data.get("status"),
            "duration": data.get("duration"),
            "recording_url": data.get("recordingUrl") or data.get("recording_url"),
            "summary": data.get("summary"),
            "disposition": data.get("disposition"),
            "full_text": data.get("fullText") or data.get("full_text"),
            "transcript": data.get("transcript"),
            "metadata": data.get("metadata") or {},
            "start_time": data.get("startTime") or data.get("start_time"),
            "end_time": data.get("endTime") or data.get("end_time"),
            "raw": data,
        }
