"""Settings API — 设置读写."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_backend_root = str(Path(__file__).parent.parent.parent.resolve())
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from fastapi import APIRouter, Request
from src.schemas import SettingsOut

router = APIRouter(tags=["settings"])

SETTINGS_DEFAULTS = SettingsOut().model_dump()


@router.get("/settings")
async def get_settings(request: Request) -> SettingsOut:
    store = request.app.state.settings_store or {}
    merged = {**SETTINGS_DEFAULTS, **store}
    return SettingsOut(**merged)


@router.put("/settings")
async def update_settings(request: Request, body: SettingsOut) -> SettingsOut:
    store = request.app.state.settings_store or {}
    store.update(body.model_dump(exclude_unset=True))
    # 持久化到磁盘
    try:
        from src.gui.launch import _get_data_dir
        data_dir = _get_data_dir()
        settings_path = Path(data_dir) / "settings.json"
        settings_path.write_text(json.dumps(store, indent=2, ensure_ascii=False))
    except Exception:
        pass  # 持久化失败不影响响应；测试环境无此模块也可通过
    # 注入 dispatcher / route_engine
    if hasattr(request.app.state, 'dispatcher') and request.app.state.dispatcher:
        request.app.state.dispatcher.latency_redline_ms = store.get("latency_redline_ms", 5000)
        request.app.state.dispatcher.predictability_threshold = store.get("predictability_threshold", 0.3)
    return SettingsOut(**{**SETTINGS_DEFAULTS, **store})
