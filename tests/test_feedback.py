from __future__ import annotations


def test_feedback_persistence(client):
    # Create a mock call first for association
    call_resp = client.post(
        "/api/calls/outbound",
        json={
            "phone_number": "+919811100001",
            "order_id": "ORD-1001",
            "purpose": "feedback_followup",
            "confirm": True,
            "idempotency_key": "fb-test-1",
        },
    )
    assert call_resp.status_code == 200
    call_id = call_resp.json()["call"]["call_id"]

    response = client.post(
        "/api/feedback",
        json={"call_id": call_id, "rating": 5, "feedback": "Helpful update"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rating"] == 5
    assert body["call_id"] == call_id

    listed = client.get("/api/feedback")
    assert listed.status_code == 200
    assert any(item["feedback_id"] == body["feedback_id"] for item in listed.json())


def test_feedback_unknown_call(client):
    response = client.post(
        "/api/feedback",
        json={"call_id": "CALL-missing", "rating": 3, "feedback": "ok"},
    )
    assert response.status_code == 400
