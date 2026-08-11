from __future__ import annotations

import numpy as np

from src.config.models import LatencyRecord

# 正态分布分位数乘子
_Z_P10 = 1.282  # ±1.282σ ≈ 80% 区间
_Z_P25 = 0.674  # ±0.674σ ≈ 50% 区间


class ShortTermPredictor:
    """Holt 线性趋势短期延迟预测器.

    轻量、无需 neuralforecast，始终可用。使用 Holt's linear trend 平滑
    水平与趋势分量，输出未来 horizon 步的 5 个分位数。

    公式:
        level(t) = α·y(t) + (1-α)·(level(t-1) + trend(t-1))
        trend(t) = β·(level(t)-level(t-1)) + (1-β)·trend(t-1)
        forecast(t+h) = level(t) + h·trend(t)
        p50 = forecast; p25/75 = forecast ∓ 0.674σ; p10/90 = forecast ∓ 1.282σ

    用法:
        pred = ShortTermPredictor(horizon=2, alpha=0.3, beta=0.1)
        q = pred.predict(records)  # {"p10": [...], "p50": [...], ...}
    """

    def __init__(
        self,
        horizon: int = 2,
        alpha: float = 0.3,
        beta: float = 0.1,
    ) -> None:
        self.horizon = horizon
        self.alpha = alpha
        self.beta = beta

    def predict(
        self, records: list[LatencyRecord]
    ) -> dict[str, list[float]] | None:
        """对未来 horizon 步预测 5 个分位数.

        Returns:
            {"p10": [...], "p25": [...], "p50": [...], "p75": [...], "p90": [...]}
            每个值长度=horizon；数据不足（<2）返回 None。
        """
        if len(records) < 2:
            return None

        values = np.array([r.latency_ms for r in records], dtype=float)

        # 1. Holt's linear trend
        level, trend = float(values[0]), 0.0
        residuals = np.zeros(len(values))
        for i, v in enumerate(values):
            if i == 0:
                residuals[0] = 0.0
                continue
            prev_level = level
            level = self.alpha * float(v) + (1 - self.alpha) * (prev_level + trend)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * trend
            residuals[i] = v - (prev_level + trend)  # 一步预测残差

        # 2. 残差 std
        sigma = float(np.std(residuals[1:])) if len(residuals) > 1 else 0.0

        # 3. 外推 + 分位数
        p50, p25, p75, p10, p90 = [], [], [], [], []
        for h in range(1, self.horizon + 1):
            center = max(0.0, level + trend * h)
            p50.append(center)
            p25.append(max(0.0, center - _Z_P25 * sigma))
            p75.append(max(0.0, center + _Z_P25 * sigma))
            p10.append(max(0.0, center - _Z_P10 * sigma))
            p90.append(max(0.0, center + _Z_P10 * sigma))

        return {
            "p10": p10,
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "p90": p90,
        }

    def compute_predictability(self, records: list[LatencyRecord]) -> float:
        """计算可预测性得分 (0-1).

        使用 Holt 一步预测残差的方差与总方差之比。
        得分 0 = 完全随机不可预测，得分 1 = 完美可预测。
        """
        if len(records) < 3:
            return 0.0

        values = np.array([r.latency_ms for r in records], dtype=float)

        # 运行 Holt 获取一步预测残差
        level, trend = float(values[0]), 0.0
        residuals = np.zeros(len(values))
        for i, v in enumerate(values):
            if i == 0:
                continue
            prev_level = level
            level = self.alpha * float(v) + (1 - self.alpha) * (prev_level + trend)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * trend
            residuals[i] = v - (prev_level + trend)

        predicted = values[1:] - residuals[1:]  # 实际值 - 残差 = 预测值

        from src.prediction.model import PredictabilityScore

        return PredictabilityScore.compute(values[1:], predicted)
