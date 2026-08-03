from __future__ import annotations

import pytest


class TestSettingsData:
    """Test settings page data transformation functions."""

    def test_strategy_options(self):
        """Strategy list contains all 5 options."""
        from src.gui.pages.settings_page import STRATEGY_OPTIONS

        ids = [s["id"] for s in STRATEGY_OPTIONS]
        assert "baseline" in ids
        assert "cost_first" in ids
        assert "quality_first" in ids
        assert "latency_aware" in ids
        assert "task_specific" in ids
        assert len(STRATEGY_OPTIONS) == 5

    def test_strategy_options_have_labels(self):
        """Each strategy option has id, label, description."""
        from src.gui.pages.settings_page import STRATEGY_OPTIONS

        for opt in STRATEGY_OPTIONS:
            assert "id" in opt
            assert "label" in opt
            assert "description" in opt

    def test_time_window_to_dict(self):
        """Time window config to dict."""
        from src.gui.pages.settings_page import time_window_to_dict

        tw = type("TimeWindow", (), {
            "weekday_night_hours": (22, 6),
            "weekend_all_day": True,
        })()
        d = time_window_to_dict(tw)
        assert d["weekday_night_start"] == 22
        assert d["weekday_night_end"] == 6
        assert d["weekend_all_day"] is True

    def test_setting_defaults(self):
        """Default setting values are valid."""
        from src.gui.pages.settings_page import DEFAULT_SETTINGS

        assert 1000 <= DEFAULT_SETTINGS["latency_redline_ms"] <= 10000
        assert 0.0 <= DEFAULT_SETTINGS["predictability_threshold"] <= 1.0
        assert DEFAULT_SETTINGS["strategy"] in {"baseline", "cost_first", "quality_first", "latency_aware", "task_specific"}
