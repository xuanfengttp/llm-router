"""A2ADriver 测试 — mock A2AClient，测试轮询包装器的 launch() 接口。"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.a2a.cli_driver import DriverConfig, DriverResult


# ---------------------------------------------------------------------------
# 辅助：构造 get_task 返回值的 mock
# ---------------------------------------------------------------------------

def _task_result(task_id: str, status: str, text: str = "", message_text: str = "") -> dict:
    """构造与 A2A JSON-RPC `get_task` 返回值结构兼容的 dict。"""
    result: dict = {
        "jsonrpc": "2.0",
        "result": {
            "task": {
                "id": task_id,
                "status": status,
            }
        },
    }
    if text:
        # 把整个文本放在一个 part 里
        result["result"]["task"]["artifact"] = {"parts": [{"text": text}]}
    if message_text:
        result["result"]["task"]["statusMessage"] = {"message": {"text": message_text}}
    return result


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------

class TestA2ADriverLaunch:
    """mock A2AClient，测试 A2ADriver.launch() 的各种路径。"""

    @pytest.fixture
    def driver_cls(self):
        """延迟导入 A2ADriver，确保 mock 先生效。"""
        from src.a2a.http_driver import A2ADriver
        return A2ADriver

    @pytest.fixture
    def config(self):
        return DriverConfig(name="remote-echo", command="", default_timeout_seconds=10.0)

    # ---- 成功路径 ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_launch_success(self, driver_cls, config):
        """send 后轮询 working→completed，得到正常输出。"""
        mock_client = AsyncMock()
        mock_client.get_task = AsyncMock(side_effect=[
            _task_result("t1", "working"),
            _task_result("t1", "completed", text="Hello, A2A!"),
        ])

        with patch("src.a2a.http_driver.A2AClient", return_value=mock_client):
            driver = driver_cls(config, base_url="http://localhost:8080")
            result = await driver.launch("t1", "say hello", "/tmp/ws")

        assert result.exit_code == 0
        assert result.stdout == "Hello, A2A!"
        assert result.timed_out is False
        assert result.driver_name == "remote-echo"
        assert result.task_id == "t1"
        mock_client.send_task.assert_awaited_once_with("say hello", "t1")
        assert mock_client.cancel_task.call_count == 0

    # ---- 失败路径 ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_launch_failure(self, driver_cls, config):
        """轮询至 failed 状态，返回非零 exit_code 和 stderr。"""
        mock_client = AsyncMock()
        mock_client.get_task = AsyncMock(side_effect=[
            _task_result("t2", "submitted"),
            _task_result("t2", "working"),
            _task_result("t2", "failed", message_text="something broke"),
        ])

        with patch("src.a2a.http_driver.A2AClient", return_value=mock_client):
            driver = driver_cls(config, base_url="http://localhost:8080")
            result = await driver.launch("t2", "bad prompt", "/tmp/ws")

        assert result.exit_code != 0
        assert "something broke" in result.stderr
        assert result.timed_out is False

    # ---- 取消路径 ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_launch_cancelled(self, driver_cls, config):
        """轮询至 cancelled 状态，标记 timed_out=True。"""
        mock_client = AsyncMock()
        mock_client.get_task = AsyncMock(side_effect=[
            _task_result("t3", "submitted"),
            _task_result("t3", "working"),
            _task_result("t3", "cancelled"),
        ])

        with patch("src.a2a.http_driver.A2AClient", return_value=mock_client):
            driver = driver_cls(config, base_url="http://localhost:8080")
            result = await driver.launch("t3", "long task", "/tmp/ws")

        assert result.timed_out is True
        # 被取消时仍尝试获取已有的输出文本
        assert isinstance(result.stdout, str)

    # ---- 超时路径 ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_launch_timeout(self, driver_cls, config):
        """永远 working，总耗时超过 timeout_seconds → timed_out=True, exit_code=-1。"""
        mock_client = AsyncMock()
        # get_task 永远返回 working
        mock_client.get_task = AsyncMock(
            return_value=_task_result("t4", "working", text="partial output")
        )

        with patch("src.a2a.http_driver.A2AClient", return_value=mock_client):
            driver = driver_cls(config, base_url="http://localhost:8080")
            result = await driver.launch("t4", "forever", "/tmp/ws", timeout_seconds=1.0)

        assert result.timed_out is True
        assert result.exit_code == -1
        assert result.stdout == "partial output"
        # 超时时应调用 cancel_task
        mock_client.cancel_task.assert_awaited_once_with("t4")

    # ---- 耗时记录 ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_elapsed_time(self, driver_cls, config):
        """elapsed_seconds 应在合理范围内。"""
        mock_client = AsyncMock()
        mock_client.get_task = AsyncMock(side_effect=[
            _task_result("t5", "submitted"),
            _task_result("t5", "working"),
            _task_result("t5", "completed", text="done"),
        ])

        with patch("src.a2a.http_driver.A2AClient", return_value=mock_client):
            driver = driver_cls(config, base_url="http://localhost:8080")
            result = await driver.launch("t5", "test", "/tmp/ws", timeout_seconds=30.0)

        assert result.elapsed_seconds > 0
        assert result.elapsed_seconds < 5.0  # mock 调用非常快

    # ---- 输出截断 ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_output_truncation(self, driver_cls, config):
        """超过 max_output_bytes 时输出应被截断。"""
        long_text = "x" * 2000
        mock_client = AsyncMock()
        mock_client.get_task = AsyncMock(side_effect=[
            _task_result("t6", "working"),
            _task_result("t6", "completed", text=long_text),
        ])

        with patch("src.a2a.http_driver.A2AClient", return_value=mock_client):
            driver = driver_cls(config, base_url="http://localhost:8080")
            result = await driver.launch("t6", "big output", "/tmp/ws", max_output_bytes=500)

        assert len(result.stdout) == 500
        assert result.exit_code == 0
        assert result.timed_out is False

    # ---- 轮询间隔验证 -----------------------------------------------------

    @pytest.mark.asyncio
    async def test_poll_interval_used(self, driver_cls, config):
        """验证实际轮询次数在预期范围内（使用 0.1s 间隔加速测试）。"""
        mock_client = AsyncMock()
        # 4 次 working 后 completed
        mock_client.get_task = AsyncMock(side_effect=[
            _task_result("t7", "submitted"),
            _task_result("t7", "working"),
            _task_result("t7", "working"),
            _task_result("t7", "working"),
            _task_result("t7", "completed", text="finally"),
        ])

        with patch("src.a2a.http_driver.A2AClient", return_value=mock_client):
            driver = driver_cls(config, base_url="http://localhost:8080", poll_interval=0.1)
            result = await driver.launch("t7", "poll", "/tmp/ws")

        assert result.exit_code == 0
        assert result.stdout == "finally"
        # 至少调用了 4-5 次 get_task (submitted + 3 x working + completed)
        assert mock_client.get_task.call_count >= 4
