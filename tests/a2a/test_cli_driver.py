from __future__ import annotations

import asyncio
import os

import pytest

from src.a2a.cli_driver import CLIDriver, DriverConfig, DriverResult


class TestDriverConfig:
    """DriverConfig data model tests."""

    def test_create_default(self):
        cfg = DriverConfig(name="claude", command="claude-internal")
        assert cfg.name == "claude"
        assert cfg.command == "claude-internal"
        assert cfg.default_timeout_seconds == 300.0

    def test_custom_timeout(self):
        cfg = DriverConfig(name="codex", command="codex", default_timeout_seconds=600.0)
        assert cfg.default_timeout_seconds == 600.0

    def test_is_frozen(self):
        cfg = DriverConfig(name="c", command="x")
        with pytest.raises(Exception):
            cfg.name = "other"  # type: ignore


class TestDriverResult:
    """DriverResult data model tests."""

    def test_create_success(self):
        result = DriverResult(
            driver_name="claude",
            task_id="t1",
            exit_code=0,
            stdout="hello world",
            stderr="",
            timed_out=False,
            elapsed_seconds=12.5,
        )
        assert result.exit_code == 0
        assert result.stdout == "hello world"
        assert result.timed_out is False

    def test_create_timeout(self):
        result = DriverResult(
            driver_name="claude",
            task_id="t1",
            exit_code=-1,
            stdout="partial output",
            stderr="",
            timed_out=True,
            elapsed_seconds=300.0,
        )
        assert result.timed_out is True
        assert result.exit_code == -1

    def test_is_frozen(self):
        result = DriverResult(
            driver_name="c", task_id="t", exit_code=0,
            stdout="", stderr="", timed_out=False, elapsed_seconds=1.0,
        )
        with pytest.raises(Exception):
            result.exit_code = 5  # type: ignore


class TestCLIDriver:
    """CLIDriver subprocess management tests."""

    @pytest.fixture
    def driver(self):
        cfg = DriverConfig(name="test", command="")
        return CLIDriver(cfg)

    def test_create_driver(self, driver):
        assert driver.config.name == "test"
        assert driver.config.default_timeout_seconds == 300.0

    @pytest.mark.asyncio
    async def test_launch_simple_command(self, driver):
        """Start a simple echo command to verify basic flow."""
        echo_driver = CLIDriver(DriverConfig(
            name="echo",
            command="python",
            default_timeout_seconds=30.0,
        ))
        result = await echo_driver.launch(
            task_id="t1",
            prompt="hello",
            workspace_root=os.getcwd(),
        )
        assert result.task_id == "t1"
        assert result.driver_name == "echo"
        assert result.timed_out is False
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_launch_echo_output(self, driver):
        """Verify stdout capture."""
        echo_driver = CLIDriver(DriverConfig(
            name="echo",
            command="python",
            default_timeout_seconds=30.0,
        ))
        result = await echo_driver.launch(
            task_id="t2",
            prompt="hello_stdout",
            workspace_root=os.getcwd(),
        )
        assert "hello_stdout" in result.stdout

    @pytest.mark.asyncio
    async def test_launch_timeout(self, driver):
        """Timeout tasks should be correctly marked as timed_out."""
        sleep_driver = CLIDriver(DriverConfig(
            name="sleep",
            command="python",
            default_timeout_seconds=0.5,
        ))
        result = await sleep_driver.launch(
            task_id="t3",
            prompt="sleep_10",
            timeout_seconds=0.3,
            workspace_root=os.getcwd(),
        )
        assert result.timed_out is True

    @pytest.mark.asyncio
    async def test_launch_error_exit_code(self, driver):
        """Non-zero exit code tasks."""
        fail_driver = CLIDriver(DriverConfig(
            name="fail",
            command="python",
            default_timeout_seconds=30.0,
        ))
        result = await fail_driver.launch(
            task_id="t4",
            prompt="exit_1",
            workspace_root=os.getcwd(),
        )
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_launch_elapsed_time(self, driver):
        """Verify elapsed_seconds is correctly recorded."""
        echo_driver = CLIDriver(DriverConfig(
            name="echo",
            command="python",
            default_timeout_seconds=30.0,
        ))
        result = await echo_driver.launch(
            task_id="t5",
            prompt="hi",
            workspace_root=os.getcwd(),
        )
        assert result.elapsed_seconds > 0

    @pytest.mark.asyncio
    async def test_custom_timeout_overrides_default(self, driver):
        """Passing timeout_seconds should override config default."""
        echo_driver = CLIDriver(DriverConfig(
            name="echo",
            command="python",
            default_timeout_seconds=1.0,
        ))
        result = await echo_driver.launch(
            task_id="t6",
            prompt="hi",
            workspace_root=os.getcwd(),
            timeout_seconds=60.0,
        )
        assert result.timed_out is False
        assert result.elapsed_seconds < 5.0
