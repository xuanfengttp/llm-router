from __future__ import annotations

import os
from typing import Any, Callable

from PIL import Image, ImageDraw

MENU_ITEMS: list[dict[str, str]] = [
    {"label": "显示窗口", "action": "show"},
    {"label": "切换自动模式", "action": "toggle_auto"},
    {"label": "退出", "action": "quit"},
]


def _create_icon_image(size: int = 32) -> Image.Image:
    """生成简单的 LLM Router 图标（蓝色圆圈 + LR 字母）."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 蓝色圆形背景
    draw.ellipse([2, 2, size - 2, size - 2], fill=(59, 130, 246))
    # 白色 "LR" 文字（用点阵模拟）
    draw.rectangle([8, 8, 11, 24], fill=(255, 255, 255))  # L 竖
    draw.rectangle([8, 22, 18, 25], fill=(255, 255, 255))  # L 横
    draw.rectangle([20, 8, 23, 24], fill=(255, 255, 255))  # R 竖
    draw.arc([19, 8, 26, 18], 270, 90, fill=(255, 255, 255), width=3)  # R 弧
    return img


def build_tooltip_text(active_tasks: int, auto_mode: bool) -> str:
    """构建托盘悬停提示文本."""
    mode = "自动" if auto_mode else "手动"
    if active_tasks == 0:
        return f"LLM Router — 空闲 ({mode})"
    return f"LLM Router — {active_tasks} 任务活跃 ({mode})"


def create_tray(
    auto_mode: bool,
    active_tasks: int,
    show_callback: Callable[[], None],
    toggle_auto_callback: Callable[[], None],
    quit_callback: Callable[[], None],
) -> Any | None:
    """创建系统托盘图标.

    Returns:
        pystray.Icon 实例，或 None（无 display 环境时）.
    """
    if os.name == "nt":
        pass  # Windows 总是有 display
    elif not os.environ.get("DISPLAY"):
        return None  # Linux 无图形环境

    try:
        import pystray
    except ImportError:
        return None

    # 在测试/CI 环境中无法真正渲染托盘，返回 None
    if os.environ.get("CI") or os.environ.get("PYTEST_CURRENT_TEST"):
        return None

    icon = pystray.Icon(
        "llm_router",
        _create_icon_image(),
        build_tooltip_text(active_tasks, auto_mode),
    )

    def on_show(icon: Any, item: Any) -> None:
        show_callback()

    def on_toggle_auto(icon: Any, item: Any) -> None:
        toggle_auto_callback()

    def on_quit(icon: Any, item: Any) -> None:
        icon.stop()
        quit_callback()

    menu = pystray.Menu(
        pystray.MenuItem("显示窗口", on_show, default=True),
        pystray.MenuItem("切换自动模式", on_toggle_auto),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_quit),
    )
    icon.menu = menu
    return icon


def run_tray(icon: Any) -> None:
    """在独立线程中运行托盘."""
    if icon is not None:
        icon.run()
