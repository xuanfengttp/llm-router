from __future__ import annotations

from dataclasses import dataclass

from src.config.models import LatencyRecord
from src.prediction.features import FeatureExtractor
from src.prediction.model import LatencyPredictor


@dataclass(frozen=True, slots=True)
class LatencyPrediction:
    """单次延迟预测结果."""

    provider: str
    model: str
    quantiles: dict[str, float]
    predictability: float
    data_points_used: int

    @property
    def p50(self) -> float:
        return self.quantiles["p50"]

    @property
    def p90(self) -> float:
        return self.quantiles["p90"]


class PredictionEngine:
    """预测引擎：orchestrate 特征提取 -> TFT 训练 -> 预测 -> 评分.

    对每个模型独立建模，因为不同模型有不同的延迟特性。

    用法:
        engine = PredictionEngine(horizon=6, lookback=48)
        records = await store.load_latency_series("openai", "gpt-4o", limit=500)
        prediction = engine.predict_for_model("openai", "gpt-4o", records)
        if prediction:
            print(f"p50 预测延迟: {prediction.p50:.1f}ms")
            print(f"可预测性: {prediction.predictability:.2f}")
    """

    def __init__(
        self,
        horizon: int = 6,
        lookback: int = 48,
        min_data_points: int = 100,
    ) -> None:
        self.horizon = horizon
        self.lookback = lookback
        self.min_data_points = min_data_points
        self._extractor = FeatureExtractor()
        self._predictors: dict[tuple[str, str], LatencyPredictor] = {}

    def predict_for_model(
        self,
        provider: str,
        model: str,
        records: list[LatencyRecord],
    ) -> LatencyPrediction | None:
        """对指定模型执行延迟预测.

        Returns:
            LatencyPrediction 或 None（数据不足时）
        """
        if len(records) < self.min_data_points:
            return None

        key = (provider, model)

        # 1. 特征工程
        df = self._extractor.extract(records)
        df = df.rename(columns={"timestamp": "ds"})
        df["unique_id"] = f"{provider}/{model}"
        df = df.dropna(subset=["lag_1", "lag_2", "lag_12"])

        if len(df) < self.min_data_points:
            return None

        # 2. 训练 TFT
        predictor = LatencyPredictor(
            horizon=self.horizon, lookback=min(self.lookback, len(df) // 4)
        )
        predictor.train(df)

        # 3. 预测
        quantiles = predictor.predict(df)

        # 4. 可预测性评分
        predictability = predictor.compute_predictability(df)

        self._predictors[key] = predictor

        return LatencyPrediction(
            provider=provider,
            model=model,
            quantiles=quantiles,
            predictability=predictability,
            data_points_used=len(df),
        )

    def predict_all(
        self,
        data: dict[str, dict[str, list[LatencyRecord]]],
    ) -> dict[str, dict[str, LatencyPrediction | None]]:
        """对所有 Provider 的所有模型执行预测."""
        results: dict[str, dict[str, LatencyPrediction | None]] = {}
        for provider, models in data.items():
            results[provider] = {}
            for model_name, records in models.items():
                results[provider][model_name] = self.predict_for_model(
                    provider, model_name, records
                )
        return results
