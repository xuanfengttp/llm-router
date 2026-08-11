from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.a2a.http_client import A2AClient

ENDPOINT = "http://localhost:8080/"


def _mock_response(json_payload: dict) -> AsyncMock:
    """Create an async context manager that returns a mock response."""
    resp = AsyncMock()
    resp.json = AsyncMock(return_value=json_payload)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


class TestSendTask:
    """send_task JSON-RPC tests."""

    @pytest.mark.asyncio
    async def test_send_task_format(self):
        """Verify JSON-RPC request method and task_id in params."""
        resp = _mock_response({
            "jsonrpc": "2.0",
            "id": "req-1",
            "result": {"task": {"id": "t1", "status": "submitted"}},
        })
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with A2AClient(endpoint=ENDPOINT) as client:
                await client.send_task(prompt="hello world", task_id="t1")

        call_args = mock_session.post.call_args
        assert call_args is not None
        _, kwargs = call_args
        payload = kwargs.get("json", {})

        assert payload["jsonrpc"] == "2.0"
        assert payload["method"] == "tasks/send"
        assert payload["params"]["id"] == "t1"
        assert payload["params"]["message"]["role"] == "user"
        assert payload["params"]["message"]["parts"][0]["text"] == "hello world"
        assert payload["params"]["metadata"] == {}
        assert payload["id"].startswith("req-")

    @pytest.mark.asyncio
    async def test_send_task_response(self):
        """send_task returns the JSON-RPC response dict."""
        resp = _mock_response({
            "jsonrpc": "2.0",
            "id": "req-1",
            "result": {"task": {"id": "t1", "status": "submitted"}},
        })
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with A2AClient(endpoint=ENDPOINT) as client:
                result = await client.send_task(prompt="hi", task_id="t1")

        assert result["jsonrpc"] == "2.0"
        assert result["result"]["task"]["id"] == "t1"
        assert result["result"]["task"]["status"] == "submitted"


class TestGetTask:
    """get_task JSON-RPC tests."""

    @pytest.mark.asyncio
    async def test_get_task_completed(self):
        """get_task returns completed status with artifact parts."""
        resp = _mock_response({
            "jsonrpc": "2.0",
            "id": "req-2",
            "result": {
                "task": {
                    "id": "t2",
                    "status": "completed",
                    "artifact": {"parts": [{"text": "output"}]},
                }
            },
        })
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with A2AClient(endpoint=ENDPOINT) as client:
                result = await client.get_task(task_id="t2")

        assert result["result"]["task"]["status"] == "completed"
        assert result["result"]["task"]["artifact"]["parts"][0]["text"] == "output"

    @pytest.mark.asyncio
    async def test_get_task_working(self):
        """get_task returns working status (polling scenario)."""
        resp = _mock_response({
            "jsonrpc": "2.0",
            "id": "req-3",
            "result": {"task": {"id": "t3", "status": "working"}},
        })
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with A2AClient(endpoint=ENDPOINT) as client:
                result = await client.get_task(task_id="t3")

        assert result["result"]["task"]["status"] == "working"


class TestCancelTask:
    """cancel_task JSON-RPC tests."""

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """cancel_task sends tasks/cancel method."""
        resp = _mock_response({
            "jsonrpc": "2.0",
            "id": "req-4",
            "result": {"task": {"id": "t4", "status": "cancelled"}},
        })
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with A2AClient(endpoint=ENDPOINT) as client:
                await client.cancel_task(task_id="t4")

        call_args = mock_session.post.call_args
        assert call_args is not None
        _, kwargs = call_args
        payload = kwargs.get("json", {})

        assert payload["method"] == "tasks/cancel"
        assert payload["params"]["id"] == "t4"


class TestAuth:
    """Authentication header tests."""

    @pytest.mark.asyncio
    async def test_auth_header(self):
        """When api_key is set, request includes Authorization: Bearer header."""
        resp = _mock_response({
            "jsonrpc": "2.0",
            "id": "req-5",
            "result": {"task": {"id": "t5", "status": "submitted"}},
        })
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with A2AClient(endpoint=ENDPOINT, api_key="secret123") as client:
                await client.send_task(prompt="hi", task_id="t5")

        call_args = mock_session.post.call_args
        assert call_args is not None
        _, kwargs = call_args
        headers = kwargs.get("headers", {})

        assert headers.get("Authorization") == "Bearer secret123"

    @pytest.mark.asyncio
    async def test_no_auth_header(self):
        """Without api_key, no Authorization header is present."""
        resp = _mock_response({
            "jsonrpc": "2.0",
            "id": "req-6",
            "result": {"task": {"id": "t6", "status": "submitted"}},
        })
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)
        mock_session.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            async with A2AClient(endpoint=ENDPOINT) as client:
                await client.send_task(prompt="hi", task_id="t6")

        call_args = mock_session.post.call_args
        assert call_args is not None
        _, kwargs = call_args
        headers = kwargs.get("headers", {})

        assert "Authorization" not in headers
