from __future__ import annotations

from dataclasses import dataclass, field

from src.prediction.engine import LatencyPrediction
from src.routing.strategy import RoutingStrategy
from src.routing.task_profile import TaskProfile
from src.scoring.profile import ModelProfile


@dataclass(frozen=True, slots=True)
class RouteResult:
    """单次路由匹配结果."""

    profile: ModelProfile
    score: float
    filtered_out: list[ModelProfile] = field(default_factory=list, hash=False)


class RouteEngine:
    """路由匹配引擎.

    执行四步匹配算法：
    Step 1: 硬约束过滤 → 候选模型集
    Step 2: Σ(模型能力_i × 任务权重_i) / Σ(权重_i) → 能力得分
    Step 3: + 延迟性价比修正 - 成本惩罚 → 最终得分
    Step 4: 排序输出最佳匹配

    用法:
        engine = RouteEngine(strategy=BaselineStrategy())
        result = engine.route(task_profile, candidates)
        if result:
            print(f"最佳模型: {result.profile.model}, 得分: {result.score:.4f}")
    """

    def __init__(
        self,
        strategy: RoutingStrategy,
        predictions: dict[str, LatencyPrediction] | None = None,
    ) -> None:
        self.strategy = strategy
        self._predictions: dict[str, LatencyPrediction] = predictions or {}

    def _apply_constraints(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
    ) -> tuple[list[ModelProfile], list[ModelProfile]]:
        """Step 1: 硬约束过滤.

        Returns:
            (通过约束的候选, 被过滤的候选)
        """
        passed: list[ModelProfile] = []
        filtered: list[ModelProfile] = []

        for p in candidates:
            constraints = task.constraints

            # 延迟约束
            if p.local_metrics.latency_p50_ms > constraints.max_latency_ms:
                filtered.append(p)
                continue

            # 成本约束
            avg_cost = (p.cost_input_1k + p.cost_output_1k) / 2
            if avg_cost > constraints.max_cost_1k:
                filtered.append(p)
                continue

            # 上下文长度约束
            if p.context_window < constraints.min_context:
                filtered.append(p)
                continue

            passed.append(p)

        return passed, filtered

    def route(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
    ) -> RouteResult | None:
        """路由匹配：返回最佳模型和评分.

        Returns:
            RouteResult 或 None（无候选满足约束时）
        """
        if not candidates:
            return None

        # Step 1: 硬约束过滤
        passed, filtered = self._apply_constraints(task, candidates)
        if not passed:
            return None

        # Step 2-4: 策略评分 + 排序
        scored = self.strategy.score(task, passed, self._predictions)

        return RouteResult(
            profile=scored[0][0],
            score=scored[0][1],
            filtered_out=filtered,
        )

    def route_top_n(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        n: int = 3,
    ) -> list[RouteResult]:
        """路由匹配：返回 Top-N 推荐."""
        if not candidates:
            return []

        passed, filtered = self._apply_constraints(task, candidates)
        if not passed:
            return []

        scored = self.strategy.score(task, passed, self._predictions)

        results: list[RouteResult] = []
        for model, score in scored[:n]:
            results.append(RouteResult(
                profile=model,
                score=score,
                filtered_out=[f for f in filtered if f not in [r.profile for r in results]],
            ))
        return results

    def with_predictions(
        self, predictions: dict[str, LatencyPrediction]
    ) -> RouteEngine:
        """返回绑定了预测数据的新引擎实例."""
        return RouteEngine(strategy=self.strategy, predictions=predictions)
