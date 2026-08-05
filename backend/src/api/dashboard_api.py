"""Dashboard: 探测触发 + 延迟查询 + WebSocket 实时推送."""
from __future__ import annotations

import sys
from pathlib import Path

import asyncio
import time
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

# Path(__file__) = backend/src/api/dashboard_api.py → .parent.parent.parent = backend/
_backend_root = str(Path(__file__).parent.parent.parent.resolve())
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from src.schemas import DashboardStatusOut, ProbeRequest, ProbeResultOut, LatencyRecordOut  # noqa: E402
from src.config.models import LatencyRecord  # noqa: E402

router = APIRouter(tags=["dashboard"])
_active_subscriptions: dict[WebSocket, dict] = {}


async def broadcast_probe_result(
    provider: str, model: str,
    latency_ms: float, success: bool, timestamp: str,
) -> None:
    """向订阅了此 provider+model 的 WebSocket 客户端推送探测结果."""
    dead: list[WebSocket] = []
    for ws, sub in _active_subscriptions.items():
        provider_models = sub.get(provider, [])
        if model in provider_models:
            try:
                await ws.send_json({
                    "type": "probe_result",
                    "provider": provider,
                    "model": model,
                    "latency_ms": latency_ms,
                    "success": success,
                    "timestamp": timestamp,
                })
            except Exception:
                dead.append(ws)
    for ws in dead:
        _active_subscriptions.pop(ws, None)


@router.get("/dashboard/status")
async def get_status(request: Request) -> DashboardStatusOut:
    providers = await request.app.state.config_manager.list_providers()
    return DashboardStatusOut(
        providers=[{
            "name": p.name, "endpoint": p.endpoint, "status": p.status.value,
            "models": [{"name": m.name, "deployment": str(m.deployment),
                        "context_window": m.context_window,
                        "cost_input_1k": m.cost_input_1k,
                        "cost_output_1k": m.cost_output_1k,
                        "tags": m.tags} for m in p.models],
        } for p in providers],
        selected_models={},
    )


@router.post("/dashboard/probe")
async def trigger_probe(request: Request, body: ProbeRequest) -> list[ProbeResultOut]:
    probe = request.app.state.network_probe
    providers = await request.app.state.config_manager.list_providers()
    provider_map = {p.name: p for p in providers}
    results: list[ProbeResultOut] = []

    async def _probe_one(pname, mname):
        p = provider_map.get(pname)
        if p is None:
            return None
        result = await probe.ping_chat_endpoint(pname, mname, p.endpoint, p.api_key)
        rec = ProbeResultOut(
            provider=pname, model=mname, success=result.success,
            latency_ms=result.latency_ms, error=result.error,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        # 持久化
        if result.success and result.latency_ms is not None:
            await request.app.state.config_manager._store.record_latency(
                pname, mname, result.latency_ms)
            # 同时写入 latency_timeseries 并广播 WebSocket
            await request.app.state.config_manager._store.save_latency_records([
                LatencyRecord(provider=pname, model=mname,
                              latency_ms=result.latency_ms, success=True),
            ])
            await broadcast_probe_result(
                pname, mname, result.latency_ms, True, rec.timestamp)
        return rec

    tasks = [_probe_one(pn, mn) for pn in body.providers for mn in body.models]
    raw = await asyncio.gather(*tasks)
    results = [r for r in raw if r is not None]
    return results


@router.get("/dashboard/latency")
async def get_latency(request: Request, provider: str, model: str, limit: int = 300) -> list[LatencyRecordOut]:
    store = request.app.state.config_manager._store
    rows = await store.get_latency_merged(provider, model, limit=limit)
    return [LatencyRecordOut(**r) for r in rows]


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    _active_subscriptions[websocket] = {}
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "subscribe":
                _active_subscriptions[websocket] = data.get("providers", {})
    except WebSocketDisconnect:
        _active_subscriptions.pop(websocket, None)
