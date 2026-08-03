# src/gui/pages/tasks_page.py
from __future__ import annotations

from typing import Any

from src.controller.task_model import AgentTask, AgentTaskStatus

# 全局引用（由 launch.py 注入）
_controller: Any = None
_task_queue: Any = None


def set_controller(controller, task_queue) -> None:
    """注入 Controller 和 TaskQueue 引用."""
    global _controller, _task_queue
    _controller = controller
    _task_queue = task_queue


def group_tasks_by_status(tasks: list[AgentTask]) -> dict[str, list[AgentTask]]:
    """任务按三列分组：待分发 / 执行中 / 失败+暂停."""
    groups: dict[str, list[AgentTask]] = {
        "pending": [],
        "running": [],
        "failed_standby": [],
    }
    for t in tasks:
        if t.status == AgentTaskStatus.PENDING:
            groups["pending"].append(t)
        elif t.status in (AgentTaskStatus.RUNNING, AgentTaskStatus.CHECKING, AgentTaskStatus.DISPATCHED):
            groups["running"].append(t)
        elif t.status in (AgentTaskStatus.FAILED, AgentTaskStatus.STANDBY):
            groups["failed_standby"].append(t)
    return groups


def task_to_card(task: AgentTask) -> dict[str, Any]:
    """任务 -> 卡片展示数据."""
    return {
        "task_id": task.task_id,
        "task_id_short": task.task_id[:8],
        "prompt": task.prompt,
        "target_model": task.target_model,
        "status": task.status.value,
        "retry_info": f"{task.retry_count}/{task.max_retries}",
        "failure_reason": task.failure_reason,
    }


def status_cn_label(status: AgentTaskStatus) -> str:
    """状态枚举 -> 中文标签."""
    labels = {
        AgentTaskStatus.PENDING: "待分发",
        AgentTaskStatus.CHECKING: "校验中",
        AgentTaskStatus.DISPATCHED: "已分发",
        AgentTaskStatus.RUNNING: "执行中",
        AgentTaskStatus.SUCCESS: "成功",
        AgentTaskStatus.FAILED: "失败",
        AgentTaskStatus.STANDBY: "暂停",
        AgentTaskStatus.CANCELLED: "已取消",
    }
    return labels.get(status, status.value)


# ── NiceGUI 组件 ──────────────────────────────────


def render() -> None:
    """渲染任务管理页面."""
    from nicegui import ui

    ui.label("任务管理").classes("text-h4")

    # 新建任务区
    with ui.card():
        ui.label("新建任务").classes("text-h6")
        with ui.row():
            prompt_input = ui.textarea("Prompt").classes("w-96")
            model_input = ui.input("目标模型").classes("w-40")
        ui.button("提交任务", on_click=lambda: _submit_task(
            prompt_input.value or "",
            model_input.value or "",
        ))

    # 自动模式开关
    with ui.row():
        ui.switch("自动模式")

    # 三列队列
    with ui.row().classes("w-full"):
        with ui.column().classes("w-1/3"):
            ui.label("待分发").classes("text-subtitle1")
        with ui.column().classes("w-1/3"):
            ui.label("执行中").classes("text-subtitle1")
        with ui.column().classes("w-1/3"):
            ui.label("失败/暂停").classes("text-subtitle1")

    # 分发日志
    with ui.card():
        ui.label("分发日志（最近 20 条）").classes("text-h6")


async def _submit_task(prompt: str, model: str) -> None:
    """提交新任务."""
    if _controller:
        await _controller.submit(prompt, model)
        from nicegui import ui

        ui.notify(f"任务已提交 -> {model}")
