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


def _get_data_dir() -> str:
    """获取数据目录，与 src.gui.launch._get_data_dir 逻辑一致."""
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path.cwd()
    data_dir = exe_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)


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
    settings_path = Path(_get_data_dir()) / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(store, indent=2, ensure_ascii=False))
    # 注入 dispatcher / route_engine
    if hasattr(request.app.state, 'dispatcher') and request.app.state.dispatcher:
        request.app.state.dispatcher.latency_redline_ms = store.get("latency_redline_ms", 5000)
        request.app.state.dispatcher.predictability_threshold = store.get("predictability_threshold", 0.3)
    return SettingsOut(**{**SETTINGS_DEFAULTS, **store})
