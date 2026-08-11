from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.prediction.model import LatencyPredictor
from src.prediction.store import ModelStore


class TestModelStore:
    """ModelStore 持久化模块测试."""

    @pytest.fixture
    def sample_features(self) -> pd.DataFrame:
        """生成模拟特征数据（含潮汐模式）."""
        np.random.seed(42)
        n = 200
        hours = np.tile(np.arange(24), (n // 24) + 1)[:n]
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

    @pytest.fixture
    def trained_predictor(self, sample_features) -> LatencyPredictor:
        """返回一个已训练的 LatencyPredictor 实例."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        return predictor

    # -- 测试 1: save + load roundtrip -- #

    def test_save_and_load_roundtrip(self, tmp_path, trained_predictor):
        """保存后加载得到完整等价对象，horizon/lookback 一致."""
        store = ModelStore(base_dir=tmp_path)
        store.save(trained_predictor)

        loaded = store.load()
        assert loaded is not None
        assert isinstance(loaded, LatencyPredictor)
        assert loaded.horizon == trained_predictor.horizon
        assert loaded.lookback == trained_predictor.lookback
        assert loaded.is_trained

    # -- 测试 2: load 不存在的文件返回 None -- #

    def test_load_nonexistent_returns_none(self, tmp_path):
        """目录下无模型文件时 load() 返回 None，不抛异常."""
        store = ModelStore(base_dir=tmp_path)
        result = store.load()
        assert result is None

    def test_load_nonexistent_dir_returns_none(self, tmp_path):
        """base_dir 本身不存在时 load() 返回 None，不抛异常."""
        store = ModelStore(base_dir=tmp_path / "nonexistent_subdir")
        result = store.load()
        assert result is None

    # -- 测试 3: save 创建文件 -- #

    def test_save_creates_file(self, tmp_path, trained_predictor):
        """save() 后文件物理存在于指定路径."""
        store = ModelStore(base_dir=tmp_path)
        store.save(trained_predictor)

        expected_path = tmp_path / "data" / "models" / "long_term_predictor.pkl"
        assert expected_path.exists()
        assert expected_path.is_file()

    # -- 测试 4: 损坏文件返回 None -- #

    def test_corrupt_file_returns_none(self, tmp_path):
        """写入非 pickle 内容后 load() 返回 None."""
        store = ModelStore(base_dir=tmp_path)
        # Ensure the directory and file exist
        file_path = store._file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("not a pickle", encoding="utf-8")

        result = store.load()
        assert result is None

    def test_empty_file_returns_none(self, tmp_path):
        """空模型文件 load() 返回 None."""
        store = ModelStore(base_dir=tmp_path)
        file_path = store._file_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("", encoding="utf-8")

        result = store.load()
        assert result is None

    # -- 测试 5: 自定义文件名 -- #

    def test_custom_filename(self, tmp_path, trained_predictor):
        """可以指定自定义文件名."""
        store = ModelStore(base_dir=tmp_path, filename="custom_model.pkl")
        store.save(trained_predictor)

        expected_path = tmp_path / "custom_model.pkl"
        assert expected_path.exists()
        loaded = store.load()
        assert loaded is not None
        assert loaded.horizon == trained_predictor.horizon

    # -- 测试 6: 默认路径为 ~/.llm_router -- #

    def test_default_path(self):
        """不传 base_dir 时使用默认路径."""
        store = ModelStore()
        from pathlib import Path
        expected = Path.home() / ".llm_router" / "data" / "models" / "long_term_predictor.pkl"
        assert store._file_path == expected
