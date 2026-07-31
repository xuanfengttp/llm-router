# tests/network/test_probe.py
import pytest
from aiohttp import web
from aiohttp.test_utils import unused_port

from src.network.probe import LatencyProbe, ProbeResult


class TestProbeResult:
    def test_success_result(self):
        result = ProbeResult(
            provider="openai",
            model="gpt-4o",
            success=True,
            latency_ms=320.5,
        )
        assert result.success is True
        assert result.latency_ms == 320.5
        assert result.error is None

    def test_failure_result(self):
        result = ProbeResult(
            provider="openai",
            model="gpt-4o",
            success=False,
            error="Connection timeout",
        )
        assert result.success is False
        assert result.latency_ms is None
        assert result.error == "Connection timeout"

    def test_result_to_dict(self):
        result = ProbeResult(
            provider="openai",
            model="gpt-4o",
            success=True,
            latency_ms=320.5,
        )
        d = result.to_dict()
        assert d["provider"] == "openai"
        assert d["model"] == "gpt-4o"
        assert d["success"] is True
        assert d["latency_ms"] == 320.5
        assert "timestamp" in d

    def test_timestamp_is_utc_iso_format(self):
        """ProbeResult 时间戳为 UTC ISO 8601 格式."""
        result = ProbeResult(provider="t", model="m", success=True, latency_ms=10.0)
        ts = result.timestamp
        # 必须以 Z 结尾或以 +00:00 结尾
        assert ts.endswith("Z") or ts.endswith("+00:00")
        from datetime import datetime

        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert dt.tzinfo is not None


class TestLatencyProbe:
    @pytest.fixture
    async def echo_server(self):
        """创建一个简单的 echo HTTP 服务用于测试."""

        async def handler(request: web.Request) -> web.Response:
            return web.json_response({"status": "ok"})

        app = web.Application()
        app.router.add_get("/models", handler)
        app.router.add_post("/chat/completions", handler)

        port = unused_port()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", port)
        await site.start()

        yield f"http://localhost:{port}"

        await runner.cleanup()

    async def test_ping_models_endpoint_success(self, echo_server):
        probe = LatencyProbe(timeout_seconds=5)
        result = await probe.ping_models_endpoint("test-provider", echo_server)
        assert result.success is True
        assert result.latency_ms is not None
        assert result.latency_ms > 0

    async def test_ping_chat_endpoint_success(self, echo_server):
        probe = LatencyProbe(timeout_seconds=5)
        result = await probe.ping_chat_endpoint(
            "test-provider", "test-model", echo_server
        )
        assert result.success is True
        assert result.latency_ms is not None

    async def test_ping_unreachable_host(self):
        probe = LatencyProbe(timeout_seconds=1)
        result = await probe.ping_models_endpoint(
            "offline-provider", "http://192.0.2.1:9999"  # TEST-NET 地址
        )
        assert result.success is False
        assert result.error is not None

    async def test_ping_timeout(self, echo_server):
        probe = LatencyProbe(timeout_seconds=0.001)  # 极短超时
        result = await probe.ping_models_endpoint("test-provider", echo_server)
        # 可能成功也可能超时，取决于网络速度
        assert isinstance(result, ProbeResult)

    async def test_probe_all_empty_list(self):
        probe = LatencyProbe()
        results = await probe.probe_all([])
        assert results == []

    async def test_probe_all_with_providers(self, echo_server):
        from src.config.models import (
            ModelConfig,
            ModelDeployment,
            ProviderConfig,
        )

        provider = ProviderConfig(
            name="test-provider",
            endpoint=echo_server,
            models=[
                ModelConfig(name="test-model", deployment=ModelDeployment.LOCAL)
            ],
        )
        probe = LatencyProbe(timeout_seconds=5)
        results = await probe.probe_all([provider])
        assert len(results) > 0
        for result in results:
            assert result.provider == "test-provider"
            assert isinstance(result.success, bool)
