"""LLM Router 入口.

用法:
    python main.py                  # 默认：内嵌浏览器 + 系统托盘，端口 8080
    python main.py --port 9090      # 指定端口
    python main.py --no-native      # 使用系统浏览器（不弹窗）
    python main.py --no-tray        # 禁用系统托盘
"""

from __future__ import annotations

import asyncio
import sys
import webbrowser
import threading
import time


def _open_browser(port: int, delay: float = 1.5) -> None:
    """延迟后打开浏览器."""
    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    """主入口."""
    from src.gui.launch import parse_args, run

    args = parse_args(sys.argv[1:])

    # 打包环境自动打开浏览器（没有原生窗口可依赖）
    if getattr(sys, "frozen", False) and not args.no_native:
        threading.Thread(target=_open_browser, args=(args.port,), daemon=True).start()

    asyncio.run(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
