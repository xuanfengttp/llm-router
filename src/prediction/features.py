from __future__ import annotations

import pandas as pd

from src.config.models import LatencyRecord


class FeatureExtractor:
    """从延迟时序数据提取特征用于 TFT 模型.

    特征分类:
    - 时间特征: hour_of_day, day_of_week, is_weekend
    - 统计特征: rolling_mean_6, rolling_std_6 (6点窗口 ≈ 3小时，按30分钟间隔)
    - lag特征: lag_1, lag_2, lag_12

    用法:
        records = await store.load_latency_series("openai", "gpt-4o", limit=500)
        df = FeatureExtractor().extract(records)
    """

    def extract(self, records: list[LatencyRecord]) -> pd.DataFrame:
        """从延迟记录中提取特征矩阵."""
        if not records:
            return pd.DataFrame()

        # 转为 DataFrame
        df = pd.DataFrame(
            [
                {"timestamp": r.timestamp, "y": r.latency_ms}
                for r in records
            ]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)

        # ── 时间特征 ──
        df["hour_of_day"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # ── 统计特征 (滚动窗口) ──
        df["rolling_mean_6"] = df["y"].rolling(window=6, min_periods=1).mean()
        df["rolling_std_6"] = df["y"].rolling(window=6, min_periods=1).std().fillna(0.0)

        # ── Lag 特征 ──
        df["lag_1"] = df["y"].shift(1)  # 上一次
        df["lag_2"] = df["y"].shift(2)  # 前两次
        df["lag_12"] = df["y"].shift(12)  # 约 6 小时前（30分钟 * 12 = 6h）

        return df
