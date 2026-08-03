from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from src.controller.task_model import AgentTask, AgentTaskStatus
from src.controller.task_queue import TaskQueue


class TestTaskQueue:
    """TaskQueue 持久化测试."""

    @pytest.fixture
    def db_path(self, tmp_path: Path):
        return tmp_path / "test_tasks.db"

    @pytest.fixture
    async def queue(self, db_path: Path):
        q = TaskQueue(str(db_path))
        await q.init_db()
        yield q
        await q.close()

    async def test_init_db_creates_table(self, queue, db_path):
        assert db_path.exists()

    async def test_enqueue_and_get(self, queue):
        task = AgentTask(task_id="t1", prompt="hello", target_model="gpt-4o")
        await queue.enqueue(task)
        loaded = await queue.get("t1")
        assert loaded is not None
        assert loaded.prompt == "hello"
        assert loaded.target_model == "gpt-4o"
        assert loaded.status == AgentTaskStatus.PENDING

    async def test_get_nonexistent(self, queue):
        result = await queue.get("nonexistent")
        assert result is None

    async def test_dequeue_pending(self, queue):
        for i in range(5):
            task = AgentTask(task_id=f"t{i}", prompt=f"p{i}", target_model="m")
            await queue.enqueue(task)
        pending = await queue.dequeue_pending(limit=3)
        assert len(pending) == 3
        assert all(t.status == AgentTaskStatus.PENDING for t in pending)

    async def test_dequeue_return_order(self, queue):
        await queue.enqueue(AgentTask(task_id="t1", prompt="first", target_model="m"))
        await queue.enqueue(AgentTask(task_id="t2", prompt="second", target_model="m"))
        pending = await queue.dequeue_pending(limit=5)
        assert pending[0].task_id == "t1"
        assert pending[1].task_id == "t2"

    async def test_dequeue_empty(self, queue):
        result = await queue.dequeue_pending()
        assert result == []

    async def test_update_status(self, queue):
        task = AgentTask(task_id="t1", prompt="p", target_model="m")
        await queue.enqueue(task)
        running = task.mark_running()
        await queue.update_status("t1", running)
        loaded = await queue.get("t1")
        assert loaded.status == AgentTaskStatus.RUNNING

    async def test_list_by_status(self, queue):
        await queue.enqueue(AgentTask(task_id="t1", prompt="p", target_model="m",
                                       status=AgentTaskStatus.SUCCESS))
        await queue.enqueue(AgentTask(task_id="t2", prompt="p", target_model="m"))
        await queue.enqueue(AgentTask(task_id="t3", prompt="p", target_model="m",
                                       status=AgentTaskStatus.FAILED))
        pending = await queue.list_by_status(AgentTaskStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].task_id == "t2"

    async def test_count_by_status(self, queue):
        await queue.enqueue(AgentTask(task_id="t1", prompt="p", target_model="m"))
        await queue.enqueue(AgentTask(task_id="t2", prompt="p", target_model="m",
                                       status=AgentTaskStatus.RUNNING))
        counts = await queue.count_by_status()
        assert counts["pending"] == 1
        assert counts["running"] == 1

    async def test_list_all_pagination(self, queue):
        for i in range(10):
            await queue.enqueue(AgentTask(task_id=f"t{i}", prompt=f"p{i}", target_model="m"))
        first_page = await queue.list_all(limit=3, offset=0)
        second_page = await queue.list_all(limit=3, offset=3)
        assert len(first_page) == 3
        assert len(second_page) == 3
        # 不重叠
        ids_p1 = {t.task_id for t in first_page}
        ids_p2 = {t.task_id for t in second_page}
        assert ids_p1.isdisjoint(ids_p2)

    async def test_enqueue_preserves_all_fields(self, queue):
        task = AgentTask(
            task_id="full-1", prompt="complex prompt", target_model="claude-3-opus",
            status=AgentTaskStatus.PENDING, retry_count=0, max_retries=5,
            failure_reason="", created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        await queue.enqueue(task)
        loaded = await queue.get("full-1")
        assert loaded.max_retries == 5
        assert loaded.created_at == "2026-01-01T00:00:00Z"
