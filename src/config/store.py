# src/config/store.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite
import yaml

from src.config.crypto import KeyCipher
from src.config.models import (
    ModelConfig,
    ModelDeployment,
    ProviderConfig,
    ProviderStatus,
)


class ConfigStore:
    """配置持久化存储: YAML 存配置 + SQLite 存运行时状态."""

    def __init__(
        self,
        config_path: Path,
        cipher: KeyCipher,
        db_path: Path | None = None,
    ) -> None:
        self.config_path = config_path
        self.cipher = cipher
        self.db_path = db_path or (config_path.parent / "router_state.db")
        self._conn: aiosqlite.Connection | None = None

    # ── YAML 配置读写 ──────────────────────────────

    def save_providers(self, providers: list[ProviderConfig]) -> None:
        """保存 Provider 列表到 YAML 配置文件，API Key 加密存储."""
        raw: list[dict[str, Any]] = []
        for p in providers:
            provider_dict: dict[str, Any] = {
                "name": p.name,
                "endpoint": p.endpoint,
                "api_key": self.cipher.encrypt_none(p.api_key),
                "models": [
                    {
                        "name": m.name,
                        "deployment": str(m.deployment),
                        "context_window": m.context_window,
                        "cost_input_1k": m.cost_input_1k,
                        "cost_output_1k": m.cost_output_1k,
                        "tags": m.tags,
                    }
                    for m in p.models
                ],
            }
            raw.append(provider_dict)

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            yaml.dump({"providers": raw}, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )

    def load_providers(self) -> list[ProviderConfig]:
        """从 YAML 配置文件加载 Provider 列表，API Key 解密."""
        if not self.config_path.exists():
            return []

        raw_text = self.config_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            return []

        data = yaml.safe_load(raw_text)
        if not data or "providers" not in data:
            return []

        providers: list[ProviderConfig] = []
        for p_raw in data["providers"]:
            api_key_encrypted = p_raw.get("api_key")
            models: list[ModelConfig] = []
            for m_raw in p_raw.get("models", []):
                models.append(
                    ModelConfig(
                        name=m_raw["name"],
                        deployment=ModelDeployment(m_raw.get("deployment", "cloud")),
                        context_window=m_raw.get("context_window", 4096),
                        cost_input_1k=m_raw.get("cost_input_1k", 0.0),
                        cost_output_1k=m_raw.get("cost_output_1k", 0.0),
                        tags=m_raw.get("tags", []),
                    )
                )
            providers.append(
                ProviderConfig(
                    name=p_raw["name"],
                    endpoint=p_raw["endpoint"],
                    api_key=(
                        self.cipher.decrypt(api_key_encrypted)
                        if api_key_encrypted
                        else None
                    ),
                    models=models,
                )
            )
        return providers

    # ── SQLite 运行时状态 ───────────────────────────

    async def init_db(self) -> None:
        """初始化 SQLite 数据库及表结构."""
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS provider_status (
                provider_name TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS latency_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_latency_provider_model
                ON latency_history(provider, model, timestamp DESC);
        """)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def update_provider_status(
        self, provider_name: str, status: ProviderStatus
    ) -> None:
        """更新 Provider 连通状态."""
        await self._conn.execute(
            "INSERT OR REPLACE INTO provider_status (provider_name, status, updated_at) "
            "VALUES (?, ?, datetime('now'))",
            (provider_name, str(status)),
        )
        await self._conn.commit()

    async def get_provider_status(self, provider_name: str) -> ProviderStatus:
        """获取单个 Provider 的连通状态."""
        cursor = await self._conn.execute(
            "SELECT status FROM provider_status WHERE provider_name = ?",
            (provider_name,),
        )
        row = await cursor.fetchone()
        if row is None:
            return ProviderStatus.UNKNOWN
        return ProviderStatus(row["status"])

    async def get_all_provider_statuses(self) -> dict[str, str]:
        """获取所有 Provider 的状态映射."""
        cursor = await self._conn.execute("SELECT provider_name, status FROM provider_status")
        rows = await cursor.fetchall()
        return {row["provider_name"]: row["status"] for row in rows}

    async def record_latency(
        self, provider: str, model: str, latency_ms: float
    ) -> None:
        """记录一次延迟探测结果."""
        await self._conn.execute(
            "INSERT INTO latency_history (provider, model, latency_ms) VALUES (?, ?, ?)",
            (provider, model, latency_ms),
        )
        await self._conn.commit()

    async def get_latency_history(
        self, provider: str, model: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """获取指定模型的延迟历史记录."""
        cursor = await self._conn.execute(
            "SELECT provider, model, latency_ms, timestamp "
            "FROM latency_history "
            "WHERE provider = ? AND model = ? "
            "ORDER BY timestamp ASC "
            "LIMIT ?",
            (provider, model, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
