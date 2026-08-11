"""card_resolver.py 的测试 — 单元测试代理卡片解析器 (AgentCardResolver)。"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.a2a.card_resolver import AgentCard, AgentCardResolver, AgentSkill

AGENT_JSON_PAYLOAD: dict = {
    "name": "code-explorer",
    "description": "Searches and analyzes codebases",
    "url": "https://agent.example.com/v1",
    "version": "1.0.0",
    "skills": [
        {"id": "code-search", "name": "Code Search", "description": "Search code"},
        {"id": "code-review", "name": "Code Review", "description": "Review code"},
    ],
}

BASE_URL = "http://test-agent.local"
WELL_KNOWN = f"{BASE_URL}/.well-known/agent.json"


# ------------------------------------------------------------------
# Helpers — 构建 mock aiohttp session
# ------------------------------------------------------------------


def _mock_response(
    *,
    status: int = 200,
    json_body: object = None,
    text_body: str = "",
    content_type: str = "application/json",
) -> MagicMock:
    """构建一个 mock aiohttp ClientResponse。"""
    resp = MagicMock()
    resp.status = status

    async def _json(**kwargs):
        if json_body is None and content_type != "application/json":
            # 模拟非 JSON 响应时的 json() 行为
            raise ValueError("not JSON")
        return json_body

    async def _text():
        return text_body

    resp.json = _json
    resp.text = _text

    # __aenter__ / __aexit__ for `async with session.get(...) as resp:`
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestAgentCardResolver:
    """AgentCardResolver 单元测试。"""

    # ------------------------------------------------------------------
    # 成功路径
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_resolve_success(self):
        """GET {base_url}/.well-known/agent.json → 返回有效 AgentCard, 各字段正确。"""
        resolver = AgentCardResolver()

        mock_resp = _mock_response(status=200, json_body=dict(AGENT_JSON_PAYLOAD))

        with patch("aiohttp.ClientSession.get", return_value=mock_resp) as mock_get:
            card: AgentCard | None = await resolver.resolve(BASE_URL)

        mock_get.assert_called_once_with(WELL_KNOWN)

        assert card is not None, "正常响应应返回 AgentCard 实例"
        assert card.name == "code-explorer"
        assert card.description == "Searches and analyzes codebases"
        assert card.url == "https://agent.example.com/v1"
        assert card.version == "1.0.0"
        assert len(card.skills) == 2
        assert card.skills[0].id == "code-search"
        assert card.skills[1].name == "Code Review"

    # ------------------------------------------------------------------
    # 正常失败 → None (不应抛出异常)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_resolve_not_found(self):
        """HTTP 404 → 返回 None, 不抛异常。"""
        resolver = AgentCardResolver()

        mock_resp = _mock_response(status=404)

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            card: AgentCard | None = await resolver.resolve(BASE_URL)

        assert card is None

    @pytest.mark.asyncio
    async def test_resolve_invalid_json(self):
        """响应体非合法 JSON → 返回 None。"""
        resolver = AgentCardResolver()

        # 带非 JSON content_type，json() 应该抛错
        mock_resp = _mock_response(
            status=200, text_body="not json {{{", content_type="text/plain"
        )

        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            card: AgentCard | None = await resolver.resolve(BASE_URL)

        assert card is None

    @pytest.mark.asyncio
    async def test_resolve_missing_fields(self):
        """agent.json 缺 name 或 url → 返回 None。"""
        resolver = AgentCardResolver()

        # 缺失 name
        mock_resp = _mock_response(
            status=200, json_body={"url": "https://x", "version": "1"}
        )
        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            card: AgentCard | None = await resolver.resolve(BASE_URL)
        assert card is None

        # 缺失 url
        mock_resp = _mock_response(
            status=200, json_body={"name": "x", "version": "1"}
        )
        with patch("aiohttp.ClientSession.get", return_value=mock_resp):
            card = await resolver.resolve(BASE_URL)
        assert card is None

    # ------------------------------------------------------------------
    # 数据模型
    # ------------------------------------------------------------------

    def test_card_contains_skills(self):
        """AgentCard.skills 列表非空, 每个元素是 AgentSkill 实例。"""
        skill1 = AgentSkill(id="s1", name="Skill One", description="Desc 1")
        skill2 = AgentSkill(id="s2", name="Skill Two", description="Desc 2")
        card = AgentCard(
            name="test-agent",
            description="test",
            url="https://example.com",
            version="1.0",
            skills=[skill1, skill2],
        )

        assert len(card.skills) == 2
        assert all(isinstance(s, AgentSkill) for s in card.skills)
        assert card.skills[0].id == "s1"
        assert card.skills[0].name == "Skill One"
        assert card.skills[0].description == "Desc 1"

    # ------------------------------------------------------------------
    # 复用 session
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_resolve_with_custom_session(self):
        """可注入外部 aiohttp.ClientSession。"""
        import aiohttp

        mock_resp = _mock_response(status=200, json_body=dict(AGENT_JSON_PAYLOAD))

        session = MagicMock(spec=aiohttp.ClientSession)
        session.get.return_value = mock_resp

        resolver = AgentCardResolver(session=session)
        card: AgentCard | None = await resolver.resolve(BASE_URL)

        assert card is not None
        assert card.name == "code-explorer"
        # 外部 session 不应被 close
        session.close.assert_not_called()
