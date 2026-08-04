"""Settings API 测试."""
from __future__ import annotations

import pytest


@pytest.fixture
def settings_client(mock_config_manager):
    from backend.src.api.settings_api import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.settings_store = {"strategy": "baseline"}
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_get_settings(settings_client):
    """GET /api/settings returns defaults merged with stored settings."""
    response = settings_client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "strategy" in data
    assert data["strategy"] == "baseline"
    assert "latency_redline_ms" in data
    assert data["latency_redline_ms"] == 5000


def test_update_settings(settings_client):
    """PUT /api/settings updates stored values."""
    response = settings_client.put("/api/settings", json={"strategy": "cost_first"})
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "cost_first"
    # other defaults should still be present
    assert data["latency_redline_ms"] == 5000
