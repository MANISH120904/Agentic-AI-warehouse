from __future__ import annotations


def test_list_orders(client):
    response = client.get("/api/orders")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) >= 10
    assert orders[0]["order_id"].startswith("ORD-")


def test_get_order(client):
    response = client.get("/api/orders/ORD-1001")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["order"]["customer_name"] == "Priya Sharma"
    assert body["is_simulated"] is True


def test_unknown_order(client):
    response = client.get("/api/orders/ORD-DOES-NOT-EXIST")
    assert response.status_code == 404


def test_customer_history(client):
    response = client.get("/api/customers/CUST-501/orders")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 2
