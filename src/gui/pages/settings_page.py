from __future__ import annotations

from typing import Any

STRATEGY_OPTIONS = [
    {"id": "baseline", "label": "均衡评分", "description": "能力 40% + 延迟 30% + 成本 30%"},
    {"id": "cost_first", "label": "成本优先", "description": "成本权重 60%，适合批量任务"},
    {"id": "quality_first", "label": "质量优先", "description": "能力权重 70%，适合关键任务"},
    {"id": "latency_aware", "label": "延迟感知", "description": "延迟权重 60%，适合实时场景"},
    {"id": "task_specific", "label": "任务分域", "description": "动态权重，根据任务类型自适应"},
]

DEFAULT_SETTINGS: dict[str, Any] = {
    "strategy": "baseline",
    "latency_redline_ms": 5000,
    "predictability_threshold": 0.3,
    "cycle_seconds": 30,
}


def time_window_to_dict(tw: Any) -> dict[str, Any]:
    """TimeWindow -> serializable dict."""
    return {
        "weekday_night_start": getattr(tw, "weekday_night_hours", (22, 6))[0],
        "weekday_night_end": getattr(tw, "weekday_night_hours", (22, 6))[1],
        "weekend_all_day": getattr(tw, "weekend_all_day", True),
    }


# Injection references
_route_engine: Any = None
_dispatcher: Any = None


def set_services(route_engine=None, dispatcher=None) -> None:
    """Inject backend service references."""
    global _route_engine, _dispatcher
    _route_engine = route_engine
    _dispatcher = dispatcher


# -- NiceGUI components -----------------------------------

def render() -> None:
    """Render the settings page."""
    from nicegui import ui

    ui.label("设置").classes("text-h4")

    # Routing strategy
    with ui.card():
        ui.label("路由策略").classes("text-h6")
        strategy = ui.select(
            label="当前策略",
            options={s["id"]: s["label"] for s in STRATEGY_OPTIONS},
            value=DEFAULT_SETTINGS["strategy"],
        ).classes("w-64")

    # Parameter configuration
    with ui.card():
        ui.label("分发参数").classes("text-h6")
        latency_slider = ui.slider(
            min=1000, max=10000, step=500,
            value=DEFAULT_SETTINGS["latency_redline_ms"],
        ).props("label=延迟红线 (ms)")
        predictability_slider = ui.slider(
            min=0.0, max=1.0, step=0.05,
            value=DEFAULT_SETTINGS["predictability_threshold"],
        ).props("label=可预测性阈值")
        cycle_spin = ui.number(
            label="轮询间隔 (秒)",
            value=DEFAULT_SETTINGS["cycle_seconds"],
            min=5, max=300,
        ).classes("w-32")

    # Time window
    with ui.card():
        ui.label("时间窗口").classes("text-h6")
        ui.label("工作日夜间 / 周末全天 — 自动模式").classes("text-caption")
        with ui.row():
            ui.number("夜间开始 (时)", value=22, min=0, max=23).classes("w-24")
            ui.number("夜间结束 (时)", value=6, min=0, max=23).classes("w-24")
        ui.switch("周末全天自动", value=True)

    ui.button("保存设置", on_click=lambda: ui.notify("设置已保存"))
