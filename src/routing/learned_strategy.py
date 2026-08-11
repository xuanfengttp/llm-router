"""LearnedStrategy — 智能路由策略.

消费预测引擎输出（p50/p90/predictability），结合模型能力与任务类型，
做上下文感知的动态路由决策。不需要训练，不保存模型文件。
"""

from __future__ import annotations

from src.prediction.engine import LatencyPrediction
from src.routing.task_profile import TaskProfile
from src.scoring.profile import ModelProfile


def _capability_score(task: TaskProfile, profile: ModelProfile) -> float:
    """加权能力得分：全维度精准匹配."""
    caps = profile.capability_vector()
    weights = task.weights or {"arena_elo": 1.0}
    numerator = 0.0
    denominator = 0.0
    for dim, weight in weights.items():
        value = caps.get(dim, 0.0)
        if dim == "arena_elo":
            value = max(0.0, min(100.0, value / 15.0))
        numerator += value * weight
        denominator += weight
    if denominator == 0:
        return 0.0
    return numerator / denominator / 100.0


def _latency_score(p50: float, max_latency: float = 5000.0) -> float:
    if p50 <= 0:
        return 1.0
    return max(0.0, 1.0 - (p50 / max_latency))


def _cost_score(cost_input: float, cost_output: float, max_cost: float = 0.1) -> float:
    avg_cost = (cost_input + cost_output) / 2
    if avg_cost <= 0:
        return 1.0
    return max(0.0, 1.0 - (avg_cost / max_cost))


class LearnedStrategy:
    """智能路由：根据环境（预测数据 + 任务类型）动态评分."""

    strategy_id = "learned"
    display_name = "智能路由"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored: list[tuple[ModelProfile, float]] = []
        for p in candidates:
            key = f"{p.provider}/{p.model}"
            pred = predictions.get(key)

            # 能力得分与成本得分（与预测无关）
            cap = _capability_score(task, p)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)

            # 基准权重
            w_cap = 0.4
            w_lat = 0.35
            w_cost = 0.25

            if pred is not None:
                lat = _latency_score(pred.p50)
                predictability = pred.predictability
                # 风险惩罚: p90-p50 差距大时扣分
                spread = pred.p90 - pred.p50
                risk_penalty = min(spread / max(pred.p50, 1.0), 1.0) * 0.15
                # 可信度调整：predictability 低 → 延迟权重降
                lat_weight_effective = w_lat * predictability
                cap_weight_effective = w_cap + (w_lat - lat_weight_effective)
                final = (cap_weight_effective * cap
                         + lat_weight_effective * lat
                         + w_cost * cost
                         - risk_penalty)
            else:
                # 无预测数据 → 回退 static
                lat = _latency_score(p.local_metrics.latency_p50_ms)
                final = w_cap * cap + w_lat * lat + w_cost * cost

            scored.append((p, max(0.0, min(1.0, final))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return (
            f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"
        )
