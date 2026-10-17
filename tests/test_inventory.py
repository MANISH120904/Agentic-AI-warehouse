from __future__ import annotations


def test_get_inventory(client):
    response = client.get("/api/inventory/SKU-A100")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["product"]["product_name"]
    assert body["is_low"] is False


def test_missing_product(client):
    response = client.get("/api/inventory/SKU-MISSING")
    assert response.status_code == 404


def test_low_stock_flag(client):
    response = client.get("/api/inventory/SKU-B210")
    assert response.status_code == 200
    assert response.json()["is_low"] is True
