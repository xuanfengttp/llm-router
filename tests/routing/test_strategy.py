from __future__ import annotations

import pytest

from src.routing.strategy import (
    BaselineStrategy,
    CostFirstStrategy,
    LatencyAwareStrategy,
    QualityFirstStrategy,
    TaskSpecificStrategy,
)
from src.routing.task_profile import DEFAULT_TASK_PROFILES, TaskConstraints, TaskProfile
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestBaselineStrategy:
    """均衡评分策略测试."""

    @pytest.fixture
    def strategy(self):
        return BaselineStrategy()

    @pytest.fixture
    def candidates(self):
        return [
            ModelProfile(
                provider="openai", model="gpt-4o",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.0025, cost_output_1k=0.0100,
                benchmark=BenchmarkData(arena_elo=1287, coding_swebench=81, reasoning_mmlu=88),
                local_metrics=LocalMetrics(latency_p50_ms=320),
            ),
            ModelProfile(
                provider="openai", model="gpt-4o-mini",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.00015, cost_output_1k=0.0006,
                benchmark=BenchmarkData(arena_elo=1150, coding_swebench=60, reasoning_mmlu=72),
                local_metrics=LocalMetrics(latency_p50_ms=100),
            ),
        ]

    def test_strategy_id_and_name(self, strategy):
        assert strategy.strategy_id == "baseline"
        assert strategy.display_name == "均衡评分"

    def test_score_returns_sorted_list(self, strategy, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        predictions: dict[str, object] = {}
        results = strategy.score(task, candidates, predictions)
        assert len(results) == 2
        # 按分数降序排列
        assert results[0][1] >= results[1][1]

    def test_score_each_element_is_model_score_tuple(self, strategy, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        predictions: dict[str, object] = {}
        results = strategy.score(task, candidates, predictions)
        for model, score in results:
            assert isinstance(model, ModelProfile)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_explain_returns_string(self, strategy, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        explanation = strategy.explain(task, candidates[0], 0.85)
        assert isinstance(explanation, str)
        assert len(explanation) > 0


class TestCostFirstStrategy:
    """成本优先策略."""

    def test_cheaper_model_scores_higher(self):
        strategy = CostFirstStrategy()
        expensive = ModelProfile(
            provider="p", model="expensive", deployment="cloud",
            context_window=128000, cost_input_1k=0.10, cost_output_1k=0.50,
            benchmark=BenchmarkData(arena_elo=1300),
        )
        cheap = ModelProfile(
            provider="p", model="cheap", deployment="cloud",
            context_window=128000, cost_input_1k=0.001, cost_output_1k=0.005,
            benchmark=BenchmarkData(arena_elo=1100),
        )
        task = TaskProfile(task_id="t", display_name="T")
        predictions: dict[str, object] = {}
        results = strategy.score(task, [expensive, cheap], predictions)
        # 便宜模型得分更高
        assert results[0][0].model == "cheap"


class TestQualityFirstStrategy:
    """质量优先策略."""

    def test_better_benchmark_scores_higher(self):
        strategy = QualityFirstStrategy()
        good = ModelProfile(
            provider="p", model="good", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(arena_elo=1400, coding_swebench=90, reasoning_mmlu=92),
        )
        bad = ModelProfile(
            provider="p", model="bad", deployment="cloud",
            context_window=128000, cost_input_1k=0.001, cost_output_1k=0.005,
            benchmark=BenchmarkData(arena_elo=900, coding_swebench=30, reasoning_mmlu=40),
        )
        task = TaskProfile(task_id="t", display_name="T", weights={"coding": 1.0, "reasoning": 1.0})
        predictions: dict[str, object] = {}
        results = strategy.score(task, [bad, good], predictions)
        assert results[0][0].model == "good"


class TestLatencyAwareStrategy:
    """延迟感知策略."""

    def test_lower_latency_scores_higher(self):
        strategy = LatencyAwareStrategy()
        fast = ModelProfile(
            provider="p", model="fast", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(arena_elo=1200),
            local_metrics=LocalMetrics(latency_p50_ms=50),
        )
        slow = ModelProfile(
            provider="p", model="slow", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(arena_elo=1250),
            local_metrics=LocalMetrics(latency_p50_ms=5000),
        )
        task = TaskProfile(task_id="t", display_name="T")
        predictions: dict[str, object] = {}
        results = strategy.score(task, [slow, fast], predictions)
        assert results[0][0].model == "fast"


class TestTaskSpecificStrategy:
    """任务分域策略."""

    def test_different_tasks_get_different_rankings(self):
        strategy = TaskSpecificStrategy()
        coder = ModelProfile(
            provider="p", model="coder", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(coding_swebench=95, reasoning_mmlu=50),
        )
        reasoner = ModelProfile(
            provider="p", model="reasoner", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(coding_swebench=50, reasoning_mmlu=95),
        )
        code_task = DEFAULT_TASK_PROFILES["code_review"]
        analysis_task = DEFAULT_TASK_PROFILES["data_analysis"]
        predictions: dict[str, object] = {}

        code_results = strategy.score(code_task, [coder, reasoner], predictions)
        analysis_results = strategy.score(analysis_task, [coder, reasoner], predictions)

        # 代码任务 coder 排第一
        assert code_results[0][0].model == "coder"
        # 分析任务 reasoner 排第一
        assert analysis_results[0][0].model == "reasoner"
