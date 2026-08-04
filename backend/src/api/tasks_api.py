"""Tasks API — 任务 CRUD 端点."""
from __future__ import annotations

import sys
from pathlib import Path

_backend_root = str(Path(__file__).parent.parent.parent.resolve())
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from fastapi import APIRouter, Request, HTTPException
from src.schemas import AgentTaskCreate, AgentTaskOut

router = APIRouter(tags=["tasks"])


@router.get("/tasks")
async def list_tasks(request: Request, limit: int = 50, offset: int = 0):
    if not hasattr(request.app.state, 'task_queue') or not request.app.state.task_queue:
        return []
    return await request.app.state.task_queue.list_all(limit=limit, offset=offset)


@router.post("/tasks")
async def create_task(request: Request, body: AgentTaskCreate):
    if not hasattr(request.app.state, 'controller') or not request.app.state.controller:
        raise HTTPException(503, "TaskController not initialized")
    task = await request.app.state.controller.submit(prompt=body.prompt, target_model=body.target_model or "")
    return {"task_id": task.task_id, "status": task.status.value}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(request: Request, task_id: str):
    if not hasattr(request.app.state, 'controller') or not request.app.state.controller:
        raise HTTPException(503, "TaskController not initialized")
    task = await request.app.state.controller.cancel(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return {"task_id": task.task_id, "status": task.status.value}


@router.post("/tasks/{task_id}/retry")
async def retry_task(request: Request, task_id: str):
    if not hasattr(request.app.state, 'controller') or not request.app.state.controller:
        raise HTTPException(503, "TaskController not initialized")
    task = await request.app.state.controller.retry_standby(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return {"task_id": task.task_id, "status": task.status.value}
