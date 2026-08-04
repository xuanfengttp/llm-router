"""Provider & Model CRUD REST API."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException

# Path(__file__) = backend/src/api/config_api.py → .parent.parent.parent = backend/
_backend_root = str(Path(__file__).parent.parent.parent.resolve())
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from src.config.models import ModelConfig, ModelDeployment  # noqa: E402
from src.schemas import ProviderConfigOut, ProviderCreate, ModelCreate, ApiKeyUpdate  # noqa: E402

router = APIRouter(tags=["config"])


def _provider_to_out(p) -> ProviderConfigOut:
    return ProviderConfigOut(
        name=p.name, endpoint=p.endpoint, status=p.status.value,
        models=[{
            "name": m.name, "deployment": str(m.deployment),
            "context_window": m.context_window,
            "cost_input_1k": m.cost_input_1k,
            "cost_output_1k": m.cost_output_1k,
            "tags": m.tags,
        } for m in p.models],
    )


@router.get("/providers")
async def list_providers(request: Request) -> list[ProviderConfigOut]:
    providers = await request.app.state.config_manager.list_providers()
    return [_provider_to_out(p) for p in providers]


@router.post("/providers")
async def create_provider(request: Request, body: ProviderCreate) -> ProviderConfigOut:
    p = await request.app.state.config_manager.add_provider(body.name, body.endpoint, body.api_key)
    return _provider_to_out(p)


@router.delete("/providers/{name}", status_code=204)
async def delete_provider(request: Request, name: str):
    try:
        await request.app.state.config_manager.remove_provider(name)
    except ValueError:
        raise HTTPException(404, f"Provider '{name}' not found")


@router.put("/providers/{name}/api-key")
async def update_api_key(request: Request, name: str, body: ApiKeyUpdate) -> ProviderConfigOut:
    try:
        p = await request.app.state.config_manager.update_provider_api_key(name, body.api_key)
        return _provider_to_out(p)
    except ValueError:
        raise HTTPException(404, f"Provider '{name}' not found")


@router.post("/providers/{name}/models")
async def add_model(request: Request, name: str, body: ModelCreate) -> ProviderConfigOut:
    m = ModelConfig(
        name=body.name, deployment=ModelDeployment(body.deployment),
        context_window=body.context_window,
        cost_input_1k=body.cost_input_1k, cost_output_1k=body.cost_output_1k,
    )
    try:
        p = await request.app.state.config_manager.add_model(name, m)
        return _provider_to_out(p)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/providers/{name}/models/{model_name}")
async def remove_model(request: Request, name: str, model_name: str) -> ProviderConfigOut:
    try:
        p = await request.app.state.config_manager.remove_model(name, model_name)
        return _provider_to_out(p)
    except ValueError as e:
        raise HTTPException(404 if "不存在" in str(e) else 400, str(e))
