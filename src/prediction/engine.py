from __future__ import annotations

from dataclasses import dataclass

from src.config.models import LatencyRecord
from src.prediction.data_gate import DataGate
from src.prediction.features import FeatureExtractor
from src.prediction.model import LatencyPredictor
from src.prediction.rl_corrector import RLCorrector
from src.prediction.short_term import ShortTermPredictor
from src.prediction.store import ModelStore

# 有序分位数键，用于 RL corrector 的 list 排序
_QUANTILE_KEYS = ["p10", "p25", "p50", "p75", "p90"]


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
    """预测引擎：串联 DataGate → ShortTermPredictor → LongTermPredictor → RLCorrector → ModelStore.

    对每个模型独立建模，因为不同模型有不同的延迟特性。

    数据路径:
        predict_for_model(provider, model, records):
          if gate.check(records) is False → return None
          short_q = short.predict(records)  # 始终可用
          如果有长期模型 → 用长期预测作为 primary
          否则 → 短期首步作为 primary
          corrected = rl.correct(provider, model, list(primary.values()))
          → LatencyPrediction

    用法:
        engine = PredictionEngine(horizon=6, lookback=48)
        records = [LatencyRecord(...), ...]
        prediction = engine.predict_for_model("openai", "gpt-4o", records)
        if prediction:
            print(f"p50 预测延迟: {prediction.p50:.1f}ms")
            print(f"可预测性: {prediction.predictability:.2f}")
    """

    def __init__(
        self,
        horizon: int = 2,
        lookback: int = 96,
        min_data_points: int = 100,
        enable_long_term: bool = True,
        model_dir: str | None = None,
    ) -> None:
        self.horizon = horizon
        self.lookback = lookback
        self.min_data_points = min_data_points
        self._gate = DataGate(min_data_points)
        self._short = ShortTermPredictor(horizon=horizon)
        self._extractor = FeatureExtractor()
        self._rl = RLCorrector()
        self._store = ModelStore(
            base_dir=None if model_dir is None else __import__("pathlib").Path(model_dir)
        )

        self._long: LatencyPredictor | None = None
        if enable_long_term:
            try:
                import neuralforecast  # noqa: F401
            except ImportError:
                self._long = None
            else:
                existing = self._store.load()
                if existing is not None:
                    self._long = existing
                else:
                    self._long = LatencyPredictor(horizon=48, lookback=lookback)

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
        # 0. 数据门槛
        if not self._gate.check(records):
            return None

        # 1. 短期预测（始终可用）
        short_q = self._short.predict(records)
        if short_q is None:
            return None
        # short_q = {"p50": [v1, v2], "p25": [...], ...}，取首步

        # 2. 长期预测（如果有模型）
        long_q: dict[str, float] | None = None
        if self._long is not None and self._long.is_trained:
            try:
                df = self._extractor.extract(records)
                df = df.rename(columns={"timestamp": "ds"})
                df["unique_id"] = f"{provider}/{model}"
                df = df.dropna(subset=["lag_1", "lag_2", "lag_12"])
                if len(df) >= self.min_data_points:
                    long_q = self._long.predict(df)
            except Exception:
                long_q = None

        # 3. 选择 primary 分位数
        if long_q is not None:
            primary_q = long_q
            predictability = self._long.compute_predictability(
                self._extractor.extract(records)
                .rename(columns={"timestamp": "ds"})
                .assign(unique_id=f"{provider}/{model}")
                .dropna(subset=["lag_1", "lag_2", "lag_12"])
            )
        else:
            primary_q = {k: v[0] for k, v in short_q.items()}  # 取首步
            predictability = self._short.compute_predictability(records)

        # 4. RL 修正：将有序分位数值传入 corrector
        raw_values = [primary_q[k] for k in _QUANTILE_KEYS]
        corrected_values = self._rl.correct(provider, model, raw_values)
        corrected_q = dict(zip(_QUANTILE_KEYS, corrected_values))

        return LatencyPrediction(
            provider=provider,
            model=model,
            quantiles=corrected_q,
            predictability=predictability,
            data_points_used=len(records),
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

    def update_from_observation(
        self,
        provider: str,
        model: str,
        actual_latency: float,
        predicted_latency: float,
    ) -> None:
        """收到实测延迟后，更新 RL 修正器.

        Args:
            provider: Provider 名称
            model: 模型名称
            actual_latency: 实测延迟 (ms)
            predicted_latency: 发送请求时预测的延迟 (ms)
        """
        self._rl.feed(provider, model, actual_latency, predicted_latency)

    def train_long_term(self, multi_series_df: "pd.DataFrame") -> None:
        """多序列训练 TFT + 持久化.

        Args:
            multi_series_df: 包含 'unique_id', 'ds', 'y' 及特征列的多序列数据集
        """
        if self._long is None:
            return
        self._long.train_multi(multi_series_df)
        self._store.save(self._long)
