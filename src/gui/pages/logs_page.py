from __future__ import annotations

from typing import Any

# 全局引用（由 launch.py 注入）
_audit_log: Any = None


def set_audit_log(audit_log) -> None:
    """注入 AuditLog 实例."""
    global _audit_log
    _audit_log = audit_log


def audit_row_to_display(row: dict[str, Any]) -> dict[str, Any]:
    """审计记录原始行 → 显示行（格式化时间 + 截断路径）."""
    ts = row.get("timestamp", "")
    if len(ts) >= 19:
        ts = ts[:19].replace("T", " ")
    path = row.get("path", "")
    if len(path) > 57:
        path = "..." + path[-57:]

    return {
        "id": row.get("id"),
        "timestamp": ts,
        "task_id": row.get("task_id", ""),
        "agent_id": row.get("agent_id", ""),
        "path": path,
        "operation": row.get("operation", ""),
        "path_category": row.get("path_category", ""),
        "decision": row.get("decision", ""),
        "reason": row.get("reason", ""),
    }


def decision_color(decision: str) -> str:
    """审计决策 → 显示颜色."""
    colors = {"allow": "green", "escalate": "orange", "deny": "red"}
    return colors.get(decision, "grey")


def operation_cn(operation: str) -> str:
    """操作枚举 → 中文."""
    labels = {"read": "读取", "write": "写入", "delete": "删除", "execute": "执行"}
    return labels.get(operation, operation)


# ── NiceGUI 组件 ──────────────────────────────────

def render() -> None:
    """渲染日志/审计页面."""
    from nicegui import ui

    ui.label("日志与审计").classes("text-h4")

    # 标签切换
    with ui.tabs() as tabs:
        audit_tab = ui.tab("审计日志")
        task_tab = ui.tab("任务操作")
        switch_tab = ui.tab("模型切换")

    with ui.tab_panels(tabs, value=audit_tab):
        with ui.tab_panel(audit_tab):
            _render_audit_table()
        with ui.tab_panel(task_tab):
            _render_task_ops_table()
        with ui.tab_panel(switch_tab):
            _render_model_switch_table()


def _render_audit_table() -> None:
    from nicegui import ui

    columns = [
        {"name": "timestamp", "label": "时间", "field": "timestamp"},
        {"name": "task_id", "label": "任务ID", "field": "task_id"},
        {"name": "agent_id", "label": "Agent", "field": "agent_id"},
        {"name": "path", "label": "路径", "field": "path"},
        {"name": "operation", "label": "操作", "field": "operation"},
        {"name": "decision", "label": "决策", "field": "decision"},
        {"name": "reason", "label": "原因", "field": "reason"},
    ]
    ui.table(columns=columns, rows=[]).classes("w-full")


def _render_task_ops_table() -> None:
    from nicegui import ui

    columns = [
        {"name": "time", "label": "时间", "field": "time"},
        {"name": "task_id", "label": "任务ID", "field": "task_id"},
        {"name": "action", "label": "操作", "field": "action"},
        {"name": "detail", "label": "详情", "field": "detail"},
    ]
    ui.table(columns=columns, rows=[]).classes("w-full")


def _render_model_switch_table() -> None:
    from nicegui import ui

    columns = [
        {"name": "time", "label": "时间", "field": "time"},
        {"name": "task_id", "label": "任务ID", "field": "task_id"},
        {"name": "from_model", "label": "原模型", "field": "from_model"},
        {"name": "to_model", "label": "切换至", "field": "to_model"},
        {"name": "reason", "label": "原因", "field": "reason"},
    ]
    ui.table(columns=columns, rows=[]).classes("w-full")
