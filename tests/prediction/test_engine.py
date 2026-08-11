from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
    """预测引擎测试 — 走短期路径（不依赖 neuralforecast）."""

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

    @pytest.fixture
    def multi_provider_data(self) -> dict[str, dict[str, list[LatencyRecord]]]:
        """多个 provider 的延迟记录."""
        data: dict[str, dict[str, list[LatencyRecord]]] = {}
        for provider in ["openai", "anthropic"]:
            data[provider] = {}
            for model_name in ["model-a", "model-b"]:
                records: list[LatencyRecord] = []
                for i in range(200):
                    base_latency = {"openai": 300.0, "anthropic": 400.0}.get(provider, 300.0)
                    latency = base_latency + (i % 5) * 10.0
                    ts = datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=30 * i)
                    records.append(
                        LatencyRecord(
                            provider=provider,
                            model=model_name,
                            latency_ms=latency,
                            timestamp=ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        )
                    )
                data[provider][model_name] = records
        return data

    def test_create_engine(self):
        """创建预测引擎."""
        engine = PredictionEngine(horizon=3, lookback=24, min_data_points=50)
        assert engine.min_data_points == 50

    def test_predict_for_model(self, sample_records):
        """对单个模型执行预测（短期路径）."""
        engine = PredictionEngine(
            horizon=3, lookback=24, min_data_points=50,
            enable_long_term=False,
        )
        result = engine.predict_for_model("openai", "gpt-4o", sample_records)

        assert result is not None
        assert result.provider == "openai"
        assert result.model == "gpt-4o"
        assert result.p50 > 0
        assert 0.0 <= result.predictability <= 1.0

    def test_insufficient_data_returns_none(self):
        """数据不足返回 None."""
        engine = PredictionEngine(min_data_points=1000, enable_long_term=False)
        few_records = [
            LatencyRecord(provider="o", model="m", latency_ms=100.0)
            for _ in range(5)
        ]
        result = engine.predict_for_model("o", "m", few_records)
        assert result is None

    def test_predict_providers(self, sample_records):
        """批量 Provider 预测."""
        engine = PredictionEngine(
            horizon=3, lookback=24, min_data_points=50,
            enable_long_term=False,
        )
        results = engine.predict_all(
            {"openai": {"gpt-4o": sample_records}}
        )
        assert "openai" in results
        assert "gpt-4o" in results["openai"]

    def test_update_from_observation_feeds_rl(self, sample_records):
        """feed 实测延迟后 RL 修正方向验证."""
        engine = PredictionEngine(
            horizon=2, lookback=24, min_data_points=50,
            enable_long_term=False,
        )

        # 第一次预测（无 RL 修正，因为无历史残差）
        result_before = engine.predict_for_model("openai", "gpt-4o", sample_records)
        assert result_before is not None

        # feed 极高实测延迟：实测 2000ms，预测 p50 ≈ base
        predicted_p50 = result_before.p50
        for _ in range(10):
            engine.update_from_observation(
                "openai", "gpt-4o",
                actual_latency=2000.0,
                predicted_latency=predicted_p50,
            )

        # 再次预测，RL 应该向上修正
        result_after = engine.predict_for_model("openai", "gpt-4o", sample_records)
        assert result_after is not None
        # 因为有正偏差残差，修正后 p50 应该 >= 修正前
        assert result_after.p50 >= result_before.p50

    def test_predict_all_multi_provider(self, multi_provider_data):
        """多 provider 都能返回结果."""
        engine = PredictionEngine(
            horizon=2, lookback=24, min_data_points=50,
            enable_long_term=False,
        )
        results = engine.predict_all(multi_provider_data)

        for provider in ["openai", "anthropic"]:
            assert provider in results
            for model_name in ["model-a", "model-b"]:
                assert model_name in results[provider]
                pred = results[provider][model_name]
                assert pred is not None, f"{provider}/{model_name} 应返回预测结果"
                assert pred.p50 > 0
                assert 0.0 <= pred.predictability <= 1.0
                assert set(pred.quantiles.keys()) == {"p10", "p25", "p50", "p75", "p90"}
