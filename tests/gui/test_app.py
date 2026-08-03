from __future__ import annotations

import pytest


class TestGuiAppCreation:
    """测试 NiceGUI app 创建."""

    def test_app_module_imports(self):
        """验证 app 模块可以导入."""
        from src.gui.app import create_app
        assert callable(create_app)

    def test_pages_module_exists(self):
        """验证 pages 子模块存在."""
        import src.gui.pages  # noqa: F401


class TestAppConfig:
    """测试 app 配置参数."""

    def test_default_title(self):
        from src.gui.app import APP_CONFIG
        assert "title" in APP_CONFIG
        assert APP_CONFIG["title"] == "LLM Router"

    def test_default_port(self):
        from src.gui.app import APP_CONFIG
        assert "port" in APP_CONFIG
        assert APP_CONFIG["port"] == 8080
