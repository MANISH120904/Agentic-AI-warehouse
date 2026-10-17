from __future__ import annotations


def test_local_db_endpoint(client):
    response = client.get("/api/local/db")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["backend"] == "sqlite"
    assert body["local"] is True
    assert body["counts"]["orders"] >= 10
    assert "warehouse.db" in body["db_path"]


def test_tool_reads_local_db(client):
    response = client.post(
        "/api/tools/get_order_status",
        json={"order_id": "ORD-1001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["order"]["order_id"] == "ORD-1001"


def test_settings_include_local_db(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["local_db"]["backend"] == "sqlite"
    assert body["local_db"]["counts"]["inventory"] >= 8
