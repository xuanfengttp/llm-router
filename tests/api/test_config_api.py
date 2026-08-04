import pytest
from fastapi.testclient import TestClient


def test_list_providers_empty(client):
    response = client.get("/api/providers")
    assert response.status_code == 200
    assert response.json() == []


def test_add_provider(client, mock_config_manager):
    response = client.post("/api/providers", json={
        "name": "test-ai", "endpoint": "https://test.ai/v1"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-ai"
    assert data["models"] == []


def test_remove_provider(client, mock_config_manager):
    client.post("/api/providers", json={
        "name": "rm-me", "endpoint": "https://rm.me/v1"
    })
    response = client.delete("/api/providers/rm-me")
    assert response.status_code == 204


def test_update_api_key(client, mock_config_manager):
    client.post("/api/providers", json={
        "name": "k", "endpoint": "https://k.ai/v1"
    })
    response = client.put("/api/providers/k/api-key", json={"api_key": "sk-123"})
    assert response.status_code == 200


def test_add_model(client, mock_config_manager):
    client.post("/api/providers", json={
        "name": "m", "endpoint": "https://m.ai/v1"
    })
    response = client.post("/api/providers/m/models", json={
        "name": "gpt-4o", "context_window": 128000
    })
    assert response.status_code == 200
    assert len(response.json()["models"]) == 1


def test_remove_model(client, mock_config_manager):
    client.post("/api/providers", json={
        "name": "mm", "endpoint": "https://mm.ai/v1"
    })
    client.post("/api/providers/mm/models", json={"name": "gpt-4o"})
    response = client.delete("/api/providers/mm/models/gpt-4o")
    assert response.status_code == 200
    assert len(response.json()["models"]) == 0
