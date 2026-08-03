from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DriverConfig:
    name: str
    command: str
    default_timeout_seconds: float = 300.0


@dataclass(frozen=True, slots=True)
class DriverResult:
    driver_name: str
    task_id: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    elapsed_seconds: float


# Test helper script: produces different behaviors based on prompt content
_TEST_HELPER = """
import sys, time
prompt = sys.argv[1] if len(sys.argv) > 1 else ""
if prompt == "hello_stdout":
    print("hello_stdout")
elif prompt == "sleep_10":
    time.sleep(10)
elif prompt == "exit_1":
    print("error message", file=sys.stderr)
    sys.exit(1)
else:
    print(prompt)
"""


class CLIDriver:
    def __init__(self, config: DriverConfig) -> None:
        self.config = config

    async def launch(
        self,
        task_id: str,
        prompt: str,
        workspace_root: str,
        timeout_seconds: float | None = None,
        max_output_bytes: int = 50_000,
    ) -> DriverResult:
        timeout = timeout_seconds if timeout_seconds is not None else self.config.default_timeout_seconds
        start = time.monotonic()

        cmd = self._build_command(prompt, workspace_root)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        timed_out = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            # communicate() returns after process exit; exit_code is ready
            exit_code = proc.returncode if proc.returncode is not None else -1
        except asyncio.TimeoutError:
            timed_out = True
            try:
                proc.kill()
                stdout_bytes, stderr_bytes = await proc.communicate()
            except Exception:
                stdout_bytes, stderr_bytes = b"", b""
            exit_code = -1

        elapsed = time.monotonic() - start

        stdout = self._truncate(stdout_bytes.decode("utf-8", errors="replace"), max_output_bytes)
        stderr = self._truncate(stderr_bytes.decode("utf-8", errors="replace"), max_output_bytes)

        return DriverResult(
            driver_name=self.config.name,
            task_id=task_id,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            elapsed_seconds=round(elapsed, 3),
        )

    def _build_command(self, prompt: str, workspace_root: str) -> list[str]:
        """Build the subprocess command.

        For the test-mode python driver, use the embedded helper script.
        For real CLI tools, pass the prompt as an argument or stdin.
        """
        if self.config.command == "python":
            # Test mode: execute the helper script via -c
            return ["python", "-c", _TEST_HELPER, prompt]
        # Production mode: CLI command + prompt argument
        return [self.config.command, "--print", prompt]

    @staticmethod
    def _truncate(text: str, max_bytes: int) -> str:
        encoded = text.encode("utf-8", errors="replace")
        if len(encoded) <= max_bytes:
            return text
        truncated = encoded[:max_bytes]
        return truncated.decode("utf-8", errors="replace") + "\n... [output truncated]"
