# tests/config/test_store.py
from pathlib import Path

import pytest

from src.config.crypto import KeyCipher, generate_key
from src.config.models import (
    LatencyRecord,
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


class TestConfigStoreTimeseries:
    """ConfigStore timeseries 表测试."""

    @pytest.fixture
    async def store_with_db(self, temp_dir):
        """创建已初始化 DB 的 ConfigStore."""
        from src.config.store import ConfigStore

        key = generate_key()
        cipher = KeyCipher(key)
        store = ConfigStore(
            config_path=temp_dir / "config.yaml",
            cipher=cipher,
            db_path=temp_dir / "test_ts.db",
        )
        await store.init_db()
        yield store
        await store.close()

    @pytest.mark.asyncio
    async def test_save_latency_records(self, store_with_db):
        """批量写入延迟记录."""
        records = [
            LatencyRecord(provider="openai", model="gpt-4o", latency_ms=320.0),
            LatencyRecord(provider="openai", model="gpt-4o-mini", latency_ms=150.0),
            LatencyRecord(provider="anthropic", model="claude-opus-5", latency_ms=850.0),
        ]
        await store_with_db.save_latency_records(records)

    @pytest.mark.asyncio
    async def test_load_latency_series_default_100(self, store_with_db):
        """加载延迟时序，默认返回最近 100 条."""
        records = [
            LatencyRecord(
                provider="openai", model="gpt-4o", latency_ms=float(i),
                timestamp=f"2026-07-31T12:{i // 60:02d}:{i % 60:02d}Z",
            )
            for i in range(150)
        ]
        await store_with_db.save_latency_records(records)
        result = await store_with_db.load_latency_series("openai", "gpt-4o")
        assert len(result) == 100
        # 子查询 DESC LIMIT 100 → 最近 100 条 (i=50..149)，外层 ASC → 升序
        assert result[0].latency_ms == 50.0
        assert result[-1].latency_ms == 149.0

    @pytest.mark.asyncio
    async def test_load_latency_series_custom_limit(self, store_with_db):
        """自定义返回数量."""
        records = [
            LatencyRecord(
                provider="openai", model="gpt-4o", latency_ms=float(i),
                timestamp=f"2026-07-31T12:{i // 60:02d}:{i % 60:02d}Z",
            )
            for i in range(50)
        ]
        await store_with_db.save_latency_records(records)
        result = await store_with_db.load_latency_series("openai", "gpt-4o", limit=10)
        assert len(result) == 10
        # DESC LIMIT 10 → 最近 10 条 (i=40..49)，外层 ASC → 升序
        assert result[0].latency_ms == 40.0
        assert result[-1].latency_ms == 49.0

    @pytest.mark.asyncio
    async def test_load_latency_series_empty(self, store_with_db):
        """未找到记录时返回空列表."""
        result = await store_with_db.load_latency_series("unknown", "unknown")
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_save_latency_records_empty_list(self, store_with_db):
        """空列表写入不报错."""
        await store_with_db.save_latency_records([])

    @pytest.mark.asyncio
    async def test_latency_history_unchanged(self, store_with_db):
        """验证原有 latency_history 表不受影响."""
        await store_with_db.record_latency("openai", "gpt-4o", 300.0)
        history = await store_with_db.get_latency_history("openai", "gpt-4o")
        assert len(history) == 1
