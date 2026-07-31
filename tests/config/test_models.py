from dataclasses import FrozenInstanceError

import pytest

from src.config.models import (
    ModelConfig,
    ModelDeployment,
    ProviderConfig,
    ProviderStatus,
)


class TestModelConfig:
    def test_create_model_with_required_fields(self):
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        assert model.name == "gpt-4o"
        assert model.deployment == ModelDeployment.CLOUD
        assert model.context_window == 4096  # default
        assert model.tags == []  # default
        assert model.cost_input_1k == 0.0  # default
        assert model.cost_output_1k == 0.0  # default

    def test_create_model_with_all_fields(self):
        model = ModelConfig(
            name="gpt-4o",
            deployment=ModelDeployment.CLOUD,
            context_window=128000,
            cost_input_1k=0.0025,
            cost_output_1k=0.0100,
            tags=["smart", "expensive"],
        )
        assert model.context_window == 128000
        assert model.cost_input_1k == 0.0025
        assert model.tags == ["smart", "expensive"]

    def test_model_is_immutable(self):
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        with pytest.raises(FrozenInstanceError):
            model.name = "changed"  # type: ignore[misc]

    def test_model_equality_by_value(self):
        a = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        b = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        assert a == b

    def test_model_hashable(self):
        a = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        b = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        assert hash(a) == hash(b)
        assert len({a, b}) == 1


class TestProviderConfig:
    def test_create_provider_with_required_fields(self):
        provider = ProviderConfig(name="openai", endpoint="https://api.openai.com/v1")
        assert provider.name == "openai"
        assert provider.endpoint == "https://api.openai.com/v1"
        assert provider.api_key is None
        assert provider.models == []
        assert provider.status == ProviderStatus.UNKNOWN

    def test_create_provider_with_models(self):
        models = [
            ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD),
            ModelConfig(name="gpt-4o-mini", deployment=ModelDeployment.CLOUD),
        ]
        provider = ProviderConfig(
            name="openai",
            endpoint="https://api.openai.com/v1",
            api_key="sk-test",
            models=models,
        )
        assert len(provider.models) == 2
        assert provider.api_key == "sk-test"

    def test_provider_is_immutable(self):
        provider = ProviderConfig(name="openai", endpoint="https://api.openai.com/v1")
        with pytest.raises(FrozenInstanceError):
            provider.name = "changed"  # type: ignore[misc]

    def test_provider_add_model_returns_new_instance(self):
        provider = ProviderConfig(name="openai", endpoint="https://api.openai.com/v1")
        new_model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        updated = provider.add_model(new_model)
        assert len(provider.models) == 0
        assert len(updated.models) == 1
        assert updated.models[0].name == "gpt-4o"

    def test_provider_remove_model_returns_new_instance(self):
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        provider = ProviderConfig(
            name="openai",
            endpoint="https://api.openai.com/v1",
            models=[model],
        )
        updated = provider.remove_model("gpt-4o")
        assert len(updated.models) == 0
        assert len(provider.models) == 1  # original unchanged

    def test_provider_remove_nonexistent_model_raises(self):
        provider = ProviderConfig(name="openai", endpoint="https://api.openai.com/v1")
        with pytest.raises(ValueError, match="不存在"):
            provider.remove_model("nonexistent")


class TestProviderStatus:
    def test_status_values(self):
        assert ProviderStatus.ONLINE == "online"
        assert ProviderStatus.OFFLINE == "offline"
        assert ProviderStatus.DEGRADED == "degraded"
        assert ProviderStatus.UNKNOWN == "unknown"


class TestModelDeployment:
    def test_deployment_values(self):
        assert ModelDeployment.CLOUD == "cloud"
        assert ModelDeployment.LOCAL == "local"
        assert ModelDeployment.HYBRID == "hybrid"


from datetime import datetime, timezone

from src.config.models import LatencyRecord


class TestLatencyRecord:
    """LatencyRecord 数据模型测试."""

    def test_create_record_with_required_fields(self):
        """仅必填字段创建记录."""
        record = LatencyRecord(
            provider="openai",
            model="gpt-4o",
            latency_ms=320.5,
        )
        assert record.provider == "openai"
        assert record.model == "gpt-4o"
        assert record.latency_ms == 320.5
        assert record.success is True
        assert record.error is None

    def test_create_record_with_all_fields(self):
        """全字段创建记录."""
        ts = "2026-07-31T12:00:00Z"
        record = LatencyRecord(
            provider="anthropic",
            model="claude-opus-5",
            latency_ms=850.0,
            success=False,
            error="Connection timeout",
            timestamp=ts,
        )
        assert record.provider == "anthropic"
        assert record.model == "claude-opus-5"
        assert record.latency_ms == 850.0
        assert record.success is False
        assert record.error == "Connection timeout"
        assert record.timestamp == ts

    def test_record_default_timestamp_is_utc_now(self):
        """默认时间戳为当前 UTC 时间."""
        before = datetime.now(timezone.utc)
        record = LatencyRecord(provider="p", model="m", latency_ms=100.0)
        after = datetime.now(timezone.utc)
        ts = datetime.fromisoformat(record.timestamp)
        # 字符串时间戳仅精确到秒，比较时去掉微秒
        before_sec = before.replace(microsecond=0)
        after_sec = after.replace(microsecond=0)
        assert before_sec <= ts <= after_sec

    def test_record_is_immutable(self):
        """LatencyRecord 为不可变对象."""
        record = LatencyRecord(provider="p", model="m", latency_ms=100.0)
        with pytest.raises(Exception):
            record.latency_ms = 200.0  # type: ignore[misc]

    def test_record_equality_by_value(self):
        """同值记录相等."""
        r1 = LatencyRecord(provider="a", model="x", latency_ms=100.0, timestamp="2026-01-01T00:00:00Z")
        r2 = LatencyRecord(provider="a", model="x", latency_ms=100.0, timestamp="2026-01-01T00:00:00Z")
        assert r1 == r2

    def test_record_hashable(self):
        """记录可哈希."""
        r1 = LatencyRecord(provider="a", model="x", latency_ms=100.0, timestamp="2026-01-01T00:00:00Z")
        r2 = LatencyRecord(provider="a", model="x", latency_ms=100.0, timestamp="2026-01-01T00:00:00Z")
        assert hash(r1) == hash(r2)
