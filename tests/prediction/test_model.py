from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.prediction.model import LatencyPredictor, PredictabilityScore


class TestPredictabilityScore:
    """可预测性评分测试."""

    def test_perfect_prediction(self):
        """完美预测得分为 1.0."""
        result = PredictabilityScore.compute(
            actual=np.array([1.0, 2.0, 3.0]),
            predicted=np.array([1.0, 2.0, 3.0]),
        )
        assert result == pytest.approx(1.0)

    def test_no_predictability(self):
        """无预测能力时得分接近 0."""
        actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        predicted = np.array([3.0, 3.0, 3.0, 3.0, 3.0])
        result = PredictabilityScore.compute(actual, predicted)
        assert result == pytest.approx(0.0)

    def test_partial_predictability(self):
        """部分可预测."""
        actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        predicted = np.array([1.5, 2.5, 3.0, 3.5, 4.5])
        result = PredictabilityScore.compute(actual, predicted)
        assert 0.0 < result < 1.0

    def test_empty_input_returns_zero(self):
        """空输入返回 0."""
        result = PredictabilityScore.compute(
            actual=np.array([]), predicted=np.array([])
        )
        assert result == 0.0


class TestLatencyPredictor:
    """TFT 延迟预测器测试."""

    @pytest.fixture
    def sample_features(self) -> pd.DataFrame:
        """生成模拟特征数据（含潮汐模式）."""
        np.random.seed(42)
        n = 200
        hours = np.tile(np.arange(24), (n // 24) + 1)[:n]
        # 潮汐模式：白天高延迟(8-18点~500ms)，晚上低延迟(~200ms)
        y = np.where((hours >= 8) & (hours < 18), 500, 200).astype(float)
        y += np.random.normal(0, 30, n)

        df = pd.DataFrame({
            "y": y,
            "hour_of_day": hours,
            "day_of_week": hours % 7,
            "is_weekend": (hours % 7 >= 5).astype(int),
            "rolling_mean_6": pd.Series(y).rolling(6, min_periods=1).mean(),
            "rolling_std_6": pd.Series(y).rolling(6, min_periods=1).std().fillna(0.0),
            "lag_1": pd.Series(y).shift(1).fillna(y[0]),
            "lag_2": pd.Series(y).shift(2).fillna(y[0]),
            "lag_12": pd.Series(y).shift(12).fillna(y[0]),
        })
        df["ds"] = pd.date_range(
            "2026-07-30", periods=n, freq="30min", tz="UTC"
        )
        df["unique_id"] = "gpt-4o"
        return df

    def test_create_predictor(self):
        """创建预测器实例."""
        predictor = LatencyPredictor(horizon=6, lookback=24)
        assert predictor.horizon == 6
        assert predictor.lookback == 24
        assert not predictor.is_trained

    def test_default_horizon_lookback(self):
        """默认 horizon=6, lookback=48."""
        p = LatencyPredictor()
        assert p.horizon == 6
        assert p.lookback == 48

    def test_train_updates_trained_flag(self, sample_features):
        """训练后 is_trained 为 True."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        assert predictor.is_trained

    def test_predict_returns_quantiles(self, sample_features):
        """预测返回分位数字典."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        result = predictor.predict(sample_features)

        assert isinstance(result, dict)
        for q in ["p10", "p25", "p50", "p75", "p90"]:
            assert q in result
            assert isinstance(result[q], float)

    def test_predict_quantiles_monotonic(self, sample_features):
        """分位数单调递增: p10 <= p25 <= p50 <= p75 <= p90."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        result = predictor.predict(sample_features)

        assert result["p10"] <= result["p25"] <= result["p50"] <= result["p75"] <= result["p90"]

    def test_predict_without_train_raises(self):
        """未训练就预测应抛出异常."""
        predictor = LatencyPredictor()
        df = pd.DataFrame({"y": [100.0], "unique_id": ["test"], "ds": pd.Timestamp.now(tz="UTC")})
        with pytest.raises(RuntimeError, match="not trained"):
            predictor.predict(df)

    def test_compute_predictability(self, sample_features):
        """计算可预测性得分."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        score = predictor.compute_predictability(sample_features)
        assert 0.0 <= score <= 1.0

    def test_save_and_load(self, temp_dir, sample_features):
        """模型保存后重新加载."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        predict_before = predictor.predict(sample_features)

        path = temp_dir / "model.pkl"
        predictor.save(path)

        loaded = LatencyPredictor.load(path)
        assert loaded.is_trained
        predict_after = loaded.predict(sample_features)
        assert predict_after["p50"] == pytest.approx(predict_before["p50"])
