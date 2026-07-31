from __future__ import annotations

import pytest

from src.config.models import LatencyRecord
from src.prediction.features import FeatureExtractor


class TestFeatureExtractor:
    """特征提取器测试."""

    @pytest.fixture
    def sample_records(self) -> list[LatencyRecord]:
        """生成 48 条模拟延迟记录（每 30 分钟一条，含潮汐模式）."""
        records: list[LatencyRecord] = []
        for i in range(48):
            hour = i // 2  # 每半小时
            # 模拟潮汐模式: 白天 (8-18) 延迟高，晚上低
            base = 500.0 if 8 <= hour < 18 else 200.0
            latency = base + (i % 5) * 20.0  # 加一点噪声
            records.append(
                LatencyRecord(
                    provider="openai",
                    model="gpt-4o",
                    latency_ms=latency,
                    timestamp=f"2026-07-30T{hour:02d}:{(i%2)*30:02d}:00Z",
                )
            )
        return records

    def test_extract_features_shape(self, sample_records):
        """特征提取输出正确的行数."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        # 每条记录对应一行特征
        assert len(df) == 48

    def test_required_columns_present(self, sample_records):
        """包含所有必需的特征列."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        required = [
            "y",  # 目标：延迟值
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "rolling_mean_6",
            "rolling_std_6",
            "lag_1",
            "lag_2",
            "lag_12",  # 约 6 小时前
        ]
        for col in required:
            assert col in df.columns, f"缺失列: {col}"

    def test_hour_of_day_feature(self, sample_records):
        """hour_of_day 特征在 0-23 范围内."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        assert df["hour_of_day"].between(0, 23).all()

    def test_is_weekend_feature(self, sample_records):
        """is_weekend 是 0 或 1."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        assert set(df["is_weekend"].unique()).issubset({0, 1})

    def test_lag_features_exist(self, sample_records):
        """lag 特征存在且部分为 NaN（前几行无法计算 lag）."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        # lag_1 的第一行是 NaN
        assert df["lag_1"].iloc[0] != df["lag_1"].iloc[0]  # NaN != NaN is True

    def test_empty_records(self):
        """空输入返回空 DataFrame."""
        extractor = FeatureExtractor()
        df = extractor.extract([])
        assert len(df) == 0

    def test_single_record(self):
        """单条记录仍有特征输出（lag/rolling 为 NaN）."""
        records = [LatencyRecord(provider="o", model="m", latency_ms=100.0)]
        extractor = FeatureExtractor()
        df = extractor.extract(records)
        assert len(df) == 1
