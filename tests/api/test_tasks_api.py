"""Tasks API 测试.

Note: Since TaskController requires full app initialization
(task_queue.db, route_engine, dispatcher, etc.), these tests stay
minimal.  Structure-only tests verify the router wiring; controller-
dependent endpoints return 503 when controller is absent.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def tasks_client(mock_config_manager):
    from backend.src.api.tasks_api import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api")
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_list_tasks_empty(tasks_client):
    """GET /api/tasks returns empty list when task_queue is not attached."""
    response = tasks_client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_create_task_no_controller(tasks_client):
    """POST /api/tasks returns 503 when no controller is attached."""
    response = tasks_client.post("/api/tasks", json={
        "prompt": "hello", "target_model": "gpt-4o"
    })
    assert response.status_code == 503


def test_cancel_task_no_controller(tasks_client):
    """POST /api/tasks/{id}/cancel returns 503 when no controller is attached."""
    response = tasks_client.post("/api/tasks/fake-id/cancel")
    assert response.status_code == 503


def test_retry_task_no_controller(tasks_client):
    """POST /api/tasks/{id}/retry returns 503 when no controller is attached."""
    response = tasks_client.post("/api/tasks/fake-id/retry")
    assert response.status_code == 503
