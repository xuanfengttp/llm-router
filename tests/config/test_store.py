# tests/config/test_store.py
from pathlib import Path

import pytest

from src.config.crypto import KeyCipher, generate_key
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
def sample_providers():
    return [
        ProviderConfig(
            name="openai",
            endpoint="https://api.openai.com/v1",
            api_key="sk-test-123",
            models=[
                ModelConfig(
                    name="gpt-4o",
                    deployment=ModelDeployment.CLOUD,
                    context_window=128000,
                )
            ],
        ),
        ProviderConfig(
            name="ollama-local",
            endpoint="http://localhost:11434",
            api_key=None,
            models=[
                ModelConfig(
                    name="qwen2.5:7b",
                    deployment=ModelDeployment.LOCAL,
                    context_window=32768,
                )
            ],
        ),
    ]


class TestConfigStoreYAML:
    def test_save_and_load_providers(self, temp_dir, cipher, sample_providers):
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, cipher=cipher)

        store.save_providers(sample_providers)
        assert config_path.exists()

        loaded = store.load_providers()
        assert len(loaded) == 2
        assert loaded[0].name == "openai"
        assert loaded[1].name == "ollama-local"

    def test_load_encrypts_api_keys(self, temp_dir, cipher, sample_providers):
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, cipher=cipher)
        store.save_providers(sample_providers)

        raw = config_path.read_text()
        assert "sk-test-123" not in raw  # API Key 不在明文文件中

        loaded = store.load_providers()
        assert loaded[0].api_key == "sk-test-123"  # 解密后恢复

    def test_load_nonexistent_file_returns_empty(self, temp_dir, cipher):
        store = ConfigStore(config_path=temp_dir / "nonexistent.yaml", cipher=cipher)
        providers = store.load_providers()
        assert providers == []

    def test_load_empty_file_returns_empty(self, temp_dir, cipher):
        config_path = temp_dir / "empty.yaml"
        config_path.write_text("")
        store = ConfigStore(config_path=config_path, cipher=cipher)
        providers = store.load_providers()
        assert providers == []

    def test_null_api_key_handled(self, temp_dir, cipher, sample_providers):
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, cipher=cipher)
        store.save_providers(sample_providers)
        loaded = store.load_providers()
        assert loaded[1].api_key is None  # ollama-local 无 key

    def test_save_overwrites_existing(self, temp_dir, cipher, sample_providers):
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, cipher=cipher)
        store.save_providers(sample_providers)
        store.save_providers(sample_providers[:1])
        loaded = store.load_providers()
        assert len(loaded) == 1


class TestConfigStoreSQLite:
    @pytest.fixture
    async def store(self, temp_dir, cipher):
        db_path = temp_dir / "state.db"
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, db_path=db_path, cipher=cipher)
        await store.init_db()
        yield store
        await store.close()

    async def test_init_db_creates_tables(self, store):
        async with store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = {row[0] async for row in cursor}
        assert "provider_status" in tables
        assert "latency_history" in tables

    async def test_update_provider_status(self, store):
        await store.update_provider_status("openai", ProviderStatus.ONLINE)
        status = await store.get_provider_status("openai")
        assert status == ProviderStatus.ONLINE

    async def test_update_status_overwrites(self, store):
        await store.update_provider_status("openai", ProviderStatus.ONLINE)
        await store.update_provider_status("openai", ProviderStatus.DEGRADED)
        status = await store.get_provider_status("openai")
        assert status == ProviderStatus.DEGRADED

    async def test_get_nonexistent_status_returns_unknown(self, store):
        status = await store.get_provider_status("nonexistent")
        assert status == ProviderStatus.UNKNOWN

    async def test_record_latency(self, store):
        await store.record_latency("openai", "gpt-4o", 320.5)
        history = await store.get_latency_history("openai", "gpt-4o", limit=10)
        assert len(history) == 1
        assert history[0]["provider"] == "openai"
        assert history[0]["model"] == "gpt-4o"
        assert history[0]["latency_ms"] == 320.5
        assert "timestamp" in history[0]

    async def test_latency_history_ordered_by_time(self, store):
        await store.record_latency("openai", "gpt-4o", 100.0)
        await store.record_latency("openai", "gpt-4o", 200.0)
        await store.record_latency("openai", "gpt-4o", 300.0)
        history = await store.get_latency_history("openai", "gpt-4o", limit=10)
        timestamps = [h["timestamp"] for h in history]
        assert timestamps == sorted(timestamps)

    async def test_latency_history_limit(self, store):
        for i in range(20):
            await store.record_latency("openai", "gpt-4o", float(i * 10))
        history = await store.get_latency_history("openai", "gpt-4o", limit=5)
        assert len(history) == 5

    async def test_get_latency_history_empty(self, store):
        history = await store.get_latency_history("openai", "nonexistent", limit=10)
        assert history == []

    async def test_get_all_provider_statuses(self, store):
        await store.update_provider_status("openai", ProviderStatus.ONLINE)
        await store.update_provider_status("anthropic", ProviderStatus.OFFLINE)
        statuses = await store.get_all_provider_statuses()
        assert statuses == {"openai": "online", "anthropic": "offline"}
