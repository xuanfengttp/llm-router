from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ModelDeployment(StrEnum):
    CLOUD = "cloud"
    LOCAL = "local"
    HYBRID = "hybrid"


class ProviderStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """单个模型的配置画像.

    Attributes:
        name: 模型名称，如 "gpt-4o", "claude-opus-5"
        deployment: 部署类型 (cloud/local/hybrid)
        context_window: 最大上下文窗口 token 数
        cost_input_1k: 每千输入 token 成本(美元)
        cost_output_1k: 每千输出 token 成本(美元)
        tags: 自由标签，用于策略匹配辅助
    """

    name: str
    deployment: ModelDeployment
    context_window: int = 4096
    cost_input_1k: float = 0.0
    cost_output_1k: float = 0.0
    tags: list[str] = field(default_factory=list, hash=False)


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """LLM Provider 配置.

    Attributes:
        name: Provider 唯一标识，如 "openai", "anthropic"
        endpoint: API 端点 URL
        api_key: API 密钥 (存储时加密，内存中明文)
        models: 该 Provider 下的模型列表
        status: 当前连通状态
    """

    name: str
    endpoint: str
    api_key: str | None = None
    models: list[ModelConfig] = field(default_factory=list, hash=False)
    status: ProviderStatus = ProviderStatus.UNKNOWN

    def add_model(self, model: ModelConfig) -> ProviderConfig:
        """返回添加模型后的新 ProviderConfig 实例 (不可变模式)."""
        if any(m.name == model.name for m in self.models):
            raise ValueError(f"模型 '{model.name}' 已存在于 Provider '{self.name}'")
        return ProviderConfig(
            name=self.name,
            endpoint=self.endpoint,
            api_key=self.api_key,
            models=[*self.models, model],
            status=self.status,
        )

    def remove_model(self, model_name: str) -> ProviderConfig:
        """返回删除模型后的新 ProviderConfig 实例."""
        if not any(m.name == model_name for m in self.models):
            raise ValueError(f"模型 '{model_name}' 不存在于 Provider '{self.name}'")
        return ProviderConfig(
            name=self.name,
            endpoint=self.endpoint,
            api_key=self.api_key,
            models=[m for m in self.models if m.name != model_name],
            status=self.status,
        )

    def with_status(self, status: ProviderStatus) -> ProviderConfig:
        """返回更新状态后的新 ProviderConfig 实例."""
        return ProviderConfig(
            name=self.name,
            endpoint=self.endpoint,
            api_key=self.api_key,
            models=self.models,
            status=status,
        )
