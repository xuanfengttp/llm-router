"""LLM Router FastAPI 后端入口."""
from __future__ import annotations

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """初始化/清理服务."""
    from src.gui.launch import _get_data_dir, _build_config_manager, _get_settings_store
    from src.network.probe import LatencyProbe

    data_dir = _get_data_dir()
    app.state.config_manager = await _build_config_manager(data_dir)
    app.state.settings_store = _get_settings_store(data_dir)
    app.state.network_probe = LatencyProbe(timeout_seconds=10.0)

    yield

    await app.state.config_manager._store.close()


app = FastAPI(title="LLM Router API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 以下 router 将在 Task 2-4 中创建后取消注释
# app.include_router(config_router, prefix="/api")
# app.include_router(dashboard_router, prefix="/api")
# app.include_router(tasks_router, prefix="/api")
# app.include_router(settings_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
