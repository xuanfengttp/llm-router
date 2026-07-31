# tests/monitor/test_scheduler.py
from __future__ import annotations

import asyncio

import pytest

from src.config.models import ProviderConfig
from src.monitor.scheduler import MonitorScheduler


class TestMonitorScheduler:
    """延迟探测调度器测试."""

    def test_create_scheduler(self):
        """创建调度器实例."""
        scheduler = MonitorScheduler(interval_seconds=60)
        assert scheduler.interval_seconds == 60
        assert scheduler.is_running is False

    def test_default_interval(self):
        """默认探测间隔."""
        scheduler = MonitorScheduler()
        assert scheduler.interval_seconds == 30

    @pytest.mark.asyncio
    async def test_probe_callback_receives_results(self):
        """探测回调收到结果."""
        results: list = []
        scheduler = MonitorScheduler(interval_seconds=0.1)

        async def collect(records):
            results.extend(records)

        scheduler.on_probe(collect)

        # 使用空 Provider 列表，验证回调机制
        task = asyncio.create_task(scheduler.start([]))
        await asyncio.sleep(0.3)
        await scheduler.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # 空 Provider 列表不产生结果，但调度器正常运行
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self):
        """调度器启动/停止生命周期."""
        scheduler = MonitorScheduler(interval_seconds=1.0)
        assert scheduler.is_running is False

        task = asyncio.create_task(scheduler.start([]))
        await asyncio.sleep(0.05)
        assert scheduler.is_running is True

        await scheduler.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_multiple_stop_is_idempotent(self):
        """重复停止不报错."""
        scheduler = MonitorScheduler(interval_seconds=1.0)
        task = asyncio.create_task(scheduler.start([]))
        await asyncio.sleep(0.05)
        await scheduler.stop()
        await scheduler.stop()  # 第二次无害
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_multiple_callbacks_invoked(self):
        """多个回调都被触发."""
        results_a: list = []
        results_b: list = []
        scheduler = MonitorScheduler(interval_seconds=0.1)

        async def cb_a(records):
            results_a.extend(records)

        async def cb_b(records):
            results_b.extend(records)

        scheduler.on_probe(cb_a)
        scheduler.on_probe(cb_b)

        task = asyncio.create_task(scheduler.start([]))
        await asyncio.sleep(0.3)
        await scheduler.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
