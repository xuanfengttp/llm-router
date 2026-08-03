from __future__ import annotations

import argparse
import asyncio
import os
import sys
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
    """构建 ConfigManager."""
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


def _is_packaged() -> bool:
    """判断是否在 PyInstaller 打包环境中运行."""
    return getattr(sys, "frozen", False)


async def _init_services(args: argparse.Namespace) -> None:
    """初始化所有后端服务并注入到 GUI 页面（async 阶段）."""
    data_dir = args.db_dir or _get_data_dir()

    config_manager = await _build_config_manager(data_dir)

    from src.gui.pages import config_page

    config_page.set_config_manager(config_manager)

    from src.gui.pages import dashboard

    dashboard.set_services(
        network_probe=None,
        prediction_engine=None,
        config_manager=config_manager,
    )

    from src.gui.pages import tasks_page

    tasks_page.set_controller(None, None)

    from src.gui.pages import logs_page

    logs_page.set_audit_log(None)

    from src.gui.pages import settings_page

    settings_page.set_services(route_engine=None, dispatcher=None)


def _start_tray(args: argparse.Namespace) -> Any:
    """启动系统托盘（独立线程），返回 tray_icon 或 None."""
    if args.no_tray:
        return None

    from src.gui.tray import create_tray, run_tray

    auto_mode = True

    def show_window() -> None:
        pass

    def toggle_auto() -> None:
        nonlocal auto_mode
        auto_mode = not auto_mode

    def quit_app() -> None:
        os._exit(0)

    tray_icon = create_tray(
        auto_mode=auto_mode,
        active_tasks=0,
        show_callback=show_window,
        toggle_auto_callback=toggle_auto,
        quit_callback=quit_app,
    )
    if tray_icon:
        tray_thread = threading.Thread(target=run_tray, args=(tray_icon,), daemon=True)
        tray_thread.start()
    return tray_icon


def run(argv: list[str] | None = None) -> None:
    """启动 LLM Router 完整应用（同步入口）.

    1. 解析参数
    2. 初始化后端服务（async）
    3. 注册页面路由
    4. 启动系统托盘
    5. 启动 NiceGUI（ui.run 自己管理事件循环）
    """
    args = parse_args(argv)

    # 阶段 1: 异步初始化（用 asyncio.run 跑完即释放事件循环）
    asyncio.run(_init_services(args))

    # 阶段 2: 注册页面路由
    from src.gui.app import create_app

    create_app()

    # 阶段 3: 启动托盘
    _start_tray(args)

    # 阶段 4: 启动 NiceGUI（同步调用，内部自己管理 asyncio）
    from nicegui import ui

    use_native = not args.no_native and not _is_packaged()

    ui.run(
        title="LLM Router",
        favicon="🔄",
        port=args.port,
        native=use_native,
        reload=False,
        show=True,
    )
