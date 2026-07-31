from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.config.models import LatencyRecord
from src.prediction.engine import LatencyPrediction, PredictionEngine


class TestLatencyPrediction:
    """预测结果数据类测试."""

    def test_create_prediction(self):
        pred = LatencyPrediction(
            provider="openai",
            model="gpt-4o",
            quantiles={"p10": 200.0, "p25": 280.0, "p50": 350.0, "p75": 450.0, "p90": 550.0},
            predictability=0.82,
            data_points_used=200,
        )
        assert pred.provider == "openai"
        assert pred.model == "gpt-4o"
        assert pred.p50 == 350.0
        assert pred.predictability == 0.82
        assert pred.quantiles is not None
        assert pred.data_points_used == 200


class TestPredictionEngine:
    """预测引擎测试."""

    @pytest.fixture
    def sample_records(self) -> list[LatencyRecord]:
        """生成足够多的训练数据."""
        records: list[LatencyRecord] = []
        for i in range(300):
            hour = i % 24
            base = 500.0 if 8 <= hour < 18 else 200.0
            latency = base + (i % 7) * 15.0
            timestamp = datetime(2026, 7, 30, 0, 0, 0, tzinfo=timezone.utc)
            timestamp = timestamp.replace(
                hour=hour, minute=(i % 4) * 15
            )
            records.append(
                LatencyRecord(
                    provider="openai",
                    model="gpt-4o",
                    latency_ms=latency,
                    timestamp=timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
            )
        records.sort(key=lambda r: r.timestamp)
        return records

    def test_create_engine(self):
        """创建预测引擎."""
        engine = PredictionEngine(horizon=3, lookback=24, min_data_points=50)
        assert engine.min_data_points == 50

    def test_predict_for_model(self, sample_records):
        """对单个模型执行预测."""
        engine = PredictionEngine(horizon=3, lookback=24, min_data_points=50)
        result = engine.predict_for_model("openai", "gpt-4o", sample_records)

        assert result is not None
        assert result.provider == "openai"
        assert result.model == "gpt-4o"
        assert result.p50 > 0
        assert 0.0 <= result.predictability <= 1.0

    def test_insufficient_data_returns_none(self):
        """数据不足返回 None."""
        engine = PredictionEngine(min_data_points=1000)
        few_records = [
            LatencyRecord(provider="o", model="m", latency_ms=100.0)
            for _ in range(5)
        ]
        result = engine.predict_for_model("o", "m", few_records)
        assert result is None

    def test_predict_providers(self, sample_records):
        """批量 Provider 预测."""
        engine = PredictionEngine(horizon=3, lookback=24, min_data_points=50)
        results = engine.predict_all(
            {"openai": {"gpt-4o": sample_records}}
        )
        assert "openai" in results
        assert "gpt-4o" in results["openai"]
