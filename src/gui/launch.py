# src/gui/launch.py
from __future__ import annotations

import argparse
import os
import threading
from pathlib import Path
from typing import Any


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数."""
    parser = argparse.ArgumentParser(description="LLM Router — 智能 Agent 任务调度")
    parser.add_argument("--port", type=int, default=8080, help="Web 界面端口 (默认 8080)")
    parser.add_argument("--no-native", action="store_true", help="禁用内嵌浏览器，使用浏览器访问")
    parser.add_argument("--no-tray", action="store_true", help="禁用系统托盘")
    parser.add_argument("--db-dir", type=str, default=None, help="SQLite 数据库目录")
    return parser.parse_args(argv)


async def _build_config_manager(data_dir: str) -> Any:
    """构建 ConfigManager（用内存数据库做测试友好模式）."""
    from src.config.crypto import generate_key, KeyCipher
    from src.config.manager import ConfigManager
    from src.config.store import ConfigStore

    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    config_path = data_path / "providers.yaml"
    key = generate_key()
    cipher = KeyCipher(key)
    store = ConfigStore(config_path=config_path, cipher=cipher, db_path=data_path / "router_state.db")
    await store.init_db()
    return ConfigManager(store)


def _get_data_dir() -> str:
    """获取数据目录（创建于用户目录下）."""
    home = Path.home()
    data_dir = home / ".llm_router"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)


async def run(argv: list[str] | None = None) -> None:
    """启动 LLM Router 完整应用.

    1. 解析参数
    2. 构建后端服务（ConfigManager、TaskQueue 等）
    3. 注入到 GUI 页面
    4. 启动 NiceGUI
    5. 启动系统托盘（独立线程）
    """
    args = parse_args(argv)

    data_dir = args.db_dir or _get_data_dir()

    # 构建 ConfigManager
    config_manager = await _build_config_manager(data_dir)

    # 注入到配置页
    from src.gui.pages import config_page

    config_page.set_config_manager(config_manager)

    # 注入到仪表板
    from src.gui.pages import dashboard

    dashboard.set_services(
        network_probe=None,
        prediction_engine=None,
        config_manager=config_manager,
    )

    # 注入到任务页
    from src.gui.pages import tasks_page

    tasks_page.set_controller(None, None)

    # 注入到日志页
    from src.gui.pages import logs_page

    logs_page.set_audit_log(None)

    # 注入到设置页
    from src.gui.pages import settings_page

    settings_page.set_services(route_engine=None, dispatcher=None)

    # 自动模式状态
    auto_mode = True
    active_tasks = 0

    # 启动托盘（独立线程）
    if not args.no_tray:
        from src.gui.tray import create_tray, run_tray

        def show_window() -> None:
            pass  # NiceGUI 窗口自动显示

        def toggle_auto() -> None:
            nonlocal auto_mode
            auto_mode = not auto_mode

        def quit_app() -> None:
            nonlocal auto_mode
            auto_mode = False
            # 托盘退出 → 触发应用关闭
            os._exit(0)

        tray_icon = create_tray(
            auto_mode=auto_mode,
            active_tasks=active_tasks,
            show_callback=show_window,
            toggle_auto_callback=toggle_auto,
            quit_callback=quit_app,
        )
        if tray_icon:
            tray_thread = threading.Thread(target=run_tray, args=(tray_icon,), daemon=True)
            tray_thread.start()

    # 启动 NiceGUI
    from src.gui.app import run_app

    run_app(port=args.port, native=not args.no_native)
