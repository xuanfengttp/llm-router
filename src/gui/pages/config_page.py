# src/gui/pages/config_page.py
from __future__ import annotations

from typing import Any

from src.config.manager import ConfigManager
from src.config.models import ModelConfig, ProviderConfig

# 全局 ConfigManager 引用（由 launch.py 注入）
_config_manager: ConfigManager | None = None


def set_config_manager(cm: ConfigManager) -> None:
    """注入 ConfigManager 实例."""
    global _config_manager
    _config_manager = cm


def provider_to_row(provider: ProviderConfig) -> dict[str, Any]:
    """Provider 转为表格行数据."""
    return {
        "name": provider.name,
        "endpoint": provider.endpoint,
        "model_count": len(provider.models),
        "status": provider.status.value,
    }


def model_to_row(model: ModelConfig) -> dict[str, Any]:
    """Model 转为表格行数据."""
    return {
        "name": model.name,
        "deployment": str(model.deployment),
        "cost_input": model.cost_input_1k,
        "cost_output": model.cost_output_1k,
        "context_window": model.context_window,
    }


def connectivity_label(latency_ms: float | None) -> tuple[str, str]:
    """延迟 → (标签文字, 颜色)."""
    if latency_ms is None:
        return ("未测试", "grey")
    if latency_ms < 300:
        return (f"良好 ({latency_ms:.0f}ms)", "green")
    if latency_ms < 1000:
        return (f"一般 ({latency_ms:.0f}ms)", "orange")
    return (f"较差 ({latency_ms:.0f}ms)", "red")


# ── NiceGUI 组件 ──────────────────────────────────

def render() -> None:
    """渲染连接配置页面."""
    from nicegui import ui

    ui.label("连接配置").classes("text-h4")

    # Provider 表格
    async def load_providers() -> list[dict]:
        if _config_manager is None:
            return []
        providers = await _config_manager.list_providers()
        return [provider_to_row(p) for p in providers]

    # 添加 Provider 对话框
    async def on_add_provider(name: str, endpoint: str, api_key: str) -> None:
        if _config_manager:
            await _config_manager.add_provider(name, endpoint, api_key)
            ui.notify(f"Provider '{name}' 已添加")

    # 删除 Provider
    async def on_remove_provider(name: str) -> None:
        if _config_manager:
            await _config_manager.remove_provider(name)
            ui.notify(f"Provider '{name}' 已删除")

    with ui.card():
        ui.label("Providers").classes("text-h6")

        with ui.row():
            name_input = ui.input("名称").classes("w-40")
            endpoint_input = ui.input("Endpoint").classes("w-80")
            api_key_input = ui.input("API Key").props("type=password").classes("w-60")

        ui.button("添加 Provider", on_click=lambda: on_add_provider(
            name_input.value or "",
            endpoint_input.value or "",
            api_key_input.value or "",
        ))

        # Provider 列表表格
        columns = [
            {"name": "name", "label": "名称", "field": "name"},
            {"name": "endpoint", "label": "Endpoint", "field": "endpoint"},
            {"name": "model_count", "label": "模型数", "field": "model_count"},
            {"name": "status", "label": "状态", "field": "status"},
        ]
        ui.table(columns=columns, rows=[]).classes("w-full")

    # 模型管理区
    with ui.card():
        ui.label("模型管理").classes("text-h6")
        ui.label("选择 Provider 后查看/管理其模型").classes("text-caption")
