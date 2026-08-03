from __future__ import annotations

import asyncio
import uuid

from src.controller.dispatcher import DispatchEngine
from src.controller.recovery import FailureInfo, RecoveryAction, RecoveryEngine
from src.controller.task_model import AgentTask, AgentTaskStatus
from src.controller.task_queue import TaskQueue


class TaskController:
    def __init__(
        self,
        queue: TaskQueue,
        dispatcher: DispatchEngine,
        recovery: RecoveryEngine,
        cycle_seconds: float = 30.0,
    ) -> None:
        self.queue = queue
        self.dispatcher = dispatcher
        self.recovery = recovery
        self.cycle_seconds = cycle_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            await self.tick()
            await asyncio.sleep(self.cycle_seconds)

    async def tick(self) -> dict:
        dispatched = 0
        recovered = 0
        stood_by = 0

        # 处理 PENDING 任务
        pending = await self.queue.dequeue_pending(limit=10)
        for task in pending:
            ok, reason = await self.dispatcher.check(task)
            if ok:
                result = await self.dispatcher.dispatch(task, {})
                if result is not None:
                    dispatched_task = task.transition_to(AgentTaskStatus.DISPATCHED)
                    await self.queue.update_status(task.task_id, dispatched_task)
                    dispatched += 1

        # 处理 FAILED 任务（可重试的）
        failed_tasks = await self.queue.list_by_status(AgentTaskStatus.FAILED)
        for task in failed_tasks:
            fi = FailureInfo(
                failure_type="network",
                message=task.failure_reason or "unknown",
            )
            action, _reason = self.recovery.decide(task, fi)
            if action in (RecoveryAction.RETRY_SAME_MODEL, RecoveryAction.RETRY_SWITCH_MODEL):
                retried = task.transition_to(AgentTaskStatus.PENDING)
                await self.queue.update_status(task.task_id, retried)
                recovered += 1
            elif action == RecoveryAction.STANDBY:
                standby = task.transition_to(AgentTaskStatus.STANDBY, task.failure_reason)
                await self.queue.update_status(task.task_id, standby)
                stood_by += 1

        return {"dispatched": dispatched, "recovered": recovered, "stood_by": stood_by}

    async def submit(self, prompt: str, target_model: str = "") -> AgentTask:
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            prompt=prompt,
            target_model=target_model,
        )
        await self.queue.enqueue(task)
        return task

    async def cancel(self, task_id: str) -> AgentTask | None:
        task = await self.queue.get(task_id)
        if task is None:
            return None
        cancelled = task.mark_cancelled()
        await self.queue.update_status(task_id, cancelled)
        return cancelled

    async def retry_standby(self, task_id: str) -> AgentTask | None:
        task = await self.queue.get(task_id)
        if task is None:
            return None
        retried = AgentTask(
            task_id=task.task_id,
            prompt=task.prompt,
            target_model=task.target_model,
            status=AgentTaskStatus.PENDING,
            retry_count=0,
            max_retries=task.max_retries,
            failure_reason="",
            created_at=task.created_at,
        )
        await self.queue.update_status(task_id, retried)
        return retried

    async def get_status(self, task_id: str) -> AgentTask | None:
        return await self.queue.get(task_id)
