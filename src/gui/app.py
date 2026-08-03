from __future__ import annotations

APP_CONFIG = {
    "title": "LLM Router",
    "port": 8080,
    "favicon": "🔄",
}


def create_app() -> None:
    """创建并配置 NiceGUI 应用.

    注册所有 5 个功能页面，设置页面标签导航。
    """
    from nicegui import ui

    # 页面注册在 ui.run() 之前通过导入完成
    # 实际页面在各自模块的顶层定义
    from src.gui.pages import (  # noqa: F811
        config_page,
        dashboard,
        logs_page,
        settings_page,
        tasks_page,
    )


def run_app(port: int = 8080, native: bool = True, **kwargs) -> None:
    """启动 NiceGUI 应用.

    Args:
        port: HTTP 端口（native=False 时使用）
        native: 是否使用内嵌浏览器窗口
        **kwargs: 传递给 ui.run() 的额外参数
    """
    from nicegui import ui

    create_app()
    ui.run(
        title=APP_CONFIG["title"],
        favicon=APP_CONFIG["favicon"],
        port=port,
        native=native,
        reload=False,
        show=True,
        **kwargs,
    )
