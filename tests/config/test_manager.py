# tests/config/test_manager.py
import pytest

from src.config.crypto import KeyCipher, generate_key
from src.config.manager import ConfigManager
from src.config.models import (
    ModelConfig,
    ModelDeployment,
    ProviderConfig,
    ProviderStatus,
)
from src.config.store import ConfigStore


@pytest.fixture
def cipher():
    return KeyCipher(generate_key())


@pytest.fixture
async def manager(temp_dir, cipher):
    config_path = temp_dir / "config.yaml"
    db_path = temp_dir / "state.db"
    store = ConfigStore(config_path=config_path, db_path=db_path, cipher=cipher)
    await store.init_db()
    mgr = ConfigManager(store)
    yield mgr
    await store.close()


class TestConfigManagerProviders:
    async def test_add_provider(self, manager):
        provider = await manager.add_provider(
            name="openai",
            endpoint="https://api.openai.com/v1",
            api_key="sk-test",
        )
        assert provider.name == "openai"
        assert provider.api_key == "sk-test"
        all_providers = await manager.list_providers()
        assert len(all_providers) == 1

    async def test_add_duplicate_provider_raises(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        with pytest.raises(ValueError, match="已存在"):
            await manager.add_provider("openai", "https://api.openai.com/v1")

    async def test_remove_provider(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        await manager.remove_provider("openai")
        providers = await manager.list_providers()
        assert len(providers) == 0

    async def test_remove_nonexistent_provider_raises(self, manager):
        with pytest.raises(ValueError, match="不存在"):
            await manager.remove_provider("nonexistent")

    async def test_get_provider(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1", api_key="sk-test")
        provider = await manager.get_provider("openai")
        assert provider.name == "openai"
        assert provider.api_key == "sk-test"

    async def test_get_nonexistent_provider(self, manager):
        provider = await manager.get_provider("nonexistent")
        assert provider is None

    async def test_update_provider_api_key(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1", api_key="sk-old")
        await manager.update_provider_api_key("openai", "sk-new")
        provider = await manager.get_provider("openai")
        assert provider.api_key == "sk-new"

    async def test_list_providers_returns_copy(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        providers = await manager.list_providers()
        providers.clear()
        assert len(await manager.list_providers()) == 1


class TestConfigManagerModels:
    async def test_add_model(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        updated = await manager.add_model("openai", model)
        assert len(updated.models) == 1
        assert updated.models[0].name == "gpt-4o"

    async def test_add_duplicate_model_raises(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        await manager.add_model("openai", model)
        with pytest.raises(ValueError, match="已存在"):
            await manager.add_model("openai", model)

    async def test_remove_model(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        await manager.add_model("openai", model)
        updated = await manager.remove_model("openai", "gpt-4o")
        assert len(updated.models) == 0

    async def test_list_models(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        await manager.add_model(
            "openai", ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        )
        await manager.add_model(
            "openai", ModelConfig(name="gpt-4o-mini", deployment=ModelDeployment.CLOUD)
        )
        models = await manager.list_models("openai")
        assert len(models) == 2


class TestConfigManagerStatus:
    async def test_update_status(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        await manager.update_status("openai", ProviderStatus.ONLINE)
        status = await manager.get_status("openai")
        assert status == ProviderStatus.ONLINE

    async def test_get_all_statuses(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        await manager.add_provider("anthropic", "https://api.anthropic.com/v1")
        await manager.update_status("openai", ProviderStatus.ONLINE)
        await manager.update_status("anthropic", ProviderStatus.OFFLINE)
        statuses = await manager.get_all_statuses()
        assert statuses == {"openai": "online", "anthropic": "offline"}


class TestConfigSchema:
    def test_valid_config_passes_validation(self):
        from src.config.schema import validate_config

        config = {
            "providers": [
                {
                    "name": "openai",
                    "endpoint": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                    "models": [{"name": "gpt-4o"}],
                }
            ]
        }
        result = validate_config(config)
        assert result.errors == []
        assert result.valid is True

    def test_missing_name_fails_validation(self):
        from src.config.schema import validate_config

        config = {
            "providers": [
                {
                    "endpoint": "https://api.openai.com/v1",
                    "models": [{"name": "gpt-4o"}],
                }
            ]
        }
        result = validate_config(config)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_invalid_endpoint_url_fails(self):
        from src.config.schema import validate_config

        config = {
            "providers": [
                {
                    "name": "openai",
                    "endpoint": "not-a-url",
                    "models": [{"name": "gpt-4o"}],
                }
            ]
        }
        result = validate_config(config)
        assert result.valid is False

    def test_empty_providers_list(self):
        from src.config.schema import validate_config

        config = {"providers": []}
        result = validate_config(config)
        assert result.valid is True

    def test_missing_providers_key(self):
        from src.config.schema import validate_config

        config = {}
        result = validate_config(config)
        assert result.valid is False
