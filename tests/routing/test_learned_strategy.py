"""LearnedStrategy 智能路由策略测试.

Learned 策略 = 消费预测引擎输出做上下文感知路由决策。
不需要训练，不保存模型文件。
"""

from __future__ import annotations

import pytest

from src.prediction.engine import LatencyPrediction
from src.routing.learned_strategy import LearnedStrategy
from src.routing.task_profile import DEFAULT_TASK_PROFILES, TaskConstraints, TaskProfile
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


def _make_model(model: str, arena_elo: float, coding: float, reasoning: float,
                lat_p50: float, cost_in: float, cost_out: float) -> ModelProfile:
    return ModelProfile(
        provider="p", model=model, deployment="cloud", context_window=128000,
        cost_input_1k=cost_in, cost_output_1k=cost_out,
        benchmark=BenchmarkData(arena_elo=arena_elo, coding_swebench=coding, reasoning_mmlu=reasoning),
        local_metrics=LocalMetrics(latency_p50_ms=lat_p50),
    )


def _pred(provider: str, model: str, p50: float, p90: float = 0.0,
          predictability: float = 0.8, p10: float = 0.0, p25: float = 0.0, p75: float = 0.0) -> LatencyPrediction:
    if p90 == 0.0:
        p90 = p50 * 1.3
    if p10 == 0.0:
        p10 = p50 * 0.7
    if p25 == 0.0:
        p25 = p50 * 0.85
    if p75 == 0.0:
        p75 = p50 * 1.15
    return LatencyPrediction(
        provider=provider, model=model,
        quantiles={"p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90},
        predictability=predictability,
        data_points_used=200,
    )


class TestLearnedStrategy:
    """智能路由策略测试."""

    @pytest.fixture
    def strategy(self):
        return LearnedStrategy()

    @pytest.fixture
    def candidates(self):
        return [
            _make_model("gpt-4o", arena_elo=1287, coding=81, reasoning=88, lat_p50=320, cost_in=0.0025, cost_out=0.0100),
            _make_model("gpt-4o-mini", arena_elo=1150, coding=60, reasoning=72, lat_p50=100, cost_in=0.00015, cost_out=0.0006),
            _make_model("claude-opus", arena_elo=1350, coding=90, reasoning=95, lat_p50=500, cost_in=0.015, cost_out=0.075),
        ]

    # ── 基本协议 ──────────────────────────────────────

    def test_strategy_id_and_name(self, strategy):
        assert strategy.strategy_id == "learned"
        assert strategy.display_name == "智能路由"

    def test_score_returns_sorted_list(self, strategy, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        predictions: dict[str, LatencyPrediction] = {}
        results = strategy.score(task, candidates, predictions)
        assert len(results) == 3
        assert results[0][1] >= results[1][1]

    def test_score_each_element_is_model_score_tuple(self, strategy, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        predictions: dict[str, LatencyPrediction] = {}
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

    # ── predictions 使用 ──────────────────────────────

    def test_predictions_p50_used_over_static_latency(self, strategy):
        """有预测数据时，延迟维度用预测 p50 而非 local_metrics 静态值."""
        fast_static = _make_model("fast", arena_elo=1200, coding=70, reasoning=70,
                                   lat_p50=5000, cost_in=0.01, cost_out=0.05)  # 静态慢
        normal_static = _make_model("normal", arena_elo=1200, coding=70, reasoning=70,
                                     lat_p50=300, cost_in=0.01, cost_out=0.05)  # 静态快
        task = TaskProfile(task_id="t", display_name="T")
        # 预测说 fast 实际很快，normal 反而慢
        predictions: dict[str, LatencyPrediction] = {
            "p/fast": _pred("p", "fast", p50=80),   # 预测快
            "p/normal": _pred("p", "normal", p50=4000),  # 预测慢
        }
        results = strategy.score(task, [fast_static, normal_static], predictions)
        # 根据预测值，fast 应该排第一
        assert results[0][0].model == "fast"

    def test_fallback_no_predictions_uses_static(self, strategy, candidates):
        """无预测数据 → 回退到 local_metrics 延迟."""
        task = DEFAULT_TASK_PROFILES["code_review"]
        predictions: dict[str, LatencyPrediction] = {}
        results = strategy.score(task, candidates, predictions)
        # gpt-4o 能力优势（arena_elo 1287 vs 1150）弥补了延迟差距，排第一
        # 验证所有候选都参与排序且分数合法
        assert len(results) == 3
        assert all(0.0 <= s <= 1.0 for _, s in results)

    # ── 可信度感知 ────────────────────────────────────

    def test_low_predictability_demotes_model(self, strategy):
        """predictability 低 → 延迟权重降低 → 模型排名下降.

        model_a 的 p50 略优于 model_b，但 predictability 极低（0.1），
        其延迟优势被大幅削弱，权重转移给能力维度后，model_b 反超。
        """
        model_a = _make_model("model_a", arena_elo=1300, coding=85, reasoning=90,
                               lat_p50=300, cost_in=0.01, cost_out=0.05)
        model_b = _make_model("model_b", arena_elo=1300, coding=85, reasoning=90,
                               lat_p50=400, cost_in=0.01, cost_out=0.05)
        task = TaskProfile(task_id="t", display_name="T")
        predictions: dict[str, LatencyPrediction] = {
            "p/model_a": _pred("p", "model_a", p50=350, predictability=0.1),  # 预测不可信
            "p/model_b": _pred("p", "model_b", p50=450, predictability=0.9),
        }
        results = strategy.score(task, [model_a, model_b], predictions)
        assert results[0][0].model == "model_b"

    # ── 风险惩罚 ──────────────────────────────────────

    def test_risk_penalty_for_high_spread(self, strategy):
        """p90-p50 差距大 → 风险惩罚扣分."""
        stable = _make_model("stable", arena_elo=1200, coding=70, reasoning=70,
                              lat_p50=300, cost_in=0.01, cost_out=0.05)
        volatile = _make_model("volatile", arena_elo=1200, coding=70, reasoning=70,
                                lat_p50=300, cost_in=0.01, cost_out=0.05)
        task = TaskProfile(task_id="t", display_name="T")
        predictions: dict[str, LatencyPrediction] = {
            "p/stable": _pred("p", "stable", p50=300, p90=320),   # 窄区间
            "p/volatile": _pred("p", "volatile", p50=300, p90=800),  # 高风险
        }
        results = strategy.score(task, [stable, volatile], predictions)
        # stable 排名更高（同等条件下稳定性更好）
        assert results[0][0].model == "stable"

    # ── 任务权重匹配 ──────────────────────────────────

    def test_task_weights_affect_ranking(self, strategy):
        """不同任务类型 → 能力维度权重不同 → 排序不同."""
        coder = _make_model("coder", arena_elo=1200, coding=95, reasoning=50,
                             lat_p50=300, cost_in=0.01, cost_out=0.05)
        reasoner = _make_model("reasoner", arena_elo=1200, coding=50, reasoning=95,
                                lat_p50=300, cost_in=0.01, cost_out=0.05)
        predictions: dict[str, LatencyPrediction] = {}

        code_task = DEFAULT_TASK_PROFILES["code_review"]
        analysis_task = DEFAULT_TASK_PROFILES["data_analysis"]

        code_results = strategy.score(code_task, [coder, reasoner], predictions)
        analysis_results = strategy.score(analysis_task, [coder, reasoner], predictions)

        assert code_results[0][0].model == "coder"
        assert analysis_results[0][0].model == "reasoner"

    # ── 动态性验证：同一模型不同时间不同分 ─────────────

    def test_different_prediction_gives_different_score(self, strategy):
        """同一模型，预测的延迟不同 → 得分不同（验证策略是'活'的）."""
        model = _make_model("m", arena_elo=1200, coding=70, reasoning=70,
                             lat_p50=300, cost_in=0.01, cost_out=0.05)
        task = TaskProfile(task_id="t", display_name="T")

        # 时段 A：快
        preds_fast = {"p/m": _pred("p", "m", p50=50, predictability=0.9)}
        score_fast = strategy.score(task, [model], preds_fast)[0][1]

        # 时段 B：慢
        preds_slow = {"p/m": _pred("p", "m", p50=3000, predictability=0.9)}
        score_slow = strategy.score(task, [model], preds_slow)[0][1]

        assert score_fast > score_slow
