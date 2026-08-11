from __future__ import annotations

from src.config.models import LatencyRecord


class DataGate:
    """数据门槛检查器：单序列或批量判断数据量是否满足预测阈值.

    用法:
        gate = DataGate(min_data_points=100)
        if gate.check(records):
            engine.predict_for_model(provider, model, records)
    """

    def __init__(self, min_data_points: int = 100) -> None:
        self.min_data_points = min_data_points

    def check(self, records: list[LatencyRecord]) -> bool:
        """单序列是否满足预测阈值."""
        return len(records) >= self.min_data_points

    def check_multi(
        self,
        data: dict[str, dict[str, list[LatencyRecord]]],
    ) -> dict[str, dict[str, bool]]:
        """批量检查，返回与入参同结构的布尔值映射."""
        return {
            provider: {
                model_name: self.check(records)
                for model_name, records in models.items()
            }
            for provider, models in data.items()
        }
