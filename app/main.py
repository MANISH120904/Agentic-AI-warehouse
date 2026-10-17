"""FastAPI entrypoint for WarehouseVoiceAI."""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import routes_calls, routes_feedback, routes_health, routes_orders
from app.config import get_settings
from app.services.timing_service import timing_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("warehousevoiceai")

settings = get_settings()

app = FastAPI(
    title="WarehouseVoiceAI",
    description=(
        "Hackathon MVP: warehouse tools, Streamlit operator dashboard, "
        "Edesy hosted voice calls, and a separate Google ADK browser voice agent."
    ),
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_execution_time(request: Request, call_next):
    """Record per-request latency for low-execution-time monitoring."""
    start = time.perf_counter()
    ok = True
    try:
        response = await call_next(request)
        ok = response.status_code < 500
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Execution-Time-Ms"] = f"{duration_ms:.2f}"
        timing_service.record(request.url.path, duration_ms, ok=ok)
        return response
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        timing_service.record(request.url.path, duration_ms, ok=False)
        raise


app.include_router(routes_health.router)
app.include_router(routes_orders.router)
app.include_router(routes_calls.router)
app.include_router(routes_feedback.router)


@app.on_event("startup")
def on_startup() -> None:
    logger.info(
        "WarehouseVoiceAI starting env=%s mock_mode=%s edesy=%s google=%s",
        settings.app_env,
        settings.mock_mode,
        settings.edesy_configured,
        settings.google_configured,
    )
    if settings.mock_mode:
        logger.info("MOCK_MODE enabled — outbound calls will be simulated.")
    elif not settings.telephony_ready:
        logger.warning(
            "Live telephony not ready. Configure EDESY_API_KEY and EDESY_AGENT_ID."
        )
