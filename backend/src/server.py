"""LLM Router FastAPI 后端入口."""
from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 将项目根目录加入 sys.path，使 src.config.* / src.network.* 等导入解析正常工作
# Path(__file__) = backend/src/server.py → .parent.parent.parent = 项目根目录
_project_root = str(Path(__file__).parent.parent.parent.resolve())
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 将 backend 根目录加入 sys.path，使 src.api.* 导入解析正常工 作
# Path(__file__) = backend/src/server.py → .parent.parent = backend/
_backend_root = str(Path(__file__).parent.parent.resolve())
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)


from src.api.config_api import router as config_router
from src.api.dashboard_api import router as dashboard_router
from src.api.tasks_api import router as tasks_router
from src.api.settings_api import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """初始化/清理服务."""
    from backend.src.bootstrap import (
        get_data_dir,
        build_config_manager,
        get_settings_store,
    )
    from src.network.probe import LatencyProbe
    from src.monitor.scheduler import MonitorScheduler

    data_dir = get_data_dir()
    app.state.config_manager = await build_config_manager(data_dir)
    app.state.settings_store = get_settings_store(data_dir)
    app.state.network_probe = LatencyProbe(timeout_seconds=10.0)

    # 启动 MonitorScheduler 后台探测
    scheduler = MonitorScheduler(interval_seconds=30)
    app.state.monitor_scheduler = scheduler

    async def on_probe_write(records):
        await app.state.config_manager._store.save_latency_records(records)

    from src.api.dashboard_api import broadcast_probe_result

    async def on_probe_broadcast(records):
        for r in records:
            if r.latency_ms > 0 or not r.success:
                await broadcast_probe_result(
                    r.provider, r.model, r.latency_ms, r.success, r.timestamp,
                )

    scheduler.on_probe(on_probe_write)
    scheduler.on_probe(on_probe_broadcast)

    async def get_providers():
        return await app.state.config_manager.list_providers()

    task = asyncio.create_task(scheduler.start(get_providers))
    app.state._scheduler_task = task

    yield

    # 停止 MonitorScheduler
    await scheduler.stop()
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await app.state.config_manager._store.close()


app = FastAPI(title="LLM Router API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# API 路由注册
app.include_router(config_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
