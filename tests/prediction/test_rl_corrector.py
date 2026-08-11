from __future__ import annotations

import time

import pytest

from src.prediction.rl_corrector import RLCorrector


class TestRLCorrector:
    """RL 修正器测试."""

    # ------------------------------------------------------------------
    # 1. feed 后再 correct，修正值偏移方向正确
    # ------------------------------------------------------------------
    def test_feed_then_correct_shifts_in_right_direction(self):
        """feed 记录正向残差后，correct 应该调高预测值."""
        corrector = RLCorrector()

        # 记录 5 次实际延迟都大于预测值（正残差）
        for i in range(5):
            corrector.feed("openai", "gpt-4o", actual=150.0, predicted_at_timestamp=100.0)

        predictions = [100.0, 100.0, 100.0]
        corrected = corrector.correct("openai", "gpt-4o", predictions)

        # 正残差 → 修正后应该更大的预测值
        assert len(corrected) == len(predictions)
        for c, p in zip(corrected, predictions):
            assert c > p, f"positive residual should push corrected above predicted: {c} > {p}"

    def test_feed_negative_residual_shifts_downward(self):
        """feed 记录负残差后，correct 应该调低预测值（但不低于 0）."""
        corrector = RLCorrector()

        for i in range(5):
            corrector.feed("openai", "gpt-4o", actual=50.0, predicted_at_timestamp=100.0)

        predictions = [80.0, 80.0, 80.0]
        corrected = corrector.correct("openai", "gpt-4o", predictions)

        # 负残差 → 修正后应该更小的预测值
        for c in corrected:
            assert c >= 0, "corrected value must not be negative"

    # ------------------------------------------------------------------
    # 2. 负数修正后 clamp 到 0（不能有负延迟）
    # ------------------------------------------------------------------
    def test_negative_correction_clamped_to_zero(self):
        """当修正导致负值时，应 clamp 到 0."""
        corrector = RLCorrector()

        # 大量负残差使 bias 很负
        for i in range(10):
            corrector.feed("openai", "gpt-4o", actual=10.0, predicted_at_timestamp=100.0)

        predictions = [5.0, 10.0]
        corrected = corrector.correct("openai", "gpt-4o", predictions)

        # 所有值必须 >= 0
        for c in corrected:
            assert c >= 0, f"clamped: {c} >= 0"

    # ------------------------------------------------------------------
    # 3. 无残差数据 → correct 返回原值不变
    # ------------------------------------------------------------------
    def test_no_residual_returns_original_unchanged(self):
        """从未 feed 过任何数据，correct 应返回原值不变."""
        corrector = RLCorrector()
        predictions = [120.0, 140.0, 160.0]
        corrected = corrector.correct("openai", "gpt-4o", predictions)

        assert corrected == pytest.approx(predictions)
        assert corrected is not predictions  # 返回新列表，不是同一引用

    # ------------------------------------------------------------------
    # 4. 超时残差（>1800s）被忽略不计入
    # ------------------------------------------------------------------
    def test_timeout_residuals_ignored(self, monkeypatch):
        """超过 30 分钟（1800s）的残差不参与修正计算."""
        corrector = RLCorrector(timeout_seconds=1800)

        # 先 feed 一批数据
        for i in range(10):
            corrector.feed("openai", "gpt-4o", actual=200.0, predicted_at_timestamp=100.0)

        # 快进时间，使所有残差过期
        monkeypatch.setattr(time, "monotonic", lambda: 999999.0)

        predictions = [100.0, 100.0, 100.0]
        corrected = corrector.correct("openai", "gpt-4o", predictions)

        # 过期残差被忽略，应返回原值
        assert corrected == pytest.approx(predictions)

    # ------------------------------------------------------------------
    # 5. 不同 (provider, model) 残差隔离
    # ------------------------------------------------------------------
    def test_different_provider_model_isolation(self):
        """feed openai/gpt-4o 不应影响 anthropic/claude-3 的修正."""
        corrector = RLCorrector()

        # 给 openai 大量正残差
        for i in range(10):
            corrector.feed("openai", "gpt-4o", actual=300.0, predicted_at_timestamp=100.0)

        # 给 anthropic 负残差
        for i in range(10):
            corrector.feed("anthropic", "claude-3", actual=50.0, predicted_at_timestamp=100.0)

        # openai 应向上修正
        oai_predictions = [100.0, 110.0]
        oai_corrected = corrector.correct("openai", "gpt-4o", oai_predictions)
        for c, p in zip(oai_corrected, oai_predictions):
            assert c > p, f"openai should be corrected upward: {c} > {p}"

        # anthropic 应向下修正
        ant_predictions = [80.0, 90.0]
        ant_corrected = corrector.correct("anthropic", "claude-3", ant_predictions)
        for c in ant_corrected:
            assert c >= 0

        # 两条序列独立，不应互相影响
        assert oai_corrected != pytest.approx(ant_corrected)

    # ------------------------------------------------------------------
    # 6. 趋势分量：斜率为正时逐步增加修正量
    # ------------------------------------------------------------------
    def test_trend_component_increases_with_horizon(self):
        """趋势 slope > 0 时，horizon 越大修正幅度越大."""
        corrector = RLCorrector()

        # 残差逐渐增大 → 正 slope
        for i in range(10):
            corrector.feed("openai", "gpt-4o", actual=float(100 + i * 20), predicted_at_timestamp=100.0)

        predictions = [100.0, 100.0, 100.0]
        corrected = corrector.correct("openai", "gpt-4o", predictions)

        # 趋势向上：越远的 horizon 修正幅度越大
        assert corrected[0] < corrected[1] < corrected[2], (
            f"with positive slope, correction should increase with horizon: {corrected}"
        )
