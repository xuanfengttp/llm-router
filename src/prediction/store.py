from __future__ import annotations

import pickle
from pathlib import Path

from src.prediction.model import LatencyPredictor


class ModelStore:
    """模型持久化管理器.

    封装 LatencyPredictor 的 save/load，管理文件存储路径。
    默认存储位置: ~/.llm_router/data/models/long_term_predictor.pkl
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        filename: str = "long_term_predictor.pkl",
    ) -> None:
        if base_dir is None:
            base_dir = Path.home() / ".llm_router"
        if filename == "long_term_predictor.pkl":
            base_dir = base_dir / "data" / "models"
        self._file_path = base_dir / filename

    def save(self, predictor: LatencyPredictor) -> None:
        """保存预测器到磁盘."""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        predictor.save(self._file_path)

    def load(self) -> LatencyPredictor | None:
        """加载预测器，文件不存在或损坏时返回 None."""
        if not self._file_path.exists():
            return None
        try:
            return LatencyPredictor.load(self._file_path)
        except (pickle.UnpicklingError, EOFError, TypeError, ValueError):
            return None
