from __future__ import annotations

import pytest

from src.config.crypto import KeyCipher, generate_key
from src.scoring.database import ScoringDB
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestScoringDB:
    """模型评分数据库测试."""

    @pytest.fixture
    async def db(self, temp_dir):
        """创建已初始化的 ScoringDB."""
        key = generate_key()
        cipher = KeyCipher(key)
        db_path = temp_dir / "test_scoring.db"
        scoring_db = ScoringDB(db_path)
        await scoring_db.init_db()
        yield scoring_db
        await scoring_db.close()

    @pytest.mark.asyncio
    async def test_init_db_creates_profiles_table(self, db):
        """初始化创建 profiles 表."""
        # 写入一条记录验证表存在
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
            benchmark=BenchmarkData(arena_elo=1287.0, coding_swebench=81.0),
        )
        await db.upsert_profile(profile)

    @pytest.mark.asyncio
    async def test_upsert_and_get_profile(self, db):
        """写入并读取模型画像."""
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
            benchmark=BenchmarkData(
                arena_elo=1287.0, coding_swebench=81.0,
                reasoning_mmlu=88.0, math_math=76.0,
            ),
            local_metrics=LocalMetrics(
                latency_p50_ms=320.0, predictability=0.82,
            ),
        )
        await db.upsert_profile(profile)
        loaded = await db.get_profile("openai", "gpt-4o")
        assert loaded is not None
        assert loaded.benchmark.arena_elo == 1287.0
        assert loaded.benchmark.coding_swebench == 81.0
        assert loaded.local_metrics.latency_p50_ms == 320.0

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile_returns_none(self, db):
        """不存在的画像返回 None."""
        loaded = await db.get_profile("unknown", "unknown")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, db):
        """更新已有画像."""
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
        )
        await db.upsert_profile(profile)

        # 更新 benchmark
        updated = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
            benchmark=BenchmarkData(arena_elo=1300.0),
        )
        await db.upsert_profile(updated)
        loaded = await db.get_profile("openai", "gpt-4o")
        assert loaded.benchmark.arena_elo == 1300.0

    @pytest.mark.asyncio
    async def test_list_all_profiles(self, db):
        """列出所有模型画像."""
        p1 = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
        )
        p2 = ModelProfile(
            provider="anthropic", model="claude-opus-5",
            deployment="cloud", context_window=200000,
            cost_input_1k=0.015, cost_output_1k=0.075,
        )
        await db.upsert_profile(p1)
        await db.upsert_profile(p2)
        all_profiles = await db.list_all()
        assert len(all_profiles) == 2

    @pytest.mark.asyncio
    async def test_update_local_metrics(self, db):
        """仅更新本地监控数据."""
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
        )
        await db.upsert_profile(profile)

        new_metrics = LocalMetrics(
            latency_p50_ms=450.0, predictability=0.65,
        )
        await db.update_local_metrics("openai", "gpt-4o", new_metrics)
        loaded = await db.get_profile("openai", "gpt-4o")
        assert loaded.local_metrics.latency_p50_ms == 450.0
        assert loaded.local_metrics.predictability == 0.65
        # benchmark 应保持不变
        assert loaded.benchmark.arena_elo == 0.0
