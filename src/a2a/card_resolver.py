"""Agent Card 解析 — 从 A2A agent 的 .well-known 端点获取 AgentCard。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp


@dataclass(frozen=True, slots=True)
class AgentSkill:
    """A2A agent 的单个技能描述。"""

    id: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class AgentCard:
    """A2A agent card 数据结构。

    代表 A2A agent 的发现与能力说明卡片，从
    ``{base_url}/.well-known/agent.json`` 获取。
    """

    name: str
    description: str
    url: str
    skills: list[AgentSkill]
    version: str


class AgentCardResolver:
    """通过 A2A 标准端点解析 AgentCard。

    用法::

        resolver = AgentCardResolver()
        card = await resolver.resolve("http://agent.local")
        if card is not None:
            print(card.name, card.version)
    """

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        self._session = session
        self._owns_session = session is None

    async def resolve(self, base_url: str) -> AgentCard | None:
        """GET ``{base_url}/.well-known/agent.json`` 并返回 AgentCard。

        404 / 解析失败 / 缺少必填字段 → None
        """
        import aiohttp

        session = self._session
        close_after = False

        if session is None:
            session = aiohttp.ClientSession()
            close_after = True

        try:
            well_known_url = f"{base_url.rstrip('/')}/.well-known/agent.json"
            async with session.get(well_known_url) as resp:
                if resp.status == 404:
                    return None

                try:
                    raw = await resp.json(content_type=None)
                except (ValueError, json.JSONDecodeError, aiohttp.ContentTypeError):
                    return None

                if not isinstance(raw, dict):
                    return None

                name = raw.get("name")
                url = raw.get("url")
                if not isinstance(name, str) or not isinstance(url, str) or not name or not url:
                    return None

                skills: list[AgentSkill] = []
                for skill_data in raw.get("skills", []) or []:
                    if isinstance(skill_data, dict):
                        sid = skill_data.get("id", "")
                        sname = skill_data.get("name", "")
                        sdesc = skill_data.get("description", "")
                        skills.append(AgentSkill(id=sid, name=sname, description=sdesc))

                return AgentCard(
                    name=name,
                    description=raw.get("description", ""),
                    url=url,
                    version=raw.get("version", ""),
                    skills=skills,
                )
        except (aiohttp.ClientError, TimeoutError):
            return None
        finally:
            if close_after:
                await session.close()
