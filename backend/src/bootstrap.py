"""LLM Router 后端启动引导工具函数."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


async def build_config_manager(data_dir: str) -> Any:
    """构建 ConfigManager."""
    from src.config.crypto import generate_key, KeyCipher
    from src.config.manager import ConfigManager
    from src.config.store import ConfigStore

    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    config_path = data_path / "providers.yaml"
    key = generate_key()
    cipher = KeyCipher(key)
    store = ConfigStore(
        config_path=config_path,
        cipher=cipher,
        db_path=data_path / "router_state.db",
    )
    await store.init_db()
    return ConfigManager(store)


def get_data_dir() -> str:
    """获取数据目录（创建于用户目录下）."""
    home = Path.home()
    data_dir = home / ".llm_router"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)


def get_settings_store(data_dir: str) -> dict:
    """从磁盘加载 settings.json，不存在则返回空字典."""
    settings_path = Path(data_dir) / "settings.json"
    if settings_path.exists():
        return json.loads(settings_path.read_text(encoding="utf-8"))
    return {}
