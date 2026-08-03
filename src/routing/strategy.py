from __future__ import annotations

from typing import Protocol

from src.prediction.engine import LatencyPrediction
from src.routing.task_profile import TaskProfile
from src.scoring.profile import ModelProfile


class RoutingStrategy(Protocol):
    """可插拔路由策略接口.

    所有策略必须实现此接口。GUI 设置页可即时切换。
    """

    strategy_id: str
    display_name: str

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        """对候选模型评分并降序排列."""
        ...

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        """解释评分依据."""
        ...


def _capability_score(task: TaskProfile, profile: ModelProfile) -> float:
    """加权能力得分: Σ(能力_i × 权重_i) / Σ(权重_i).

    若任务无权重，使用 arena_elo 作为默认维度。
    """
    caps = profile.capability_vector()
    weights = task.weights or {"arena_elo": 1.0}

    numerator = 0.0
    denominator = 0.0
    for dim, weight in weights.items():
        value = caps.get(dim, 0.0)
        # 归一化 arena_elo 到 0-100
        if dim == "arena_elo":
            value = max(0.0, min(100.0, value / 15.0))
        numerator += value * weight
        denominator += weight

    if denominator == 0:
        return 0.0
    return numerator / denominator / 100.0  # 归一化到 [0, 1]


def _latency_score(latency_p50: float, max_latency: float = 5000.0) -> float:
    """延迟得分：延迟越低得分越高."""
    if latency_p50 <= 0:
        return 1.0
    return max(0.0, 1.0 - (latency_p50 / max_latency))


def _cost_score(cost_input: float, cost_output: float, max_cost: float = 0.1) -> float:
    """成本得分：成本越低得分越高."""
    avg_cost = (cost_input + cost_output) / 2
    if avg_cost <= 0:
        return 1.0
    return max(0.0, 1.0 - (avg_cost / max_cost))


class BaselineStrategy:
    """均衡评分 (w_cap=0.4, w_lat=0.3, w_cost=0.3)."""

    strategy_id = "baseline"
    display_name = "均衡评分"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = 0.4 * cap + 0.3 * lat + 0.3 * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return (
            f"[{self.display_name}] {model.model}: 最终得分 {score:.4f} "
            f"(能力={_capability_score(task, model):.4f}, "
            f"延迟={_latency_score(model.local_metrics.latency_p50_ms):.4f}, "
            f"成本={_cost_score(model.cost_input_1k, model.cost_output_1k):.4f})"
        )


class CostFirstStrategy:
    """成本优先 (w_cap=0.2, w_lat=0.2, w_cost=0.6)."""

    strategy_id = "cost_first"
    display_name = "成本优先"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = 0.2 * cap + 0.2 * lat + 0.6 * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return (
            f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"
        )


class QualityFirstStrategy:
    """质量优先 (w_cap=0.7, w_lat=0.2, w_cost=0.1).

    注：w_cost=0.1 是有意偏离计划（计划为 0.2）——质量优先策略应
    弱化成本考量，让能力强但昂贵的模型也能胜出。
    """

    strategy_id = "quality_first"
    display_name = "质量优先"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = 0.7 * cap + 0.2 * lat + 0.1 * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"


class LatencyAwareStrategy:
    """延迟感知 (w_cap=0.3, w_lat=0.6, w_cost=0.1)."""

    strategy_id = "latency_aware"
    display_name = "延迟感知"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = 0.3 * cap + 0.6 * lat + 0.1 * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"


class TaskSpecificStrategy:
    """任务分域 — 按 TaskProfile.weights 动态分配能力:延迟:成本权重."""

    strategy_id = "task_specific"
    display_name = "任务分域"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        avg_weight = sum(task.weights.values()) / max(len(task.weights), 1)
        w_cap = 0.3 + 0.4 * avg_weight
        w_lat = 0.4 * (1.0 - avg_weight)
        w_cost = 0.3 * (1.0 - avg_weight)
        total = w_cap + w_lat + w_cost
        w_cap /= total
        w_lat /= total
        w_cost /= total

        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = w_cap * cap + w_lat * lat + w_cost * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"


# 策略注册表
BUILTIN_STRATEGIES: dict[str, RoutingStrategy] = {
    "baseline": BaselineStrategy(),
    "cost_first": CostFirstStrategy(),
    "quality_first": QualityFirstStrategy(),
    "latency_aware": LatencyAwareStrategy(),
    "task_specific": TaskSpecificStrategy(),
}
