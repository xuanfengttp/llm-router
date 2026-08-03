from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.controller.task_model import AgentTask, AgentTaskStatus


class TestAgentTaskStatus:
    """状态枚举."""

    def test_status_values(self):
        assert AgentTaskStatus.PENDING.value == "pending"
        assert AgentTaskStatus.CHECKING.value == "checking"
        assert AgentTaskStatus.DISPATCHED.value == "dispatched"
        assert AgentTaskStatus.RUNNING.value == "running"
        assert AgentTaskStatus.SUCCESS.value == "success"
        assert AgentTaskStatus.FAILED.value == "failed"
        assert AgentTaskStatus.STANDBY.value == "standby"
        assert AgentTaskStatus.CANCELLED.value == "cancelled"


class TestAgentTask:
    """AgentTask 数据模型."""

    def test_create_minimal(self):
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            prompt="hello",
            target_model="gpt-4o",
        )
        assert task.task_id
        assert task.prompt == "hello"
        assert task.target_model == "gpt-4o"
        assert task.status == AgentTaskStatus.PENDING
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.failure_reason == ""

    def test_create_with_all_fields(self):
        now = datetime.now(timezone.utc).isoformat()
        task = AgentTask(
            task_id="abc-123",
            prompt="test prompt",
            target_model="gpt-4o",
            status=AgentTaskStatus.RUNNING,
            retry_count=1,
            max_retries=5,
            failure_reason="timeout",
            created_at=now,
            updated_at=now,
        )
        assert task.status == AgentTaskStatus.RUNNING
        assert task.retry_count == 1
        assert task.max_retries == 5
        assert task.failure_reason == "timeout"

    def test_is_frozen(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        with pytest.raises(Exception):
            task.status = AgentTaskStatus.RUNNING  # type: ignore

    def test_transition_to(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        new_task = task.transition_to(AgentTaskStatus.RUNNING)
        assert new_task.status == AgentTaskStatus.RUNNING
        assert new_task.task_id == task.task_id
        # 原对象不变
        assert task.status == AgentTaskStatus.PENDING

    def test_transition_with_reason(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        new_task = task.transition_to(AgentTaskStatus.FAILED, reason="test")
        assert new_task.status == AgentTaskStatus.FAILED
        assert new_task.failure_reason == "test"

    def test_with_retry(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        retried = task.with_retry("timeout")
        assert retried.retry_count == 1
        assert retried.status == AgentTaskStatus.FAILED

    def test_with_retry_exceeds_max_goes_standby(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m", retry_count=2)
        retried = task.with_retry("crash")
        assert retried.retry_count == 3
        assert retried.status == AgentTaskStatus.STANDBY

    def test_mark_running(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        running = task.mark_running()
        assert running.status == AgentTaskStatus.RUNNING

    def test_mark_success(self):
        task = AgentTask(
            task_id="a", prompt="p", target_model="m",
            status=AgentTaskStatus.RUNNING,
        )
        done = task.mark_success()
        assert done.status == AgentTaskStatus.SUCCESS

    def test_mark_failed_retryable(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m", retry_count=0)
        failed = task.mark_failed("timeout")
        assert failed.status == AgentTaskStatus.FAILED
        assert failed.retry_count == 1

    def test_mark_failed_exceeds_max(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m", retry_count=2)
        failed = task.mark_failed("timeout")
        assert failed.status == AgentTaskStatus.STANDBY
        assert failed.retry_count == 3

    def test_mark_cancelled(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        cancelled = task.mark_cancelled()
        assert cancelled.status == AgentTaskStatus.CANCELLED

    def test_updated_at_changes_on_transition(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        new_task = task.transition_to(AgentTaskStatus.RUNNING)
        assert new_task.updated_at != task.updated_at

    def test_equality_by_value(self):
        task_id = str(uuid.uuid4())
        a = AgentTask(task_id=task_id, prompt="p", target_model="m")
        b = AgentTask(task_id=task_id, prompt="p", target_model="m")
        assert a == b

    def test_hashable(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        assert hash(task) is not None
