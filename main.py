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


def main() -> None:
    """主入口."""
    from src.gui.launch import run

    asyncio.run(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
