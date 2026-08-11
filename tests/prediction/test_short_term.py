from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.config.models import LatencyRecord
from src.prediction.short_term import ShortTermPredictor


def _records(values: list[float], provider="openai", model="gpt-4o") -> list[LatencyRecord]:
    """把一组延迟值转成按时间升序的 LatencyRecord（30min 间隔）."""
    base = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)
    return [
        LatencyRecord(
            provider=provider,
            model=model,
            latency_ms=v,
            timestamp=(base + timedelta(minutes=30 * i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        for i, v in enumerate(values)
    ]


class TestShortTermPredictor:
    """EWMA 短期预测测试."""

    def test_predict_returns_quantiles(self):
        """返回 5 个分位数且单调递增."""
        pred = ShortTermPredictor(horizon=2, alpha=0.3)
        result = pred.predict(_records([200.0 + i * 5 for i in range(50)]))
        assert result is not None
        assert set(result.keys()) == {"p10", "p25", "p50", "p75", "p90"}
        for h in range(2):
            assert result["p10"][h] <= result["p25"][h] <= result["p50"][h] <= result["p75"][h] <= result["p90"][h]

    def test_predict_quantiles_are_lists_with_horizon_length(self):
        """每个分位数是长度=horizon 的列表."""
        pred = ShortTermPredictor(horizon=3)
        result = pred.predict(_records([300.0] * 50))
        assert len(result["p50"]) == 3

    def test_predict_positive(self):
        """所有分位数 > 0."""
        pred = ShortTermPredictor(horizon=2)
        result = pred.predict(_records([200.0 + i for i in range(50)]))
        for q in result.values():
            for v in q:
                assert v > 0

    def test_predict_follows_trend(self):
        """明显上升趋势 → 预测 p50 > 末值."""
        pred = ShortTermPredictor(horizon=2, alpha=0.3)
        rising = [100.0 + i * 10 for i in range(50)]  # 100→590
        result = pred.predict(_records(rising))
        assert result is not None
        assert result["p50"][0] > rising[-1]

    def test_insufficient_data(self):
        """< 2 点 → None."""
        pred = ShortTermPredictor(horizon=2)
        assert pred.predict(_records([100.0])) is None
        assert pred.predict([]) is None

    def test_stable_series_narrow_spread(self):
        """常数序列 → 分位数离散度极小（p10≈p90）."""
        pred = ShortTermPredictor(horizon=1)
        result = pred.predict(_records([250.0] * 50))
        assert abs(result["p90"][0] - result["p10"][0]) < 5.0
