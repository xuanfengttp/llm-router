from __future__ import annotations

import pytest


class TestTrayIcon:
    """测试系统托盘逻辑."""

    def test_create_icon_image(self):
        """生成图标图像（非 None）."""
        from src.gui.tray import _create_icon_image

        img = _create_icon_image()
        assert img is not None
        assert img.size[0] > 0
        assert img.size[1] > 0

    def test_build_tooltip_text(self):
        """构建悬停提示文本."""
        from src.gui.tray import build_tooltip_text

        text = build_tooltip_text(active_tasks=3, auto_mode=True)
        assert "3" in text
        assert "自动" in text

    def test_build_tooltip_idle(self):
        """空闲状态提示."""
        from src.gui.tray import build_tooltip_text

        text = build_tooltip_text(active_tasks=0, auto_mode=False)
        assert "空闲" in text
        assert "手动" in text

    def test_tray_menu_items_exist(self):
        """菜单项列表非空."""
        from src.gui.tray import MENU_ITEMS

        assert len(MENU_ITEMS) >= 3
        labels = [m["label"] for m in MENU_ITEMS]
        assert any("显示" in l for l in labels)
        assert any("自动" in l for l in labels)
        assert any("退出" in l for l in labels)

    def test_create_tray_returns_none_when_no_display(self):
        """无 display 环境时返回 None."""
        from src.gui.tray import create_tray

        tray = create_tray(
            auto_mode=True,
            active_tasks=0,
            show_callback=lambda: None,
            toggle_auto_callback=lambda: None,
            quit_callback=lambda: None,
        )
        assert tray is None  # 测试环境无 $DISPLAY
