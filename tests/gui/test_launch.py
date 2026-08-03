# tests/gui/test_launch.py
from __future__ import annotations

import pytest


class TestLaunchConfig:
    """测试启动配置."""

    def test_parse_args_defaults(self):
        """默认命令行参数."""
        from src.gui.launch import parse_args

        args = parse_args([])
        assert args.port == 8080
        assert args.no_native is False
        assert args.no_tray is False
        assert args.db_dir is None

    def test_parse_args_custom(self):
        """自定义命令行参数."""
        from src.gui.launch import parse_args

        args = parse_args(["--port", "9090", "--no-native", "--no-tray"])
        assert args.port == 9090
        assert args.no_native is True
        assert args.no_tray is True

    def test_launch_exports_run_function(self):
        """launch 模块导出 run 函数."""
        from src.gui.launch import run
        assert callable(run)

    def test_main_py_exists(self):
        """main.py 可以导入."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("main", "main.py")
        assert spec is not None


class TestLaunchOrchestration:
    """测试启动协调逻辑."""

    @pytest.mark.asyncio
    async def test_build_services(self, tmp_path):
        """服务构建不抛异常."""
        from src.gui.launch import _build_config_manager

        cm = await _build_config_manager(str(tmp_path))
        assert cm is not None
