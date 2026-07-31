# src/monitor/scheduler.py
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from src.config.models import LatencyRecord, ProviderConfig
from src.network.probe import LatencyProbe

ProbeCallback = Callable[[list[LatencyRecord]], Awaitable[None]]


class MonitorScheduler:
    """定时延迟探测调度器.

    每 interval_seconds 秒对所有 Provider 执行连通性探测，
    结果通过回调通知，写入 timeseries 数据库。

    用法:
        scheduler = MonitorScheduler(interval_seconds=30)
        scheduler.on_probe(lambda records: store.save_latency_records(records))
        await scheduler.start(providers)
        # ... 运行中 ...
        await scheduler.stop()
    """

    def __init__(self, interval_seconds: float = 30) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._callbacks: list[ProbeCallback] = []
        self._probe = LatencyProbe(timeout_seconds=10.0)

    @property
    def is_running(self) -> bool:
        return self._running

    def on_probe(self, callback: ProbeCallback) -> None:
        """注册探测结果回调."""
        self._callbacks.append(callback)

    async def start(self, providers: list[ProviderConfig]) -> None:
        """启动定时探测循环."""
        self._running = True
        try:
            while self._running:
                if providers:
                    probe_results = await self._probe.probe_all(providers)
                    records = [
                        LatencyRecord(
                            provider=r.provider,
                            model=r.model,
                            latency_ms=r.latency_ms or 0.0,
                            success=r.success,
                            error=r.error,
                            timestamp=r.timestamp,
                        )
                        for r in probe_results
                    ]
                    for cb in self._callbacks:
                        try:
                            await cb(records)
                        except Exception:
                            pass  # 回调异常不影响调度循环

                await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    async def stop(self) -> None:
        """停止调度循环."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
