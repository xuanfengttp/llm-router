"""A2ADriver — 通过 A2AClient HTTP/JSON-RPC 调用远程 A2A agent 的轮询包装器。"""

import asyncio
import time

from src.a2a.cli_driver import DriverConfig, DriverResult


# A2AClient 可能尚未创建；测试中通过 mock 注入，生产环境中 import 后即可使用。
try:
    from src.a2a.http_client import A2AClient  # noqa: F401
except ImportError:
    A2AClient = None  # type: ignore[assignment]


class A2ADriver:
    """通过 HTTP/JSON-RPC 轮询远程 A2A agent 并暴露与 CLIDriver 一致的 launch() 接口。"""

    def __init__(
        self,
        config: DriverConfig,
        base_url: str,
        poll_interval: float = 2.0,
    ) -> None:
        self.config = config
        self.base_url = base_url
        self.poll_interval = poll_interval

    async def launch(
        self,
        task_id: str,
        prompt: str,
        workspace_root: str,  # 保留以兼容 CLIDriver 接口，A2A 无需此参数
        timeout_seconds: float | None = None,
        max_output_bytes: int = 50_000,
    ) -> DriverResult:
        timeout = timeout_seconds if timeout_seconds is not None else self.config.default_timeout_seconds

        # 这里 A2AClient 在生产中为真实类，测试中为 mock；lint 告警可忽略
        client = A2AClient(self.base_url)  # type: ignore[misc]

        t0 = time.monotonic()
        await client.send_task(prompt, task_id)

        stdout = ""
        stderr = ""

        while True:
            elapsed = time.monotonic() - t0

            task_resp = await client.get_task(task_id)

            task_data = _extract_task(task_resp)
            if task_data is None:
                # 格式异常，短暂等待后重试
                if elapsed >= timeout:
                    return DriverResult(
                        driver_name=self.config.name,
                        task_id=task_id,
                        exit_code=-1,
                        stdout=stdout,
                        stderr=stderr,
                        timed_out=True,
                        elapsed_seconds=round(elapsed, 3),
                    )
                await asyncio.sleep(self.poll_interval)
                continue

            status: str = task_data.get("status", "")

            # 持续收集可能的中间输出
            artifact = task_data.get("artifact") or {}
            parts = artifact.get("parts") or []
            for part in parts:
                text = part.get("text", "")
                if text:
                    stdout = text

            if status == "completed":
                stdout = _truncate(stdout, max_output_bytes)
                return DriverResult(
                    driver_name=self.config.name,
                    task_id=task_id,
                    exit_code=0,
                    stdout=stdout,
                    stderr="",
                    timed_out=False,
                    elapsed_seconds=round(elapsed, 3),
                )

            if status == "failed":
                msg_block = task_data.get("statusMessage") or {}
                inner_msg = msg_block.get("message") or {}
                stderr = inner_msg.get("text", "")
                return DriverResult(
                    driver_name=self.config.name,
                    task_id=task_id,
                    exit_code=1,
                    stdout=stdout,
                    stderr=stderr,
                    timed_out=False,
                    elapsed_seconds=round(elapsed, 3),
                )

            if status == "cancelled":
                return DriverResult(
                    driver_name=self.config.name,
                    task_id=task_id,
                    exit_code=0,
                    stdout=_truncate(stdout, max_output_bytes),
                    stderr="",
                    timed_out=True,
                    elapsed_seconds=round(elapsed, 3),
                )

            # submitted / working / 其他中间状态
            if elapsed >= timeout:
                await client.cancel_task(task_id)
                return DriverResult(
                    driver_name=self.config.name,
                    task_id=task_id,
                    exit_code=-1,
                    stdout=_truncate(stdout, max_output_bytes),
                    stderr=stderr,
                    timed_out=True,
                    elapsed_seconds=round(elapsed, 3),
                )

            await asyncio.sleep(self.poll_interval)


def _extract_task(response: dict) -> dict | None:
    """从 A2A JSON-RPC 响应中提取 task 对象。"""
    if not isinstance(response, dict):
        return None
    result = response.get("result")
    if not isinstance(result, dict):
        return None
    task = result.get("task")
    if not isinstance(task, dict):
        return None
    return task


def _truncate(text: str, max_bytes: int) -> str:
    """将文本截断到 max_bytes 字节（UTF-8）。"""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    # 截断到 max_bytes 并解码，忽略末尾可能不完整的 UTF-8 序列
    return encoded[:max_bytes].decode("utf-8", errors="ignore")
