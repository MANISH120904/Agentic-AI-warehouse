from __future__ import annotations

from app.services.prediction_service import PredictionService


def test_delay_risk_endpoint(client):
    response = client.get("/api/orders/ORD-1003/delay-risk")
    assert response.status_code == 200
    body = response.json()
    assert body["is_simulated"] is True
    assert body["risk"] in {"low", "medium", "high"}
    assert isinstance(body["reasons"], list)
    assert body["risk"] == "high"


def test_delay_risk_unknown_order(client):
    response = client.get("/api/orders/ORD-NOPE/delay-risk")
    assert response.status_code == 404


def test_prediction_service_low_risk(repo):
    service = PredictionService(repo)
    result = service.predict_delivery_delay("ORD-1004")
    assert result["ok"] is True
    assert result["risk"] in {"low", "medium"}
    assert result["is_simulated"] is True
