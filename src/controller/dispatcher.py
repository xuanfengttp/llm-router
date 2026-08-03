from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.controller.task_model import AgentTask
from src.prediction.engine import LatencyPrediction
from src.routing.engine import RouteEngine, RouteResult
from src.routing.task_profile import DEFAULT_TASK_PROFILES
from src.scoring.profile import ModelProfile


@dataclass(frozen=True, slots=True)
class TimeWindow:
    allow_weekday_night: bool = True
    weekday_night_start: str = "21:00"
    weekday_night_end: str = "09:00"
    allow_weekend_all_day: bool = True
    allow_weekday_day: bool = False

    def is_auto_mode(self, dt: datetime | None = None) -> bool:
        if dt is None:
            dt = datetime.now(timezone.utc)
        weekday = dt.weekday()
        is_weekend = weekday >= 5

        if is_weekend:
            return self.allow_weekend_all_day

        hour = dt.hour
        night_start = int(self.weekday_night_start.split(":")[0])
        night_end = int(self.weekday_night_end.split(":")[0])

        is_night = hour >= night_start or hour < night_end
        if is_night:
            return self.allow_weekday_night

        return self.allow_weekday_day


class DispatchEngine:
    def __init__(
        self,
        route_engine: RouteEngine,
        candidates: list[ModelProfile],
        latency_redline_ms: float = 5000.0,
        predictability_threshold: float = 0.3,
        time_window: TimeWindow | None = None,
    ) -> None:
        self.route_engine = route_engine
        self.candidates = candidates
        self.latency_redline_ms = latency_redline_ms
        self.predictability_threshold = predictability_threshold
        self.time_window = time_window or TimeWindow()

    async def check(self, task: AgentTask) -> tuple[bool, str]:
        # 1. time window check
        if not self.time_window.is_auto_mode():
            return False, "current time is not within auto mode time window"

        # 2. candidate model existence check
        matching = [c for c in self.candidates if c.model == task.target_model or not task.target_model]
        if not matching:
            matching = self.candidates

        if not matching:
            return False, "no available candidate models"

        # 3. latency redline check
        for c in matching:
            if c.local_metrics.latency_p50_ms > self.latency_redline_ms:
                return False, f"model {c.model} p50 latency {c.local_metrics.latency_p50_ms:.0f}ms exceeds redline {self.latency_redline_ms:.0f}ms"

        # 4. predictability check
        for c in matching:
            if c.local_metrics.predictability < self.predictability_threshold:
                return False, f"model {c.model} predictability {c.local_metrics.predictability:.2f} below threshold {self.predictability_threshold}"

        return True, ""

    async def dispatch(
        self,
        task: AgentTask,
        predictions: dict[str, LatencyPrediction],
    ) -> RouteResult | None:
        ok, _reason = await self.check(task)
        if not ok:
            return None

        task_profile = DEFAULT_TASK_PROFILES.get("general_chat", list(DEFAULT_TASK_PROFILES.values())[0])
        self.route_engine._predictions = predictions

        result = self.route_engine.route(task_profile, self.candidates)
        return result
