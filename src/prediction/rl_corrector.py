from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import NamedTuple


class _ResidualEntry(NamedTuple):
    residual: float
    feed_time: float


class RLCorrector:
    """在线 RL 修正器：根据实测延迟 vs 预测延迟的残差修正预测输出.

    维护每个 (provider, model) 的最近 K=10 个残差，使用偏差 + 线性趋势
    对预测值进行逐 horizon 修正，并 clamp 到非负值。

    用法:
        corrector = RLCorrector()
        corrector.feed("openai", "gpt-4o", actual=150.0, predicted_at_timestamp=100.0)
        corrected = corrector.correct("openai", "gpt-4o", [110.0, 120.0])
    """

    def __init__(
        self,
        max_residuals: int = 10,
        timeout_seconds: float = 1800.0,
    ) -> None:
        self.max_residuals = max_residuals
        self.timeout_seconds = timeout_seconds
        # (provider, model) -> deque of _ResidualEntry
        self._residuals: dict[tuple[str, str], deque[_ResidualEntry]] = defaultdict(
            lambda: deque(maxlen=max_residuals)
        )

    def feed(
        self,
        provider: str,
        model: str,
        actual: float,
        predicted_at_timestamp: float,
    ) -> None:
        """记录一次残差.

        Args:
            actual: 实测延迟 (ms)
            predicted_at_timestamp: 在发送请求时预测的延迟 (ms)
        """
        key = (provider, model)
        residual = actual - predicted_at_timestamp
        self._residuals[key].append(
            _ResidualEntry(residual=residual, feed_time=time.monotonic())
        )

    def correct(
        self,
        provider: str,
        model: str,
        predictions: list[float],
    ) -> list[float]:
        """根据历史残差修正预测值.

        Args:
            predictions: 原始预测值列表，按 horizon=1, 2, ..., H 排列

        Returns:
            修正后的预测值列表，长度与输入相同，每个值 >= 0
        """
        key = (provider, model)
        entries = self._residuals.get(key)

        if not entries:
            return list(predictions)

        now = time.monotonic()
        valid = [
            e.residual
            for e in entries
            if now - e.feed_time <= self.timeout_seconds
        ]

        if not valid:
            return list(predictions)

        n = len(valid)

        # bias = mean(residuals)
        bias = sum(valid) / n

        # alpha = linear_regression_slope (OLS against index 0, 1, ..., n-1)
        alpha = 0.0
        if n >= 2:
            mean_x = (n - 1) / 2.0  # mean of 0..n-1
            # covariance(x, y) / variance(x)
            num, den = 0.0, 0.0
            for i, r in enumerate(valid):
                dx = i - mean_x
                num += dx * r
                den += dx * dx
            if den > 0:
                alpha = num / den

        corrected = []
        for h, y_pred in enumerate(predictions, start=1):
            y_corr = y_pred + bias + alpha * h
            if y_corr < 0:
                y_corr = 0.0
            corrected.append(y_corr)

        return corrected
