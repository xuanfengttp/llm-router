# src/config/manager.py
from __future__ import annotations

from src.config.models import (
    ModelConfig,
    ProviderConfig,
    ProviderStatus,
)
from src.config.store import ConfigStore


class ConfigManager:
    """配置管理业务逻辑层，统筹 YAML 持久化 + SQLite 运行时状态."""

    def __init__(self, store: ConfigStore) -> None:
        self._store = store
        self._providers: list[ProviderConfig] = self._store.load_providers()

    # ── Provider CRUD ──────────────────────────────

    async def add_provider(
        self,
        name: str,
        endpoint: str,
        api_key: str | None = None,
    ) -> ProviderConfig:
        """添加新 Provider."""
        if any(p.name == name for p in self._providers):
            raise ValueError(f"Provider '{name}' 已存在")
        provider = ProviderConfig(name=name, endpoint=endpoint, api_key=api_key)
        self._providers.append(provider)
        self._store.save_providers(self._providers)
        return provider

    async def remove_provider(self, name: str) -> None:
        """删除 Provider 及其所有模型."""
        if not any(p.name == name for p in self._providers):
            raise ValueError(f"Provider '{name}' 不存在")
        self._providers = [p for p in self._providers if p.name != name]
        self._store.save_providers(self._providers)

    async def get_provider(self, name: str) -> ProviderConfig | None:
        """获取单个 Provider 配置."""
        for p in self._providers:
            if p.name == name:
                return p
        return None

    async def list_providers(self) -> list[ProviderConfig]:
        """列出所有 Provider (返回副本)."""
        return list(self._providers)

    async def update_provider_api_key(self, name: str, api_key: str) -> ProviderConfig:
        """更新 Provider 的 API Key."""
        for i, p in enumerate(self._providers):
            if p.name == name:
                updated = ProviderConfig(
                    name=p.name,
                    endpoint=p.endpoint,
                    api_key=api_key,
                    models=p.models,
                    status=p.status,
                )
                self._providers[i] = updated
                self._store.save_providers(self._providers)
                return updated
        raise ValueError(f"Provider '{name}' 不存在")

    # ── Model CRUD ─────────────────────────────────

    async def add_model(
        self, provider_name: str, model: ModelConfig
    ) -> ProviderConfig:
        """向 Provider 添加模型."""
        for i, p in enumerate(self._providers):
            if p.name == provider_name:
                updated = p.add_model(model)
                self._providers[i] = updated
                self._store.save_providers(self._providers)
                return updated
        raise ValueError(f"Provider '{provider_name}' 不存在")

    async def remove_model(
        self, provider_name: str, model_name: str
    ) -> ProviderConfig:
        """从 Provider 移除模型."""
        for i, p in enumerate(self._providers):
            if p.name == provider_name:
                updated = p.remove_model(model_name)
                self._providers[i] = updated
                self._store.save_providers(self._providers)
                return updated
        raise ValueError(f"Provider '{provider_name}' 不存在")

    async def list_models(self, provider_name: str) -> list[ModelConfig]:
        """列出 Provider 下的所有模型."""
        provider = await self.get_provider(provider_name)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' 不存在")
        return list(provider.models)

    # ── 运行时状态 ──────────────────────────────────

    async def update_status(
        self, provider_name: str, status: ProviderStatus
    ) -> None:
        """更新 Provider 连通状态 (写入 SQLite)."""
        # 同时更新内存中的状态
        for i, p in enumerate(self._providers):
            if p.name == provider_name:
                self._providers[i] = p.with_status(status)
                break
        await self._store.update_provider_status(provider_name, status)

    async def get_status(self, provider_name: str) -> ProviderStatus:
        """获取 Provider 连通状态."""
        return await self._store.get_provider_status(provider_name)

    async def get_all_statuses(self) -> dict[str, str]:
        """获取所有 Provider 的状态."""
        return await self._store.get_all_provider_statuses()
