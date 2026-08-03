from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.a2a.cli_driver import CLIDriver, DriverConfig
from src.a2a.driver_registry import DriverRegistry
from src.a2a.gateway import A2AGateway
from src.controller.task_model import AgentTask, AgentTaskStatus
from src.controller.task_queue import TaskQueue


class TestA2AGateway:
    @pytest.fixture
    def registry(self):
        driver = CLIDriver(DriverConfig(
            name="echo",
            command="python",
            default_timeout_seconds=30.0,
        ))
        reg = DriverRegistry()
        reg.register(driver)
        return reg

    @pytest.fixture
    def gateway(self, registry):
        return A2AGateway(registry)

    @pytest.fixture
    async def queue(self, tmp_path: Path):
        q = TaskQueue(str(tmp_path / "test_a2a.db"))
        await q.init_db()
        yield q
        await q.close()

    @pytest.mark.asyncio
    async def test_create_gateway(self, gateway, registry):
        assert gateway.registry is registry

    @pytest.mark.asyncio
    async def test_execute_success(self, gateway):
        task = AgentTask(task_id="t1", prompt="hello", target_model="echo")
        updated, result = await gateway.execute(
            task,
            workspace_root=os.getcwd(),
            driver_name="echo",
        )
        assert updated.status == AgentTaskStatus.SUCCESS
        assert result.exit_code == 0
        assert result.timed_out is False

    @pytest.mark.asyncio
    async def test_execute_sets_running(self, gateway):
        task = AgentTask(task_id="t2", prompt="hi", target_model="echo")
        updated, result = await gateway.execute(
            task,
            workspace_root=os.getcwd(),
            driver_name="echo",
        )
        # 最终状态是 SUCCESS，但执行过程中经过了 RUNNING
        assert updated.status == AgentTaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_timeout(self, gateway):
        """超时任务应标记为 FAILED."""
        slow_driver = CLIDriver(DriverConfig(
            name="slow",
            command="python",
            default_timeout_seconds=0.5,
        ))
        gateway.registry.register(slow_driver)

        task = AgentTask(task_id="t3", prompt="sleep_10", target_model="slow")
        updated, result = await gateway.execute(
            task,
            workspace_root=os.getcwd(),
            driver_name="slow",
            timeout_seconds=0.3,
        )
        assert updated.status == AgentTaskStatus.FAILED
        assert result.timed_out is True

    @pytest.mark.asyncio
    async def test_execute_error_exit_code(self, gateway):
        """非零退出码应标记为 FAILED."""
        fail_driver = CLIDriver(DriverConfig(
            name="fail",
            command="python",
            default_timeout_seconds=30.0,
        ))
        gateway.registry.register(fail_driver)

        task = AgentTask(task_id="t4", prompt="exit_1", target_model="fail")
        updated, result = await gateway.execute(
            task,
            workspace_root=os.getcwd(),
            driver_name="fail",
        )
        assert updated.status == AgentTaskStatus.FAILED
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_execute_nonexistent_driver(self, gateway):
        task = AgentTask(task_id="t5", prompt="hi", target_model="m")
        updated, result = await gateway.execute(
            task,
            workspace_root=os.getcwd(),
            driver_name="nonexistent",
        )
        assert updated.status == AgentTaskStatus.FAILED
        assert "not found" in updated.failure_reason.lower()

    @pytest.mark.asyncio
    async def test_execute_elapsed_is_recorded(self, gateway):
        task = AgentTask(task_id="t6", prompt="hi", target_model="echo")
        updated, result = await gateway.execute(
            task,
            workspace_root=os.getcwd(),
            driver_name="echo",
        )
        assert result.elapsed_seconds > 0
        assert result.elapsed_seconds < 60.0
