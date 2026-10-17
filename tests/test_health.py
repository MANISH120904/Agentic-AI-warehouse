from __future__ import annotations


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mock_mode"] is True
    assert "edesy_configured" in body


def test_settings_masks_secrets(client, monkeypatch):
    monkeypatch.setenv("EDESY_API_KEY", "vp_live_abcdefghijklmnopqrstuvwxyz")
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSyDummyKeyForTestsOnly123456")
    from app.config import reset_settings_cache

    reset_settings_cache()
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert "vp_live_abcdefghijklmnopqrstuvwxyz" not in body["edesy_api_key_masked"]
    assert "AIzaSyDummyKeyForTestsOnly123456" not in body["google_api_key_masked"]
    assert body["edesy_configured"] is True
