# src/gui/pages/dashboard.py
from __future__ import annotations

from typing import Any

# 全局引用（由 launch.py 注入）
_network_probe: Any = None
_prediction_engine: Any = None
_config_manager: Any = None


def set_services(network_probe=None, prediction_engine=None, config_manager=None) -> None:
    """注入后端服务引用."""
    global _network_probe, _prediction_engine, _config_manager
    _network_probe = network_probe
    _prediction_engine = prediction_engine
    _config_manager = config_manager


def latency_to_echarts(records: list[dict]) -> dict[str, Any]:
    """延迟记录 → ECharts option 数据.

    按模型分组产生多条折线。
    """
    if not records:
        return {"xAxis": [], "series": []}

    # 按模型分组
    by_model: dict[str, list[tuple[str, float]]] = {}
    for r in records:
        model = r.get("model", "unknown")
        ts = r.get("timestamp", "")[:19]  # 截断到秒
        latency = r.get("latency_ms", 0.0)
        by_model.setdefault(model, []).append((ts, latency))

    # 收集所有时间点（去重排序）
    all_ts = sorted({ts for pts in by_model.values() for ts, _ in pts})

    series = []
    for model, points in by_model.items():
        ts_map = dict(points)
        data = [ts_map.get(ts, None) for ts in all_ts]
        series.append({
            "name": model,
            "type": "line",
            "data": data,
            "smooth": True,
        })

    return {"xAxis": all_ts, "series": series}


def predictability_label(score: float | None) -> tuple[str, str]:
    """可预测性分数 → (标签, 颜色)."""
    if score is None:
        return ("无数据", "grey")
    if score >= 0.7:
        return ("高", "green")
    if score >= 0.4:
        return ("中", "orange")
    return ("低", "red")


def status_color(status: str) -> str:
    """Provider 状态字符串 → 颜色."""
    colors = {"online": "green", "degraded": "orange", "offline": "red", "unknown": "grey"}
    return colors.get(status, "grey")


# ── NiceGUI 组件 ──────────────────────────────────

def render() -> None:
    """渲染监控仪表板页面."""
    from nicegui import ui

    ui.label("监控仪表板").classes("text-h4")

    # ECharts 图表
    with ui.card():
        ui.label("延迟曲线").classes("text-h6")

        # 使用 ECharts CDN
        ui.add_head_html("""
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
        """)

        chart = ui.html().classes("w-full")
        chart.style("height: 400px")
        chart.set_content('<div id="latency-chart" style="width:100%;height:400px;"></div>')

        ui.timer(5.0, lambda: _refresh_chart())

    # 预测面板
    with ui.card():
        ui.label("延迟预测").classes("text-h6")
        with ui.row():
            ui.label("P50: --")
            ui.label("P90: --")
            ui.label("可预测性: --")

    # Provider 状态指示
    with ui.card():
        ui.label("Provider 状态").classes("text-h6")


def _refresh_chart() -> None:
    """定时刷新 ECharts 数据."""
    pass  # 通过 ui.run_javascript 动态更新
