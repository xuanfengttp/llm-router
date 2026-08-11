"""LLM Router FastAPI 后端入口."""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 将项目根目录加入 sys.path，使 src.config.* / src.network.* 等导入解析正常工作
# PyInstaller (frozen) vs 开发模式路径处理
if getattr(sys, 'frozen', False):
    # PyInstaller --onefile: sys._MEIPASS 是临时解压目录，包含了 --add-data 内容
    _bundle_dir = str(Path(sys._MEIPASS))
    if _bundle_dir not in sys.path:
        sys.path.insert(0, _bundle_dir)
    # src.api.* 在 _MEIPASS/backend/src/api/ 下，需额外加 backend/ 到 sys.path
    _backend_dir = str(Path(sys._MEIPASS) / "backend")
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)
else:
    # Path(__file__) = backend/src/server.py → .parent.parent.parent = 项目根目录
    _project_root = str(Path(__file__).parent.parent.parent.resolve())
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    # 将 backend 根目录加入 sys.path，使 src.api.* 导入解析正常工作
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

    # 配置日志：同时输出到 stdout（被 Tauri 捕获到 llm-router.log）和 data 目录下的日志文件
    log_dir = Path(data_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "server.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 移除已有的 handler，避免重复添加
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    # 文件 handler
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root_logger.addHandler(file_handler)

    # 控制台 handler（stdout，会被 Tauri 捕获追加到 llm-router.log）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root_logger.addHandler(console_handler)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=19876)
