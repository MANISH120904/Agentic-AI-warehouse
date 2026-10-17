"""Shared pytest fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import reset_settings_cache
from app.db import reset_repository_cache
from app.main import app
from app.repositories.sqlite_repository import SqliteRepository


@pytest.fixture()
def temp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = Path(__file__).resolve().parents[1] / "app" / "data"
    for name in ("orders.json", "inventory.json", "shipments.json", "calls.json", "feedback.json"):
        shutil.copy(source / name, tmp_path / name)

    db_path = tmp_path / "warehouse.db"
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("EDESY_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("EDESY_AGENT_ID", "")
    monkeypatch.setenv("WAREHOUSE_DB_PATH", str(db_path))
    reset_settings_cache()
    reset_repository_cache()

    from app.api import routes_calls, routes_feedback, routes_orders
    from app.services.call_service import CallService
    from app.services.feedback_service import FeedbackService
    from app.services.inventory_service import InventoryService
    from app.services.order_service import OrderService
    from app.services.prediction_service import PredictionService

    repo = SqliteRepository(db_path=db_path, seed_dir=tmp_path, auto_seed=True)
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
def repo(temp_data_dir: Path) -> SqliteRepository:
    db_path = temp_data_dir / "warehouse.db"
    return SqliteRepository(db_path=db_path, seed_dir=temp_data_dir, auto_seed=True)
