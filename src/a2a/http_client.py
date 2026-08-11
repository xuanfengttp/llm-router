from __future__ import annotations

import uuid
from dataclasses import dataclass

import aiohttp


@dataclass(frozen=True, slots=True)
class A2AClient:
    """Standard A2A JSON-RPC 2.0 over HTTP client."""

    endpoint: str
    api_key: str | None = None

    _session: aiohttp.ClientSession | None = None

    async def send_task(self, prompt: str, task_id: str) -> dict:
        """POST tasks/send with JSON-RPC payload."""
        return await self._call(
            method="tasks/send",
            params={
                "message": {
                    "role": "user",
                    "parts": [{"text": prompt}],
                },
                "id": task_id,
                "metadata": {},
            },
        )

    async def get_task(self, task_id: str) -> dict:
        """POST tasks/get to retrieve task status."""
        return await self._call(
            method="tasks/get",
            params={"id": task_id},
        )

    async def cancel_task(self, task_id: str) -> dict:
        """POST tasks/cancel to cancel a task."""
        return await self._call(
            method="tasks/cancel",
            params={"id": task_id},
        )

    async def _call(self, method: str, params: dict) -> dict:
        """Send a JSON-RPC 2.0 request and return the parsed response."""
        payload = {
            "jsonrpc": "2.0",
            "id": f"req-{uuid.uuid4()}",
            "method": method,
            "params": params,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        session = self._session
        if session is None:
            session = aiohttp.ClientSession()
            object.__setattr__(self, "_session", session)

        async with session.post(self.endpoint, json=payload, headers=headers) as resp:
            return await resp.json()

    async def __aenter__(self) -> A2AClient:
        session = aiohttp.ClientSession()
        object.__setattr__(self, "_session", session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        session = self._session
        if session is not None:
            await session.close()
            object.__setattr__(self, "_session", None)

    async def close(self) -> None:
        """Explicitly close the session."""
        session = self._session
        if session is not None:
            await session.close()
            object.__setattr__(self, "_session", None)
