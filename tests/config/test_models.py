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
