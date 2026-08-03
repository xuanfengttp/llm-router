from __future__ import annotations

import os

from src.a2a.cli_driver import DriverResult
from src.a2a.driver_registry import DriverRegistry
from src.controller.task_model import AgentTask


class A2AGateway:
    def __init__(self, registry: DriverRegistry) -> None:
        self.registry = registry

    async def execute(
        self,
        task: AgentTask,
        workspace_root: str = "",
        driver_name: str = "",
        timeout_seconds: float | None = None,
    ) -> tuple[AgentTask, DriverResult]:
        # 1. 标记 RUNNING
        running_task = task.mark_running()

        # 2. 选择 driver
        driver = None
        if driver_name:
            driver = self.registry.get(driver_name)

        if driver is None:
            failed_task = running_task.mark_failed(
                f"Driver '{driver_name}' not found in registry"
            )
            # 构造一个虚拟 DriverResult
            fake_result = DriverResult(
                driver_name=driver_name,
                task_id=task.task_id,
                exit_code=-1,
                stdout="",
                stderr=f"Driver '{driver_name}' not found",
                timed_out=False,
                elapsed_seconds=0.0,
            )
            return failed_task, fake_result

        # 3. 确定 workspace_root
        if not workspace_root:
            workspace_root = os.path.join("workspaces", task.task_id)

        # 4. 启动子进程
        result = await driver.launch(
            task_id=task.task_id,
            prompt=task.prompt,
            workspace_root=workspace_root,
            timeout_seconds=timeout_seconds,
        )

        # 5. 根据结果更新任务状态
        if result.timed_out:
            updated = running_task.mark_failed("timeout")
        elif result.exit_code != 0:
            updated = running_task.mark_failed(f"exit_code: {result.exit_code}")
        else:
            updated = running_task.mark_success()

        return updated, result
