from __future__ import annotations

import pytest

from src.routing.engine import RouteEngine, RouteResult
from src.routing.strategy import BaselineStrategy
from src.routing.task_profile import DEFAULT_TASK_PROFILES, TaskConstraints, TaskProfile
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestRouteResult:
    """路由结果测试."""

    def test_create_result(self):
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
        )
        result = RouteResult(
            profile=profile,
            score=0.85,
            filtered_out=[],
        )
        assert result.profile == profile
        assert result.score == 0.85
        assert result.filtered_out == []


class TestRouteEngine:
    """路由引擎集成测试."""

    @pytest.fixture
    def candidates(self):
        return [
            ModelProfile(
                provider="openai", model="gpt-4o",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.0025, cost_output_1k=0.0100,
                benchmark=BenchmarkData(arena_elo=1287, coding_swebench=81, reasoning_mmlu=88),
                local_metrics=LocalMetrics(latency_p50_ms=320, latency_p95_ms=850),
            ),
            ModelProfile(
                provider="openai", model="gpt-4o-mini",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.00015, cost_output_1k=0.0006,
                benchmark=BenchmarkData(arena_elo=1150, coding_swebench=60, reasoning_mmlu=72),
                local_metrics=LocalMetrics(latency_p50_ms=100, latency_p95_ms=200),
            ),
            ModelProfile(
                provider="local", model="qwen2.5:7b",
                deployment="local", context_window=32768,
                cost_input_1k=0.0, cost_output_1k=0.0,
                benchmark=BenchmarkData(arena_elo=800, coding_swebench=40),
                local_metrics=LocalMetrics(latency_p50_ms=1500, latency_p95_ms=3000),
            ),
        ]

    @pytest.fixture
    def engine(self):
        return RouteEngine(strategy=BaselineStrategy())

    def test_create_engine(self, engine):
        assert engine.strategy.strategy_id == "baseline"

    def test_route_returns_best_match(self, engine, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        result = engine.route(task, candidates)

        assert result is not None
        assert result.profile is not None
        assert result.score > 0
        # code_review 的 cost 约束 (max_cost_1k=0.005) 会过滤 gpt-4o (avg 0.00625)，
        # 延迟约束 (max_latency_ms=500) 会过滤 qwen (1500ms)。
        # 只剩 gpt-4o-mini 通过全部约束，它就是最佳匹配。
        assert result.profile.model == "gpt-4o-mini"

    def test_route_applies_hard_constraints(self, candidates):
        """硬约束过滤."""
        engine = RouteEngine(strategy=BaselineStrategy())
        task = TaskProfile(
            task_id="t", display_name="T",
            constraints=TaskConstraints(max_latency_ms=200),
        )
        result = engine.route(task, candidates)
        # gpt-4o (320ms) 被过滤，应选中 gpt-4o-mini (100ms)
        assert result.profile.model == "gpt-4o-mini"

    def test_route_max_cost_filter(self, candidates):
        """最大成本约束."""
        engine = RouteEngine(strategy=BaselineStrategy())
        task = TaskProfile(
            task_id="t", display_name="T",
            constraints=TaskConstraints(max_cost_1k=0.001),
        )
        result = engine.route(task, candidates)
        # gpt-4o-mini (0.00015+0.0006)/2=0.000375 通过，qwen 免费通过
        assert result.profile.model in ("gpt-4o-mini", "qwen2.5:7b")

    def test_route_min_context_filter(self, candidates):
        """最小上下文约束."""
        engine = RouteEngine(strategy=BaselineStrategy())
        task = TaskProfile(
            task_id="t", display_name="T",
            constraints=TaskConstraints(min_context=100000),
        )
        result = engine.route(task, candidates)
        # qwen 只有 32k，被过滤
        assert result.profile.model in ("gpt-4o", "gpt-4o-mini")

    def test_route_all_candidates_filtered_returns_none(self, candidates):
        """所有候选都不满足硬约束时返回 None."""
        engine = RouteEngine(strategy=BaselineStrategy())
        task = TaskProfile(
            task_id="t", display_name="T",
            constraints=TaskConstraints(max_latency_ms=10),
        )
        result = engine.route(task, candidates)
        assert result is None

    def test_route_empty_candidates_returns_none(self, engine):
        task = DEFAULT_TASK_PROFILES["code_review"]
        result = engine.route(task, [])
        assert result is None

    def test_route_top_n(self, engine, candidates):
        """获取 Top-N 推荐."""
        # 使用一个约束宽松的任务，确保至少有 2 个候选通过过滤
        task = TaskProfile(
            task_id="t", display_name="T",
            constraints=TaskConstraints(max_latency_ms=5000, max_cost_1k=1.0, min_context=4096),
        )
        results = engine.route_top_n(task, candidates, n=2)
        assert len(results) == 2
        assert results[0].score >= results[1].score
