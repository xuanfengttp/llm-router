"""API JSON 响应模型 (Pydantic v2)."""
from __future__ import annotations

from pydantic import BaseModel


class ModelConfigOut(BaseModel):
    name: str
    deployment: str
    context_window: int
    cost_input_1k: float
    cost_output_1k: float
    tags: list[str] = []


class ProviderConfigOut(BaseModel):
    name: str
    endpoint: str
    status: str
    models: list[ModelConfigOut]


class ProviderCreate(BaseModel):
    name: str
    endpoint: str
    api_key: str | None = None


class ModelCreate(BaseModel):
    name: str
    deployment: str = "cloud"
    context_window: int = 128000
    cost_input_1k: float = 0.0
    cost_output_1k: float = 0.0


class ApiKeyUpdate(BaseModel):
    api_key: str


class ProbeResultOut(BaseModel):
    provider: str
    model: str
    success: bool
    latency_ms: float | None = None
    error: str | None = None
    timestamp: str


class LatencyRecordOut(BaseModel):
    provider: str
    model: str
    latency_ms: float
    timestamp: str
    success: bool = True


class DashboardStatusOut(BaseModel):
    providers: list[ProviderConfigOut]
    selected_models: dict[str, list[str]]


class ProbeRequest(BaseModel):
    providers: list[str]
    models: list[str]


class SettingsOut(BaseModel):
    strategy: str = "baseline"
    latency_redline_ms: int = 5000
    predictability_threshold: float = 0.3
    cycle_seconds: int = 30
    max_retries: int = 3
    night_start: int = 22
    night_end: int = 6
    weekend_all_day: bool = True
    allow_weekday_day: bool = False
    theme: str = "dark"
    language: str = "zh"
    data_dir: str = ""


class AgentTaskCreate(BaseModel):
    prompt: str
    target_model: str | None = None


class AgentTaskOut(BaseModel):
    task_id: str
    status: str
