from __future__ import annotations


def test_execution_metrics_endpoint(client):
    client.get("/health")
    client.get("/api/orders")
    response = client.get("/api/metrics/execution")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["low_execution_time"] is True
    assert body["sample_count"] >= 1
    assert "avg_ms" in body
    assert body["low_latency_target_ms"] == 500
