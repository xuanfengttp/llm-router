from __future__ import annotations

import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd


class PredictabilityScore:
    """可预测性评分：1 - (残差方差 / 总方差).

    得分 0 = 完全随机不可预测
    得分 1 = 完美可预测
    """

    @staticmethod
    def compute(actual: np.ndarray, predicted: np.ndarray) -> float:
        if len(actual) == 0 or len(predicted) == 0:
            return 0.0
        residual_var = float(np.var(actual - predicted))
        total_var = float(np.var(actual))
        if total_var == 0:
            return 1.0  # 常数信号，完美可预测
        score = 1.0 - (residual_var / total_var)
        return float(max(0.0, min(1.0, score)))


class LatencyPredictor:
    """TFT 延迟预测器.

    封装 NeuralForecast TFT 模型，提供训练、预测、可预测性评分、
    模型持久化等能力。

    用法:
        predictor = LatencyPredictor(horizon=6, lookback=48)
        df = feature_extractor.extract(records)
        df["unique_id"] = "gpt-4o"
        predictor.train(df)
        prediction = predictor.predict(df)
        print(f"p50 预测: {prediction['p50']:.1f}ms")
        print(f"可预测性: {predictor.compute_predictability(df):.2f}")
    """

    def __init__(self, horizon: int = 6, lookback: int = 48) -> None:
        self.horizon = horizon
        self.lookback = lookback
        self._model: object | None = None
        self._trained = False

    @property
    def is_trained(self) -> bool:
        return self._trained

    def train(self, df: pd.DataFrame) -> None:
        """训练 TFT 模型.

        Args:
            df: 包含 'unique_id', 'ds', 'y' 及特征列的数据集
        """
        from neuralforecast import NeuralForecast
        from neuralforecast.losses.pytorch import MQLoss
        from neuralforecast.models import TFT

        # 静默 lightning 的进度条和警告
        warnings.filterwarnings("ignore")

        n_rows = len(df)
        # TFT 需要合理的数据量，自适应调整 horizon
        if n_rows < self.lookback + self.horizon:
            effective_horizon = max(1, (n_rows - self.lookback) // 2)
        else:
            effective_horizon = self.horizon

        if effective_horizon < 1:
            effective_horizon = 1

        # 多分位数 loss
        loss = MQLoss(quantiles=[0.1, 0.25, 0.5, 0.75, 0.9])

        model = TFT(
            h=effective_horizon,
            input_size=self.lookback,
            hidden_size=32,
            n_head=4,
            dropout=0.1,
            loss=loss,
            learning_rate=1e-3,
            max_steps=100,
            val_check_steps=10,
            early_stop_patience_steps=5,
            scaler_type="standard",
        )

        # val_size 必须 > 0，否则 early stopping 会报错
        val_size = max(1, int(n_rows * 0.1))

        self._model = NeuralForecast(models=[model], freq="30min")
        self._model.fit(df=df, val_size=val_size)
        self._trained = True

    def train_multi(self, df: pd.DataFrame) -> None:
        """训练 TFT 模型以处理多个 provider/model 的延迟序列.

        与 train() 的区别:
        - df 可包含多个 unique_id 值（如 "openai/gpt-4o", "anthropic/claude-3"）
        - unique_id 仅作为序列分隔符传给 NeuralForecast，不作为特征
        - 使用更大 hidden_size 和更长训练步数以捕获跨序列的通用潮汐模式

        Args:
            df: 包含 'unique_id', 'ds', 'y' 及特征列的多序列数据集
        """
        from neuralforecast import NeuralForecast
        from neuralforecast.losses.pytorch import MQLoss
        from neuralforecast.models import TFT

        warnings.filterwarnings("ignore")

        n_rows = len(df)
        if n_rows < self.lookback + self.horizon:
            effective_horizon = max(1, (n_rows - self.lookback) // 2)
        else:
            effective_horizon = self.horizon

        if effective_horizon < 1:
            effective_horizon = 1

        loss = MQLoss(quantiles=[0.1, 0.25, 0.5, 0.75, 0.9])

        model = TFT(
            h=effective_horizon,
            input_size=self.lookback,
            hidden_size=64,          # 更大的隐藏层以捕获跨序列模式
            n_head=4,
            dropout=0.1,
            loss=loss,
            learning_rate=1e-3,
            max_steps=200,           # 更长训练以学习通用潮汐模式
            val_check_steps=10,
            early_stop_patience_steps=5,
            scaler_type="standard",
        )

        val_size = max(1, int(n_rows * 0.1))

        self._model = NeuralForecast(models=[model], freq="30min")
        self._model.fit(df=df, val_size=val_size)
        self._trained = True

    def predict(self, df: pd.DataFrame) -> dict[str, float]:
        """预测下一个 horizon 步的延迟分位数.

        Returns:
            {"p10": ..., "p25": ..., "p50": ..., "p75": ..., "p90": ...}
        """
        if not self._trained or self._model is None:
            raise RuntimeError("Model is not trained, please call train() first")

        forecast = self._model.predict(df)

        # NeuralForecast 1.7.0 MQLoss 分位数输出列名：
        #  quantiles_to_outputs([0.1, 0.25, 0.5, 0.75, 0.9]) 得到：
        #  names: ['-lo-80.0', '-lo-50.0', '-median', '-hi-50.0', '-hi-80.0']
        #  模型名前缀: TFT
        #  完整列名: TFT-lo-80.0, TFT-lo-50.0, TFT-median, TFT-hi-50.0, TFT-hi-80.0
        try:
            p10 = float(forecast["TFT-lo-80.0"].iloc[0])
            p25 = float(forecast["TFT-lo-50.0"].iloc[0])
            p50 = float(forecast["TFT-median"].iloc[0])
            p75 = float(forecast["TFT-hi-50.0"].iloc[0])
            p90 = float(forecast["TFT-hi-80.0"].iloc[0])
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"预测结果解析失败: {e}") from e

        # 确保分位数单调：TFT 在小数据上可能输出非单调序列
        values = [p10, p25, p50, p75, p90]
        values.sort()
        return {
            "p10": values[0],
            "p25": values[1],
            "p50": values[2],
            "p75": values[3],
            "p90": values[4],
        }

    def compute_predictability(self, df: pd.DataFrame) -> float:
        """计算可预测性得分 (0-1).

        使用训练数据的中位数预测值 vs 实际 y 值。
        """
        if not self._trained or self._model is None:
            raise RuntimeError("Model is not trained, please call train() first")

        forecast = self._model.predict(df)
        try:
            predicted = forecast["TFT-median"].values
            # 预测输出长度可能小于输入
            actual = df["y"].values[-len(predicted):]
            return PredictabilityScore.compute(actual, predicted)
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"可预测性计算失败: {e}") from e

    def save(self, path: Path) -> None:
        """保存模型到文件."""
        if self._model is None:
            raise RuntimeError("无模型可保存")
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "horizon": self.horizon,
                    "lookback": self.lookback,
                    "model": self._model,
                },
                f,
            )

    @classmethod
    def load(cls, path: Path) -> LatencyPredictor:
        """从文件加载模型."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        predictor = cls(
            horizon=data["horizon"],
            lookback=data["lookback"],
        )
        predictor._model = data["model"]
        predictor._trained = True
        return predictor
