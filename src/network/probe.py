# src/network/probe.py
from __future__ import annotations

import time
from dataclasses import dataclass, field

import aiohttp

from src.config.models import ProviderConfig


@dataclass(slots=True)
class ProbeResult:
    """单次连通性探测结果."""

    provider: str
    model: str
    success: bool
    latency_ms: float | None = None
    error: str | None = None
    timestamp: str = field(
        default_factory=lambda: time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
    )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class LatencyProbe:
    """异步 HTTP 连通性探测与延迟测量.

    用法:
        probe = LatencyProbe(timeout_seconds=10)
        result = await probe.ping_models_endpoint("openai", "https://api.openai.com/v1")
        print(f"延迟: {result.latency_ms}ms")
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def _measure(
        self,
        provider: str,
        model: str,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        json_body: dict | None = None,
    ) -> ProbeResult:
        """执行一次 HTTP 请求并测量延迟."""
        start = time.perf_counter()
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.request(
                    method, url, headers=headers, json=json_body
                ) as resp:
                    await resp.read()  # 确保完整接收
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    return ProbeResult(
                        provider=provider,
                        model=model,
                        success=200 <= resp.status < 300,
                        latency_ms=round(elapsed_ms, 2),
                    )
        except aiohttp.ClientError as e:
            return ProbeResult(
                provider=provider,
                model=model,
                success=False,
                error=f"HTTP error: {e}",
            )
        except TimeoutError:
            return ProbeResult(
                provider=provider,
                model=model,
                success=False,
                error="Connection timeout",
            )
        except Exception as e:
            return ProbeResult(
                provider=provider,
                model=model,
                success=False,
                error=f"Unexpected: {type(e).__name__}: {e}",
            )

    async def ping_models_endpoint(
        self, provider: str, endpoint: str, api_key: str | None = None
    ) -> ProbeResult:
        """探测 /v1/models 端点 (GET)."""
        url = f"{endpoint.rstrip('/')}/models"
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return await self._measure(provider, "all", url, method="GET", headers=headers)

    async def ping_chat_endpoint(
        self,
        provider: str,
        model: str,
        endpoint: str,
        api_key: str | None = None,
    ) -> ProbeResult:
        """探测 /chat/completions 端点 (POST 最小有效请求体，验证真实推理可达性)."""
        url = f"{endpoint.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        # 发送最小有效请求：1 token max_tokens 避免消耗
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }
        return await self._measure(
            provider, model, url, method="POST", headers=headers, json_body=body
        )

    async def probe_all(
        self, providers: list[ProviderConfig]
    ) -> list[ProbeResult]:
        """对所有 Provider 执行批量连通性探测.

        对每个 Provider：
        1. ping /models 端点确认连通
        2. ping /chat/completions 测量实际调用延迟
        """
        results: list[ProbeResult] = []

        async def probe_one(provider: ProviderConfig) -> None:
            # 1. 基本连通性
            result = await self.ping_models_endpoint(
                provider.name, provider.endpoint, provider.api_key
            )
            results.append(result)

            # 2. 每个模型的 chat 延迟 (只需要端点可达就继续)
            if result.success:
                for model in provider.models:
                    chat_result = await self.ping_chat_endpoint(
                        provider.name,
                        model.name,
                        provider.endpoint,
                        provider.api_key,
                    )
                    results.append(chat_result)

        # 顺序执行以保证结果有序 (后续 Phase 可改为并行)
        for provider in providers:
            await probe_one(provider)

        return results
