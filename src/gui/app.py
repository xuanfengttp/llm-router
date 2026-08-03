from __future__ import annotations

APP_CONFIG = {
    "title": "LLM Router",
    "port": 8080,
    "favicon": "🔄",
}


def create_app() -> None:
    """注册所有功能页面路由。

    NiceGUI 3.x 用 @ui.page() 装饰器定义页面路径，每个页面的
    render() 函数作为页面内容渲染。
    """
    from nicegui import ui

    # 导入页面模块的 render 函数
    from src.gui.pages.config_page import render as config_render
    from src.gui.pages.dashboard import render as dashboard_render
    from src.gui.pages.logs_page import render as logs_render
    from src.gui.pages.settings_page import render as settings_render
    from src.gui.pages.tasks_page import render as tasks_render

    @ui.page("/")
    def index_page():
        """根路径重定向到仪表板."""
        with ui.header(elevated=True).classes("items-center justify-between"):
            ui.label("LLM Router").classes("text-h5")
            ui.space()
            ui.link("仪表板", "/dashboard").classes("text-white")
            ui.link("连接配置", "/config").classes("text-white")
            ui.link("任务管理", "/tasks").classes("text-white")
            ui.link("日志审计", "/logs").classes("text-white")
            ui.link("设置", "/settings").classes("text-white")

        dashboard_render()

    @ui.page("/config")
    def config_page():
        _render_with_header("连接配置", config_render)

    @ui.page("/dashboard")
    def dashboard_page():
        _render_with_header("仪表板", dashboard_render)

    @ui.page("/tasks")
    def tasks_page():
        _render_with_header("任务管理", tasks_render)

    @ui.page("/logs")
    def logs_page():
        _render_with_header("日志审计", logs_render)

    @ui.page("/settings")
    def settings_page():
        _render_with_header("设置", settings_render)


def _render_with_header(active_label: str, render_fn) -> None:
    """带统一顶栏的页面布局."""
    from nicegui import ui

    with ui.header(elevated=True).classes("items-center justify-between"):
        ui.link("LLM Router 🗲", "/").classes("text-h5 no-underline text-white font-bold")
        ui.space()
        tabs = [
            ("仪表板", "/dashboard"),
            ("连接配置", "/config"),
            ("任务管理", "/tasks"),
            ("日志审计", "/logs"),
            ("设置", "/settings"),
        ]
        for label, path in tabs:
            link = ui.link(label, path).classes("text-white")
            if label == active_label:
                link.classes("text-white font-bold underline")

    render_fn()


def run_app(port: int = 8080, native: bool = True, **kwargs) -> None:
    """启动 NiceGUI 应用.

    Args:
        port: HTTP 端口
        native: 是否使用内嵌浏览器窗口
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
