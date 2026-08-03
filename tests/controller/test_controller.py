from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest

from src.controller.controller import TaskController
from src.controller.dispatcher import DispatchEngine, TimeWindow
from src.controller.recovery import FailureInfo, RecoveryEngine
from src.controller.task_model import AgentTask, AgentTaskStatus
from src.controller.task_queue import TaskQueue
from src.routing.engine import RouteEngine
from src.routing.strategy import BaselineStrategy
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestTaskController:
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
        ]

    @pytest.fixture
    async def controller(self, tmp_path: Path, candidates):
        db_path = str(tmp_path / "test_tasks.db")
        queue = TaskQueue(db_path)
        await queue.init_db()

        route = RouteEngine(strategy=BaselineStrategy())
        tw = TimeWindow(allow_weekday_day=True)  # always auto
        dispatcher = DispatchEngine(route_engine=route, candidates=candidates, time_window=tw)
        recovery = RecoveryEngine(max_retries=2)

        ctrl = TaskController(
            queue=queue,
            dispatcher=dispatcher,
            recovery=recovery,
            cycle_seconds=0.1,
        )
        yield ctrl
        await ctrl.stop()
        await queue.close()

    async def test_submit_task(self, controller):
        task = await controller.submit("hello world")
        assert task.task_id
        assert task.prompt == "hello world"
        assert task.status == AgentTaskStatus.PENDING

    async def test_submit_with_target_model(self, controller):
        task = await controller.submit("code", target_model="gpt-4o-mini")
        assert task.target_model == "gpt-4o-mini"

    async def test_cancel_task(self, controller):
        task = await controller.submit("test")
        cancelled = await controller.cancel(task.task_id)
        assert cancelled.status == AgentTaskStatus.CANCELLED

    async def test_cancel_nonexistent(self, controller):
        result = await controller.cancel("nonexistent")
        assert result is None

    async def test_get_status(self, controller):
        task = await controller.submit("test")
        loaded = await controller.get_status(task.task_id)
        assert loaded is not None
        assert loaded.prompt == "test"

    async def test_get_status_nonexistent(self, controller):
        result = await controller.get_status("nonexistent")
        assert result is None

    async def test_tick_dispatches_pending_task(self, controller):
        task = await controller.submit("dispatch me", target_model="gpt-4o-mini")
        await controller.tick()
        updated = await controller.get_status(task.task_id)
        assert updated.status in (
            AgentTaskStatus.DISPATCHED,
            AgentTaskStatus.CHECKING,
        )

    async def test_tick_empty_queue_no_error(self, controller):
        result = await controller.tick()
        assert result["dispatched"] >= 0

    async def test_retry_standby(self, controller):
        task = await controller.submit("test")
        # 手动置为 standby
        standby = task.transition_to(AgentTaskStatus.STANDBY, "test")
        await controller.queue.update_status(task.task_id, standby)
        # retry_standby
        result = await controller.retry_standby(task.task_id)
        assert result is not None
        assert result.status == AgentTaskStatus.PENDING
        assert result.retry_count == 0  # reset
