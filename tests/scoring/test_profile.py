from __future__ import annotations

import pytest

from src.scoring.profile import (
    BenchmarkData,
    BenchmarkFetcher,
    LocalMetrics,
    ModelProfile,
)


class TestBenchmarkData:
    """公开 Benchmark 数据测试."""

    def test_create_benchmark(self):
        bm = BenchmarkData(
            arena_elo=1287.5,
            coding_swebench=38.4,
            reasoning_mmlu=88.7,
            math_math=76.6,
        )
        assert bm.arena_elo == 1287.5
        assert bm.coding_swebench == 38.4
        assert bm.reasoning_mmlu == 88.7
        assert bm.math_math == 76.6
        # 可选字段默认值
        assert bm.instruction_follow == 0.0
        assert bm.multilingual == 0.0
        assert bm.tool_use == 0.0

    def test_benchmark_is_frozen(self):
        bm = BenchmarkData(arena_elo=100.0)
        with pytest.raises(Exception):
            bm.arena_elo = 200.0  # type: ignore[misc]

    def test_benchmark_to_dict(self):
        bm = BenchmarkData(arena_elo=1200.0, coding_swebench=40.0)
        d = bm.to_dict()
        assert d["arena_elo"] == 1200.0
        assert d["coding_swebench"] == 40.0


class TestLocalMetrics:
    """本地监控指标测试."""

    def test_create_local_metrics(self):
        lm = LocalMetrics(
            latency_p50_ms=320.0,
            latency_p95_ms=850.0,
            latency_p99_ms=1800.0,
            predicted_latency_ms=380.0,
            predictability=0.82,
            throughput_rpm=120.0,
            error_rate=0.003,
        )
        assert lm.latency_p50_ms == 320.0
        assert lm.predictability == 0.82
        assert lm.error_rate == 0.003

    def test_local_metrics_defaults(self):
        lm = LocalMetrics()
        assert lm.latency_p50_ms == 0.0
        assert lm.predictability == 0.0
        assert lm.error_rate == 0.0

    def test_local_metrics_update(self):
        """返回新实例（不可变模式）."""
        lm = LocalMetrics(latency_p50_ms=100.0)
        updated = lm.with_latency(p50_ms=200.0, p95_ms=300.0, p99_ms=400.0)
        assert updated.latency_p50_ms == 200.0
        assert updated.latency_p95_ms == 300.0
        assert lm.latency_p50_ms == 100.0  # 原实例不变


class TestModelProfile:
    """模型能力画像测试."""

    def test_create_profile(self):
        bm = BenchmarkData(arena_elo=1200.0, coding_swebench=40.0)
        lm = LocalMetrics(latency_p50_ms=320.0)
        profile = ModelProfile(
            provider="openai",
            model="gpt-4o",
            deployment="cloud",
            context_window=128000,
            cost_input_1k=0.0025,
            cost_output_1k=0.0100,
            benchmark=bm,
            local_metrics=lm,
        )
        assert profile.provider == "openai"
        assert profile.model == "gpt-4o"
        assert profile.benchmark.arena_elo == 1200.0
        assert profile.local_metrics.latency_p50_ms == 320.0

    def test_profile_is_frozen(self):
        profile = ModelProfile(
            provider="p", model="m", deployment="cloud",
            context_window=4096, cost_input_1k=0.0, cost_output_1k=0.0,
        )
        with pytest.raises(Exception):
            profile.model = "new"  # type: ignore[misc]

    def test_profile_with_local_metrics(self):
        """更新本地监控数据."""
        profile = ModelProfile(
            provider="p", model="m", deployment="cloud",
            context_window=4096, cost_input_1k=0.0, cost_output_1k=0.0,
        )
        new_lm = LocalMetrics(latency_p50_ms=250.0, predictability=0.9)
        updated = profile.with_local_metrics(new_lm)
        assert updated.local_metrics.latency_p50_ms == 250.0
        assert profile.local_metrics.latency_p50_ms == 0.0  # 原实例不变

    def test_profile_capability_vector(self):
        """能力向量提取."""
        bm = BenchmarkData(
            arena_elo=1250.0, coding_swebench=41.0,
            reasoning_mmlu=88.0, math_math=76.0,
        )
        profile = ModelProfile(
            provider="p", model="m", deployment="cloud",
            context_window=128000, cost_input_1k=0.005, cost_output_1k=0.010,
            benchmark=bm,
        )
        vec = profile.capability_vector()
        assert "coding" in vec
        assert "reasoning" in vec
        assert "math" in vec
        assert vec["coding"] == 41.0
        assert vec["reasoning"] == 88.0
        assert vec["math"] == 76.0


class TestBenchmarkFetcher:
    """Benchmark 数据拉取器测试."""

    def test_fetcher_has_default_sources(self):
        fetcher = BenchmarkFetcher()
        assert len(fetcher.sources) >= 2  # Chatbot Arena + OpenRouter

    def test_parse_arena_response(self):
        """解析 Chatbot Arena 格式的响应."""
        fetcher = BenchmarkFetcher()
        sample = {
            "gpt-4o": {
                "arena_score": 1287,
                "coding": 81.4,
                "math": 72.3,
                "reasoning": 85.6,
            }
        }
        result = fetcher._parse_arena_data(sample)
        assert "gpt-4o" in result
        assert result["gpt-4o"].arena_elo == 1287.0
        assert result["gpt-4o"].coding_swebench == 81.4

    def test_parse_openrouter_response(self):
        """解析 OpenRouter 格式的响应."""
        fetcher = BenchmarkFetcher()
        sample = {
            "data": [
                {
                    "slug": "gpt-4o",
                    "metrics": {
                        "coding": 80.0,
                        "reasoning": 88.0,
                        "instruction_following": 91.0,
                    }
                }
            ]
        }
        result = fetcher._parse_openrouter_data(sample)
        assert "gpt-4o" in result
        assert result["gpt-4o"].coding_swebench == 80.0
        assert result["gpt-4o"].instruction_follow == 91.0

    def test_merge_sources(self):
        """多数据源融合."""
        fetcher = BenchmarkFetcher()
        arena = {"gpt-4o": BenchmarkData(arena_elo=1287.0, coding_swebench=81.0)}
        openrouter = {"gpt-4o": BenchmarkData(coding_swebench=79.0, reasoning_mmlu=88.0)}
        merged = fetcher._merge_benchmarks([arena, openrouter])
        assert "gpt-4o" in merged
        # 优先使用第一个源的 arena_elo（仅 Arena 有）
        assert merged["gpt-4o"].arena_elo == 1287.0
        # coding 取平均值
        assert merged["gpt-4o"].coding_swebench == 80.0
