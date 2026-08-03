from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.controller.dispatcher import DispatchEngine, TimeWindow
from src.controller.task_model import AgentTask
from src.routing.engine import RouteEngine
from src.routing.strategy import BaselineStrategy
from src.routing.task_profile import DEFAULT_TASK_PROFILES
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestTimeWindow:
    """Time window tests."""

    def test_default_weekday_night_is_auto(self):
        tw = TimeWindow()
        # Monday 2:00 AM = weekday 0, hour 2
        dt = datetime(2026, 8, 3, 2, 0)  # Monday
        assert tw.is_auto_mode(dt) is True

    def test_default_weekday_day_is_not_auto(self):
        tw = TimeWindow()
        dt = datetime(2026, 8, 3, 14, 0)  # Monday 2pm
        assert tw.is_auto_mode(dt) is False

    def test_default_weekend_all_day_is_auto(self):
        tw = TimeWindow()
        dt_sat = datetime(2026, 8, 1, 14, 0)  # Saturday 2pm
        dt_sun = datetime(2026, 8, 2, 9, 0)   # Sunday 9am
        assert tw.is_auto_mode(dt_sat) is True
        assert tw.is_auto_mode(dt_sun) is True

    def test_allow_weekday_day_enabled(self):
        tw = TimeWindow(allow_weekday_day=True)
        dt = datetime(2026, 8, 3, 14, 0)  # Monday 2pm
        assert tw.is_auto_mode(dt) is True

    def test_current_time_defaults_to_now(self):
        tw = TimeWindow()
        result = tw.is_auto_mode()
        assert isinstance(result, bool)


class TestDispatchEngine:
    """Dispatch decision engine tests."""

    @pytest.fixture
    def candidates(self):
        return [
            ModelProfile(
                provider="openai", model="gpt-4o-mini",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.00015, cost_output_1k=0.0006,
                benchmark=BenchmarkData(arena_elo=1150),
                local_metrics=LocalMetrics(latency_p50_ms=100, predictability=1.0),
            ),
            ModelProfile(
                provider="openai", model="gpt-4o",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.0025, cost_output_1k=0.0100,
                benchmark=BenchmarkData(arena_elo=1287),
                local_metrics=LocalMetrics(latency_p50_ms=320, predictability=1.0),
            ),
        ]

    @pytest.fixture
    def engine(self, candidates):
        route = RouteEngine(strategy=BaselineStrategy())
        return DispatchEngine(
            route_engine=route,
            candidates=candidates,
        )

    def test_create_engine(self, engine):
        assert engine.latency_redline_ms == 5000.0
        assert engine.predictability_threshold == 0.3

    async def test_check_passes_within_limits(self, engine):
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o-mini")
        ok, reason = await engine.check(task)
        assert ok is True, f"Expected pass but got: {reason}"
        assert reason == ""

    async def test_check_fails_latency_too_high(self):
        route = RouteEngine(strategy=BaselineStrategy())
        engine = DispatchEngine(
            route_engine=route,
            candidates=[
                ModelProfile(
                    provider="p", model="slow", deployment="cloud",
                    context_window=64000, cost_input_1k=0.001, cost_output_1k=0.005,
                    benchmark=BenchmarkData(arena_elo=1000),
                    local_metrics=LocalMetrics(latency_p50_ms=6000),
                ),
            ],
            latency_redline_ms=5000,
        )
        task = AgentTask(task_id="t", prompt="p", target_model="slow")
        ok, reason = await engine.check(task)
        assert ok is False
        assert "latency" in reason.lower()

    async def test_dispatch_success(self, engine):
        task = AgentTask(task_id="t", prompt="code review", target_model="")
        result = await engine.dispatch(task, {})
        assert result is not None
        assert result.profile is not None
        assert result.score > 0

    async def test_dispatch_all_filtered_returns_none(self):
        route = RouteEngine(strategy=BaselineStrategy())
        engine = DispatchEngine(
            route_engine=route,
            candidates=[
                ModelProfile(
                    provider="p", model="slow", deployment="cloud",
                    context_window=64000, cost_input_1k=0.001, cost_output_1k=0.005,
                    benchmark=BenchmarkData(arena_elo=1000),
                    local_metrics=LocalMetrics(latency_p50_ms=6000),
                ),
            ],
            latency_redline_ms=100,
        )
        task = AgentTask(task_id="t", prompt="p", target_model="")
        result = await engine.dispatch(task, {})
        assert result is None
