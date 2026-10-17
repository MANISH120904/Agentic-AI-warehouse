"""Shared pytest fixtures."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import reset_settings_cache
from app.main import app
from app.repositories.json_repository import JsonRepository


@pytest.fixture()
def temp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = Path(__file__).resolve().parents[1] / "app" / "data"
    for name in ("orders.json", "inventory.json", "shipments.json"):
        shutil.copy(source / name, tmp_path / name)
    (tmp_path / "calls.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "feedback.json").write_text("[]\n", encoding="utf-8")

    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("EDESY_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("EDESY_AGENT_ID", "")
    reset_settings_cache()

    # Point services used by routers at temp data
    from app.api import routes_calls, routes_feedback, routes_orders
    from app.services.call_service import CallService
    from app.services.feedback_service import FeedbackService
    from app.services.inventory_service import InventoryService
    from app.services.order_service import OrderService
    from app.services.prediction_service import PredictionService

    repo = JsonRepository(tmp_path)
    routes_orders.order_service = OrderService(repo)
    routes_orders.inventory_service = InventoryService(repo)
    routes_orders.prediction_service = PredictionService(repo)
    routes_calls.call_service = CallService(repo=repo)
    routes_feedback.feedback_service = FeedbackService(repo)
    routes_feedback.call_service = CallService(repo=repo)
    routes_feedback.order_service = OrderService(repo)
    routes_feedback.prediction_service = PredictionService(repo)
    return tmp_path


@pytest.fixture()
def client(temp_data_dir: Path) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def repo(temp_data_dir: Path) -> JsonRepository:
    return JsonRepository(temp_data_dir)
