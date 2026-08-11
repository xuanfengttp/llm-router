from __future__ import annotations

import pytest

from src.config.models import LatencyRecord
from src.prediction.data_gate import DataGate


def _records(n: int, provider: str = "openai", model: str = "gpt-4o") -> list[LatencyRecord]:
    """生成 n 条延迟记录."""
    return [
        LatencyRecord(provider=provider, model=model, latency_ms=100.0 + i)
        for i in range(n)
    ]


class TestDataGate:
    """数据门槛检查测试."""

    def test_check_below_threshold(self):
        """99 点 → 不达标."""
        gate = DataGate(min_data_points=100)
        assert gate.check(_records(99)) is False

    def test_check_at_threshold(self):
        """100 点 → 刚好达标."""
        gate = DataGate(min_data_points=100)
        assert gate.check(_records(100)) is True

    def test_check_above_threshold(self):
        """101 点 → 达标."""
        gate = DataGate(min_data_points=100)
        assert gate.check(_records(101)) is True

    def test_check_empty(self):
        """空序列 → 不达标."""
        gate = DataGate(min_data_points=100)
        assert gate.check([]) is False

    def test_custom_threshold(self):
        """自定义阈值生效."""
        gate = DataGate(min_data_points=10)
        assert gate.check(_records(10)) is True
        assert gate.check(_records(9)) is False

    def test_check_multi(self):
        """批量检查返回每序列布尔值，结构保持."""
        gate = DataGate(min_data_points=100)
        data = {
            "openai": {
                "gpt-4o": _records(150),
                "gpt-3.5": _records(50),
            },
            "anthropic": {
                "claude-3": _records(100),
            },
        }
        result = gate.check_multi(data)
        assert result == {
            "openai": {"gpt-4o": True, "gpt-3.5": False},
            "anthropic": {"claude-3": True},
        }

    def test_check_multi_empty(self):
        """空字典 → 空结果."""
        gate = DataGate(min_data_points=100)
        assert gate.check_multi({}) == {}
