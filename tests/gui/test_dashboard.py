# tests/gui/test_dashboard.py
from __future__ import annotations

import pytest


class TestDashboardData:
    """测试仪表板数据变换函数."""

    def test_latency_to_echarts_series(self):
        """延迟记录 → ECharts 系列数据."""
        from src.gui.pages.dashboard import latency_to_echarts

        records = [
            {"model": "gpt-4o", "timestamp": "2026-08-03T10:00:00", "latency_ms": 450.0},
            {"model": "gpt-4o", "timestamp": "2026-08-03T10:01:00", "latency_ms": 480.0},
            {"model": "claude-sonnet", "timestamp": "2026-08-03T10:00:00", "latency_ms": 350.0},
            {"model": "claude-sonnet", "timestamp": "2026-08-03T10:01:00", "latency_ms": 360.0},
        ]
        result = latency_to_echarts(records)
        assert "xAxis" in result
        assert "series" in result
        assert len(result["series"]) == 2  # 两条线

    def test_latency_to_echarts_empty(self):
        """空数据时返回空系列."""
        from src.gui.pages.dashboard import latency_to_echarts

        result = latency_to_echarts([])
        assert result["series"] == []
        assert result["xAxis"] == []

    def test_predictability_label(self):
        """可预测性分数 → 标签."""
        from src.gui.pages.dashboard import predictability_label

        assert predictability_label(0.9) == ("高", "green")
        assert predictability_label(0.5) == ("中", "orange")
        assert predictability_label(0.2) == ("低", "red")
        assert predictability_label(None) == ("无数据", "grey")

    def test_status_color(self):
        """Provider 状态 → 颜色."""
        from src.gui.pages.dashboard import status_color

        assert status_color("online") == "green"
        assert status_color("degraded") == "orange"
        assert status_color("offline") == "red"
        assert status_color("unknown") == "grey"
