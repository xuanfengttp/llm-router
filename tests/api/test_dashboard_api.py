"""Dashboard API 测试."""
from __future__ import annotations


def test_dashboard_status(dashboard_client, mock_config_manager):
    """GET /api/dashboard/status 返回 providers 和 selected_models."""
    import pytest
    # Create at least one provider so we can assert on the providers list.
    from src.config.models import ProviderConfig
    mock_config_manager._providers.append(
        ProviderConfig(name="ds", endpoint="https://ds.ai/v1")
    )
    response = dashboard_client.get("/api/dashboard/status")
    assert response.status_code == 200
    data = response.json()
    assert len(data["providers"]) >= 1


def test_dashboard_probe(dashboard_client, mock_config_manager):
    """POST /api/dashboard/probe: 对不存在的 provider 返回空列表."""
    response = dashboard_client.post("/api/dashboard/probe", json={
        "providers": ["nonexist"], "models": ["m1"]
    })
    assert response.status_code == 200
    assert response.json() == []
