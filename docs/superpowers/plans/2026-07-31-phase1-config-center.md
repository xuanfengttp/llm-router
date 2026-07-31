# Phase 1：连接配置与模型注册中心 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建 Provider/模型配置的 CRUD 管理、加密存储、连通性测试功能，作为整个 LLM Router 的数据基础层。

**架构：** 配置数据用 YAML 文件（可 Git 版本管理）+ SQLite 存储运行时状态。Python dataclass 建模 Provider/Model，加密存储 API Key。aiohttp 异步 HTTP 客户端做连通性探测和延迟测量。

**技术栈：** Python 3.12+, dataclasses, PyYAML, aiosqlite, cryptography (Fernet), aiohttp, pytest + pytest-asyncio

**前置依赖：** 无（Phase 1 是项目起点）

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/__init__.py` | 项目根包 |
| `src/config/__init__.py` | 配置子包 |
| `src/config/models.py` | Provider/Model dataclass 定义 |
| `src/config/store.py` | YAML 配置持久化 + SQLite 运行时状态 |
| `src/config/crypto.py` | API Key Fernet 对称加密 |
| `src/config/manager.py` | 配置 CRUD 业务逻辑 |
| `src/config/schema.py` | YAML 配置 JSON Schema 校验 |
| `src/network/__init__.py` | 网络子包 |
| `src/network/probe.py` | 连通性测试 + 延迟探测（aiohttp） |
| `tests/__init__.py` | 测试根包 |
| `tests/conftest.py` | pytest fixtures |
| `tests/config/__init__.py` | 配置测试子包 |
| `tests/config/test_models.py` | 模型 dataclass 测试 |
| `tests/config/test_crypto.py` | 加密/解密测试 |
| `tests/config/test_store.py` | 存储层测试 |
| `tests/config/test_manager.py` | CRUD 业务逻辑测试 |
| `tests/network/__init__.py` | 网络测试子包 |
| `tests/network/test_probe.py` | 连通性测试用例 |
| `pyproject.toml` | 项目元数据与依赖 |
| `config.example.yaml` | 示例配置文件 |

---

### 任务 1：项目骨架搭建

**文件：**
- 创建：`pyproject.toml`
- 创建：`src/__init__.py`
- 创建：`src/config/__init__.py`
- 创建：`src/network/__init__.py`
- 创建：`tests/__init__.py`
- 创建：`tests/config/__init__.py`
- 创建：`tests/network/__init__.py`
- 创建：`tests/conftest.py`
- 创建：`config.example.yaml`

- [ ] **步骤 1：创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=75.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "llm-router"
version = "0.1.0"
description = "智能 Agent 任务调度与 LLM 路由控制系统"
requires-python = ">=3.12"
dependencies = [
    "pyyaml>=6.0",
    "aiosqlite>=0.20",
    "aiohttp>=3.9",
    "cryptography>=43.0",
    "jsonschema>=4.23",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **步骤 2：创建空 `__init__.py` 文件**

```python
# src/__init__.py
"""LLM Router - 智能 Agent 任务调度与 LLM 路由控制系统."""
```

```python
# src/config/__init__.py
"""配置管理子包 - Provider/Model CRUD、加密存储、连通性测试."""
```

```python
# src/network/__init__.py
"""网络子包 - HTTP 连通性探测与延迟测量."""
```

- [ ] **步骤 3：创建 tests/conftest.py 基础 fixtures**

```python
# tests/conftest.py
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试，测试结束后自动清理."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def example_providers():
    """示例 Provider 配置数据."""
    return [
        {
            "name": "openai",
            "endpoint": "https://api.openai.com/v1",
            "api_key": "sk-test-openai-key-12345",
            "models": [
                {
                    "name": "gpt-4o",
                    "deployment": "cloud",
                    "context_window": 128000,
                    "cost_input_1k": 0.0025,
                    "cost_output_1k": 0.0100,
                    "tags": ["smart", "cloud", "expensive"],
                },
                {
                    "name": "gpt-4o-mini",
                    "deployment": "cloud",
                    "context_window": 128000,
                    "cost_input_1k": 0.00015,
                    "cost_output_1k": 0.0006,
                    "tags": ["cheap", "cloud", "fast"],
                },
            ],
        },
        {
            "name": "anthropic",
            "endpoint": "https://api.anthropic.com/v1",
            "api_key": "sk-ant-test-key-67890",
            "models": [
                {
                    "name": "claude-opus-5",
                    "deployment": "cloud",
                    "context_window": 200000,
                    "cost_input_1k": 0.015,
                    "cost_output_1k": 0.075,
                    "tags": ["smart", "cloud", "expensive"],
                },
            ],
        },
        {
            "name": "ollama-local",
            "endpoint": "http://localhost:11434",
            "api_key": None,
            "models": [
                {
                    "name": "qwen2.5:7b",
                    "deployment": "local",
                    "context_window": 32768,
                    "cost_input_1k": 0.0,
                    "cost_output_1k": 0.0,
                    "tags": ["cheap", "local", "basic"],
                },
            ],
        },
    ]
```

- [ ] **步骤 4：创建示例配置文件**

```yaml
# config.example.yaml
# LLM Router 配置文件示例
# 复制为 config.yaml 并填入实际配置

providers:
  - name: openai
    endpoint: https://api.openai.com/v1
    api_key: "sk-your-key-here"
    models:
      - name: gpt-4o
        deployment: cloud
        context_window: 128000
      - name: gpt-4o-mini
        deployment: cloud
        context_window: 128000
```

- [ ] **步骤 5：安装依赖并验证**

运行：`pip install -e ".[dev]"`
预期：所有依赖安装成功

- [ ] **步骤 6：运行空测试确认骨架正常**

运行：`pytest tests/ -v`
预期：无测试收集 (no tests ran)，但框架正常启动

- [ ] **步骤 7：Commit**

```bash
git add pyproject.toml src/ tests/ config.example.yaml .gitignore
git commit -m "chore: 项目骨架搭建 - LLM Router Phase 1 基础结构"
```

---

### 任务 2：数据模型定义

**文件：**
- 创建：`src/config/models.py`
- 创建：`tests/config/test_models.py`

- [ ] **步骤 1：编写数据模型测试**

```python
# tests/config/test_models.py
from dataclasses import FrozenInstanceError

import pytest

from src.config.models import (
    ModelConfig,
    ModelDeployment,
    ProviderConfig,
    ProviderStatus,
)


class TestModelConfig:
    def test_create_model_with_required_fields(self):
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        assert model.name == "gpt-4o"
        assert model.deployment == ModelDeployment.CLOUD
        assert model.context_window == 4096  # default
        assert model.tags == []  # default
        assert model.cost_input_1k == 0.0  # default
        assert model.cost_output_1k == 0.0  # default

    def test_create_model_with_all_fields(self):
        model = ModelConfig(
            name="gpt-4o",
            deployment=ModelDeployment.CLOUD,
            context_window=128000,
            cost_input_1k=0.0025,
            cost_output_1k=0.0100,
            tags=["smart", "expensive"],
        )
        assert model.context_window == 128000
        assert model.cost_input_1k == 0.0025
        assert model.tags == ["smart", "expensive"]

    def test_model_is_immutable(self):
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        with pytest.raises(FrozenInstanceError):
            model.name = "changed"  # type: ignore[misc]

    def test_model_equality_by_value(self):
        a = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        b = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        assert a == b

    def test_model_hashable(self):
        a = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        b = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        assert hash(a) == hash(b)
        assert len({a, b}) == 1


class TestProviderConfig:
    def test_create_provider_with_required_fields(self):
        provider = ProviderConfig(name="openai", endpoint="https://api.openai.com/v1")
        assert provider.name == "openai"
        assert provider.endpoint == "https://api.openai.com/v1"
        assert provider.api_key is None
        assert provider.models == []
        assert provider.status == ProviderStatus.UNKNOWN

    def test_create_provider_with_models(self):
        models = [
            ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD),
            ModelConfig(name="gpt-4o-mini", deployment=ModelDeployment.CLOUD),
        ]
        provider = ProviderConfig(
            name="openai",
            endpoint="https://api.openai.com/v1",
            api_key="sk-test",
            models=models,
        )
        assert len(provider.models) == 2
        assert provider.api_key == "sk-test"

    def test_provider_is_immutable(self):
        provider = ProviderConfig(name="openai", endpoint="https://api.openai.com/v1")
        with pytest.raises(FrozenInstanceError):
            provider.name = "changed"  # type: ignore[misc]

    def test_provider_add_model_returns_new_instance(self):
        provider = ProviderConfig(name="openai", endpoint="https://api.openai.com/v1")
        new_model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        updated = provider.add_model(new_model)
        assert len(provider.models) == 0
        assert len(updated.models) == 1
        assert updated.models[0].name == "gpt-4o"

    def test_provider_remove_model_returns_new_instance(self):
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        provider = ProviderConfig(
            name="openai",
            endpoint="https://api.openai.com/v1",
            models=[model],
        )
        updated = provider.remove_model("gpt-4o")
        assert len(updated.models) == 0
        assert len(provider.models) == 1  # original unchanged

    def test_provider_remove_nonexistent_model_raises(self):
        provider = ProviderConfig(name="openai", endpoint="https://api.openai.com/v1")
        with pytest.raises(ValueError, match="不存在"):
            provider.remove_model("nonexistent")


class TestProviderStatus:
    def test_status_values(self):
        assert ProviderStatus.ONLINE == "online"
        assert ProviderStatus.OFFLINE == "offline"
        assert ProviderStatus.DEGRADED == "degraded"
        assert ProviderStatus.UNKNOWN == "unknown"


class TestModelDeployment:
    def test_deployment_values(self):
        assert ModelDeployment.CLOUD == "cloud"
        assert ModelDeployment.LOCAL == "local"
        assert ModelDeployment.HYBRID == "hybrid"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/config/test_models.py -v`
预期：全部 FAIL（模块不存在）

- [ ] **步骤 3：实现数据模型**

```python
# src/config/models.py
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
    tags: list[str] = field(default_factory=list)


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
    models: list[ModelConfig] = field(default_factory=list)
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/config/test_models.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add src/config/models.py tests/config/test_models.py
git commit -m "feat(config): 定义 Provider/Model 不可变数据模型"
```

---

### 任务 3：加密模块

**文件：**
- 创建：`src/config/crypto.py`
- 创建：`tests/config/test_crypto.py`

- [ ] **步骤 1：编写加密模块测试**

```python
# tests/config/test_crypto.py
import pytest

from src.config.crypto import KeyCipher, generate_key


class TestKeyCipher:
    @pytest.fixture
    def cipher(self):
        key = generate_key()
        return KeyCipher(key)

    def test_encrypt_decrypt_roundtrip(self, cipher):
        plaintext = "sk-test-api-key-abc123"
        encrypted = cipher.encrypt(plaintext)
        assert encrypted != plaintext
        assert isinstance(encrypted, str)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_string(self, cipher):
        encrypted = cipher.encrypt("")
        assert cipher.decrypt(encrypted) == ""

    def test_encrypt_unicode(self, cipher):
        plaintext = "密钥-🔑-テスト"
        encrypted = cipher.encrypt(plaintext)
        assert cipher.decrypt(encrypted) == plaintext

    def test_encrypt_none_returns_none(self, cipher):
        assert cipher.encrypt_none(None) is None
        encrypted = cipher.encrypt_none("sk-key")
        assert encrypted is not None
        assert cipher.decrypt(encrypted) == "sk-key"

    def test_different_keys_produce_different_ciphertexts(self, cipher):
        plaintext = "sk-test-key"
        ct1 = cipher.encrypt(plaintext)
        ct2 = cipher.encrypt(plaintext)
        assert ct1 != ct2  # Fernet uses random IV per encryption

    def test_wrong_key_cannot_decrypt(self, cipher):
        other_cipher = KeyCipher(generate_key())
        encrypted = cipher.encrypt("sk-test-key")
        with pytest.raises(Exception):
            other_cipher.decrypt(encrypted)

    def test_tampered_ciphertext_raises(self, cipher):
        encrypted = cipher.encrypt("sk-test-key")
        tampered = encrypted[:-4] + "AAAA"
        with pytest.raises(Exception):
            cipher.decrypt(tampered)


class TestGenerateKey:
    def test_generate_key_returns_string(self):
        key = generate_key()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_key_is_random(self):
        keys = {generate_key() for _ in range(10)}
        assert len(keys) == 10
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/config/test_crypto.py -v`
预期：全部 FAIL

- [ ] **步骤 3：实现加密模块**

```python
# src/config/crypto.py
from __future__ import annotations

from cryptography.fernet import Fernet


def generate_key() -> str:
    """生成新的 Fernet 密钥并返回 base64 字符串."""
    return Fernet.generate_key().decode("utf-8")


class KeyCipher:
    """基于 Fernet 的对称加解密，用于 API Key 安全存储.

    用法:
        key = generate_key()
        cipher = KeyCipher(key)
        encrypted = cipher.encrypt("sk-abc123")
        decrypted = cipher.decrypt(encrypted)
    """

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> str:
        """加密明文字符串，返回 base64 密文."""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """解密密文，返回原始明文字符串."""
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    def encrypt_none(self, plaintext: str | None) -> str | None:
        """加密可选的明文字符串, None 透传."""
        if plaintext is None:
            return None
        return self.encrypt(plaintext)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/config/test_crypto.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add src/config/crypto.py tests/config/test_crypto.py
git commit -m "feat(config): Fernet 加解密模块用于 API Key 安全存储"
```

---

### 任务 4：配置持久化存储层

**文件：**
- 创建：`src/config/store.py`
- 创建：`tests/config/test_store.py`

- [ ] **步骤 1：编写存储层测试**

```python
# tests/config/test_store.py
from pathlib import Path

import pytest

from src.config.crypto import KeyCipher, generate_key
from src.config.models import (
    ModelConfig,
    ModelDeployment,
    ProviderConfig,
    ProviderStatus,
)
from src.config.store import ConfigStore


@pytest.fixture
def cipher():
    return KeyCipher(generate_key())


@pytest.fixture
def sample_providers():
    return [
        ProviderConfig(
            name="openai",
            endpoint="https://api.openai.com/v1",
            api_key="sk-test-123",
            models=[
                ModelConfig(
                    name="gpt-4o",
                    deployment=ModelDeployment.CLOUD,
                    context_window=128000,
                )
            ],
        ),
        ProviderConfig(
            name="ollama-local",
            endpoint="http://localhost:11434",
            api_key=None,
            models=[
                ModelConfig(
                    name="qwen2.5:7b",
                    deployment=ModelDeployment.LOCAL,
                    context_window=32768,
                )
            ],
        ),
    ]


class TestConfigStoreYAML:
    def test_save_and_load_providers(self, temp_dir, cipher, sample_providers):
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, cipher=cipher)

        store.save_providers(sample_providers)
        assert config_path.exists()

        loaded = store.load_providers()
        assert len(loaded) == 2
        assert loaded[0].name == "openai"
        assert loaded[1].name == "ollama-local"

    def test_load_encrypts_api_keys(self, temp_dir, cipher, sample_providers):
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, cipher=cipher)
        store.save_providers(sample_providers)

        raw = config_path.read_text()
        assert "sk-test-123" not in raw  # API Key 不在明文文件中

        loaded = store.load_providers()
        assert loaded[0].api_key == "sk-test-123"  # 解密后恢复

    def test_load_nonexistent_file_returns_empty(self, temp_dir, cipher):
        store = ConfigStore(config_path=temp_dir / "nonexistent.yaml", cipher=cipher)
        providers = store.load_providers()
        assert providers == []

    def test_load_empty_file_returns_empty(self, temp_dir, cipher):
        config_path = temp_dir / "empty.yaml"
        config_path.write_text("")
        store = ConfigStore(config_path=config_path, cipher=cipher)
        providers = store.load_providers()
        assert providers == []

    def test_null_api_key_handled(self, temp_dir, cipher, sample_providers):
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, cipher=cipher)
        store.save_providers(sample_providers)
        loaded = store.load_providers()
        assert loaded[1].api_key is None  # ollama-local 无 key

    def test_save_overwrites_existing(self, temp_dir, cipher, sample_providers):
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, cipher=cipher)
        store.save_providers(sample_providers)
        store.save_providers(sample_providers[:1])
        loaded = store.load_providers()
        assert len(loaded) == 1


class TestConfigStoreSQLite:
    @pytest.fixture
    async def store(self, temp_dir, cipher):
        db_path = temp_dir / "state.db"
        config_path = temp_dir / "config.yaml"
        store = ConfigStore(config_path=config_path, db_path=db_path, cipher=cipher)
        await store.init_db()
        yield store
        await store.close()

    async def test_init_db_creates_tables(self, store):
        async with store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = {row[0] async for row in cursor}
        assert "provider_status" in tables
        assert "latency_history" in tables

    async def test_update_provider_status(self, store):
        await store.update_provider_status("openai", ProviderStatus.ONLINE)
        status = await store.get_provider_status("openai")
        assert status == ProviderStatus.ONLINE

    async def test_update_status_overwrites(self, store):
        await store.update_provider_status("openai", ProviderStatus.ONLINE)
        await store.update_provider_status("openai", ProviderStatus.DEGRADED)
        status = await store.get_provider_status("openai")
        assert status == ProviderStatus.DEGRADED

    async def test_get_nonexistent_status_returns_unknown(self, store):
        status = await store.get_provider_status("nonexistent")
        assert status == ProviderStatus.UNKNOWN

    async def test_record_latency(self, store):
        await store.record_latency("openai", "gpt-4o", 320.5)
        history = await store.get_latency_history("openai", "gpt-4o", limit=10)
        assert len(history) == 1
        assert history[0]["provider"] == "openai"
        assert history[0]["model"] == "gpt-4o"
        assert history[0]["latency_ms"] == 320.5
        assert "timestamp" in history[0]

    async def test_latency_history_ordered_by_time(self, store):
        await store.record_latency("openai", "gpt-4o", 100.0)
        await store.record_latency("openai", "gpt-4o", 200.0)
        await store.record_latency("openai", "gpt-4o", 300.0)
        history = await store.get_latency_history("openai", "gpt-4o", limit=10)
        timestamps = [h["timestamp"] for h in history]
        assert timestamps == sorted(timestamps)

    async def test_latency_history_limit(self, store):
        for i in range(20):
            await store.record_latency("openai", "gpt-4o", float(i * 10))
        history = await store.get_latency_history("openai", "gpt-4o", limit=5)
        assert len(history) == 5

    async def test_get_latency_history_empty(self, store):
        history = await store.get_latency_history("openai", "nonexistent", limit=10)
        assert history == []

    async def test_get_all_provider_statuses(self, store):
        await store.update_provider_status("openai", ProviderStatus.ONLINE)
        await store.update_provider_status("anthropic", ProviderStatus.OFFLINE)
        statuses = await store.get_all_provider_statuses()
        assert statuses == {"openai": "online", "anthropic": "offline"}
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/config/test_store.py -v`
预期：全部 FAIL

- [ ] **步骤 3：实现存储层**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/config/test_store.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add src/config/store.py tests/config/test_store.py
git commit -m "feat(config): YAML 配置持久化 + SQLite 运行时状态存储"
```

---

### 任务 5：配置管理业务逻辑

**文件：**
- 创建：`src/config/manager.py`
- 创建：`src/config/schema.py`
- 创建：`tests/config/test_manager.py`

- [ ] **步骤 1：编写配置管理器测试**

```python
# tests/config/test_manager.py
import pytest

from src.config.crypto import KeyCipher, generate_key
from src.config.manager import ConfigManager
from src.config.models import (
    ModelConfig,
    ModelDeployment,
    ProviderConfig,
    ProviderStatus,
)
from src.config.store import ConfigStore


@pytest.fixture
def cipher():
    return KeyCipher(generate_key())


@pytest.fixture
async def manager(temp_dir, cipher):
    config_path = temp_dir / "config.yaml"
    db_path = temp_dir / "state.db"
    store = ConfigStore(config_path=config_path, db_path=db_path, cipher=cipher)
    await store.init_db()
    mgr = ConfigManager(store)
    yield mgr
    await store.close()


class TestConfigManagerProviders:
    async def test_add_provider(self, manager):
        provider = await manager.add_provider(
            name="openai",
            endpoint="https://api.openai.com/v1",
            api_key="sk-test",
        )
        assert provider.name == "openai"
        assert provider.api_key == "sk-test"
        all_providers = await manager.list_providers()
        assert len(all_providers) == 1

    async def test_add_duplicate_provider_raises(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        with pytest.raises(ValueError, match="已存在"):
            await manager.add_provider("openai", "https://api.openai.com/v1")

    async def test_remove_provider(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        await manager.remove_provider("openai")
        providers = await manager.list_providers()
        assert len(providers) == 0

    async def test_remove_nonexistent_provider_raises(self, manager):
        with pytest.raises(ValueError, match="不存在"):
            await manager.remove_provider("nonexistent")

    async def test_get_provider(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1", api_key="sk-test")
        provider = await manager.get_provider("openai")
        assert provider.name == "openai"
        assert provider.api_key == "sk-test"

    async def test_get_nonexistent_provider(self, manager):
        provider = await manager.get_provider("nonexistent")
        assert provider is None

    async def test_update_provider_api_key(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1", api_key="sk-old")
        await manager.update_provider_api_key("openai", "sk-new")
        provider = await manager.get_provider("openai")
        assert provider.api_key == "sk-new"

    async def test_list_providers_returns_copy(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        providers = await manager.list_providers()
        providers.clear()
        assert len(await manager.list_providers()) == 1


class TestConfigManagerModels:
    async def test_add_model(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        updated = await manager.add_model("openai", model)
        assert len(updated.models) == 1
        assert updated.models[0].name == "gpt-4o"

    async def test_add_duplicate_model_raises(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        await manager.add_model("openai", model)
        with pytest.raises(ValueError, match="已存在"):
            await manager.add_model("openai", model)

    async def test_remove_model(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        model = ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        await manager.add_model("openai", model)
        updated = await manager.remove_model("openai", "gpt-4o")
        assert len(updated.models) == 0

    async def test_list_models(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        await manager.add_model(
            "openai", ModelConfig(name="gpt-4o", deployment=ModelDeployment.CLOUD)
        )
        await manager.add_model(
            "openai", ModelConfig(name="gpt-4o-mini", deployment=ModelDeployment.CLOUD)
        )
        models = await manager.list_models("openai")
        assert len(models) == 2


class TestConfigManagerStatus:
    async def test_update_status(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        await manager.update_status("openai", ProviderStatus.ONLINE)
        status = await manager.get_status("openai")
        assert status == ProviderStatus.ONLINE

    async def test_get_all_statuses(self, manager):
        await manager.add_provider("openai", "https://api.openai.com/v1")
        await manager.add_provider("anthropic", "https://api.anthropic.com/v1")
        await manager.update_status("openai", ProviderStatus.ONLINE)
        await manager.update_status("anthropic", ProviderStatus.OFFLINE)
        statuses = await manager.get_all_statuses()
        assert statuses == {"openai": "online", "anthropic": "offline"}
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/config/test_manager.py -v`
预期：全部 FAIL

- [ ] **步骤 3：实现配置管理器**

```python
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
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/config/test_manager.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add src/config/manager.py tests/config/test_manager.py
git commit -m "feat(config): ConfigManager 业务逻辑层 CRUD + 状态管理"
```

---

### 任务 6：连通性探测与延迟测量

**文件：**
- 创建：`src/network/probe.py`
- 创建：`tests/network/test_probe.py`

- [ ] **步骤 1：编写连通性探测测试**

```python
# tests/network/test_probe.py
import pytest
from aiohttp import web
from aiohttp.test_utils import unused_port

from src.network.probe import LatencyProbe, ProbeResult


class TestProbeResult:
    def test_success_result(self):
        result = ProbeResult(
            provider="openai",
            model="gpt-4o",
            success=True,
            latency_ms=320.5,
        )
        assert result.success is True
        assert result.latency_ms == 320.5
        assert result.error is None

    def test_failure_result(self):
        result = ProbeResult(
            provider="openai",
            model="gpt-4o",
            success=False,
            error="Connection timeout",
        )
        assert result.success is False
        assert result.latency_ms is None
        assert result.error == "Connection timeout"

    def test_result_to_dict(self):
        result = ProbeResult(
            provider="openai",
            model="gpt-4o",
            success=True,
            latency_ms=320.5,
        )
        d = result.to_dict()
        assert d["provider"] == "openai"
        assert d["model"] == "gpt-4o"
        assert d["success"] is True
        assert d["latency_ms"] == 320.5
        assert "timestamp" in d


class TestLatencyProbe:
    @pytest.fixture
    async def echo_server(self):
        """创建一个简单的 echo HTTP 服务用于测试."""

        async def handler(request: web.Request) -> web.Response:
            return web.json_response({"status": "ok"})

        app = web.Application()
        app.router.add_get("/v1/models", handler)
        app.router.add_post("/v1/chat/completions", handler)

        port = unused_port()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", port)
        await site.start()

        yield f"http://localhost:{port}"

        await runner.cleanup()

    async def test_ping_models_endpoint_success(self, echo_server):
        probe = LatencyProbe(timeout_seconds=5)
        result = await probe.ping_models_endpoint("test-provider", echo_server)
        assert result.success is True
        assert result.latency_ms is not None
        assert result.latency_ms > 0

    async def test_ping_chat_endpoint_success(self, echo_server):
        probe = LatencyProbe(timeout_seconds=5)
        result = await probe.ping_chat_endpoint(
            "test-provider", "test-model", echo_server
        )
        assert result.success is True
        assert result.latency_ms is not None

    async def test_ping_unreachable_host(self):
        probe = LatencyProbe(timeout_seconds=1)
        result = await probe.ping_models_endpoint(
            "offline-provider", "http://192.0.2.1:9999"  # TEST-NET 地址
        )
        assert result.success is False
        assert result.error is not None

    async def test_ping_timeout(self, echo_server):
        probe = LatencyProbe(timeout_seconds=0.001)  # 极短超时
        result = await probe.ping_models_endpoint("test-provider", echo_server)
        # 可能成功也可能超时，取决于网络速度
        assert isinstance(result, ProbeResult)

    async def test_probe_all_empty_list(self):
        probe = LatencyProbe()
        results = await probe.probe_all([])
        assert results == []

    async def test_probe_all_with_providers(self, echo_server):
        from src.config.models import (
            ModelConfig,
            ModelDeployment,
            ProviderConfig,
        )

        provider = ProviderConfig(
            name="test-provider",
            endpoint=echo_server,
            models=[
                ModelConfig(name="test-model", deployment=ModelDeployment.LOCAL)
            ],
        )
        probe = LatencyProbe(timeout_seconds=5)
        results = await probe.probe_all([provider])
        assert len(results) > 0
        for result in results:
            assert result.provider == "test-provider"
            assert isinstance(result.success, bool)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/network/test_probe.py -v`
预期：全部 FAIL

- [ ] **步骤 3：实现连通性探测**

```python
# src/network/probe.py
from __future__ import annotations

import time
from dataclasses import dataclass, field

import aiohttp

from src.config.models import ProviderConfig


@dataclass(slots=True)
class ProbeResult:
    """单次连通性探测结果."""

    provider: str
    model: str
    success: bool
    latency_ms: float | None = None
    error: str | None = None
    timestamp: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S")
    )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class LatencyProbe:
    """异步 HTTP 连通性探测与延迟测量.

    用法:
        probe = LatencyProbe(timeout_seconds=10)
        result = await probe.ping_models_endpoint("openai", "https://api.openai.com/v1")
        print(f"延迟: {result.latency_ms}ms")
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def _measure(
        self,
        provider: str,
        model: str,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
    ) -> ProbeResult:
        """执行一次 HTTP 请求并测量延迟."""
        start = time.perf_counter()
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.request(method, url, headers=headers) as resp:
                    await resp.read()  # 确保完整接收
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    return ProbeResult(
                        provider=provider,
                        model=model,
                        success=resp.status < 500,
                        latency_ms=round(elapsed_ms, 2),
                    )
        except aiohttp.ClientError as e:
            return ProbeResult(
                provider=provider,
                model=model,
                success=False,
                error=f"HTTP error: {e}",
            )
        except TimeoutError:
            return ProbeResult(
                provider=provider,
                model=model,
                success=False,
                error="Connection timeout",
            )
        except Exception as e:
            return ProbeResult(
                provider=provider,
                model=model,
                success=False,
                error=f"Unexpected: {type(e).__name__}: {e}",
            )

    async def ping_models_endpoint(
        self, provider: str, endpoint: str
    ) -> ProbeResult:
        """探测 /v1/models 端点 (GET)."""
        url = f"{endpoint.rstrip('/')}/models"
        return await self._measure(provider, "all", url, method="GET")

    async def ping_chat_endpoint(
        self,
        provider: str,
        model: str,
        endpoint: str,
        api_key: str | None = None,
    ) -> ProbeResult:
        """探测 /v1/chat/completions 端点 (POST 空请求)."""
        url = f"{endpoint.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        # 发送最小合法请求体
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }
        start = time.perf_counter()
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(url, json=body, headers=headers) as resp:
                    await resp.read()
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    # 即使返回 4xx (如无权限) 也算连通——只要服务器响应了
                    return ProbeResult(
                        provider=provider,
                        model=model,
                        success=resp.status < 500,
                        latency_ms=round(elapsed_ms, 2),
                    )
        except aiohttp.ClientError as e:
            return ProbeResult(
                provider=provider,
                model=model,
                success=False,
                error=f"HTTP error: {e}",
            )
        except TimeoutError:
            return ProbeResult(
                provider=provider, model=model, success=False, error="Connection timeout"
            )
        except Exception as e:
            return ProbeResult(
                provider=provider,
                model=model,
                success=False,
                error=f"Unexpected: {type(e).__name__}: {e}",
            )

    async def probe_all(
        self, providers: list[ProviderConfig]
    ) -> list[ProbeResult]:
        """对所有 Provider 执行批量连通性探测.

        对每个 Provider：
        1. ping /models 端点确认连通
        2. ping /chat/completions 测量实际调用延迟
        """
        results: list[ProbeResult] = []

        async def probe_one(provider: ProviderConfig) -> None:
            # 1. 基本连通性
            result = await self.ping_models_endpoint(
                provider.name, provider.endpoint
            )
            results.append(result)

            # 2. 每个模型的 chat 延迟 (只需要端点可达就继续)
            if result.success:
                for model in provider.models:
                    chat_result = await self.ping_chat_endpoint(
                        provider.name,
                        model.name,
                        provider.endpoint,
                        provider.api_key,
                    )
                    results.append(chat_result)

        # 顺序执行以保证结果有序 (后续 Phase 可改为并行)
        for provider in providers:
            await probe_one(provider)

        return results
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/network/test_probe.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add src/network/probe.py tests/network/test_probe.py
git commit -m "feat(network): aiohttp 异步连通性探测与延迟测量"
```

---

### 任务 7：配置 Schema 校验

**文件：**
- 创建：`src/config/schema.py`
- 修改：`tests/config/test_manager.py` (添加校验相关测试)

- [ ] **步骤 1：编写 Schema 校验测试**

在 `tests/config/test_manager.py` 末尾追加：

```python
class TestConfigSchema:
    def test_valid_config_passes_validation(self):
        from src.config.schema import validate_config

        config = {
            "providers": [
                {
                    "name": "openai",
                    "endpoint": "https://api.openai.com/v1",
                    "api_key": "sk-test",
                    "models": [{"name": "gpt-4o"}],
                }
            ]
        }
        result = validate_config(config)
        assert result.errors == []
        assert result.valid is True

    def test_missing_name_fails_validation(self):
        from src.config.schema import validate_config

        config = {
            "providers": [
                {
                    "endpoint": "https://api.openai.com/v1",
                    "models": [{"name": "gpt-4o"}],
                }
            ]
        }
        result = validate_config(config)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_invalid_endpoint_url_fails(self):
        from src.config.schema import validate_config

        config = {
            "providers": [
                {
                    "name": "openai",
                    "endpoint": "not-a-url",
                    "models": [{"name": "gpt-4o"}],
                }
            ]
        }
        result = validate_config(config)
        assert result.valid is False

    def test_empty_providers_list(self):
        from src.config.schema import validate_config

        config = {"providers": []}
        result = validate_config(config)
        assert result.valid is True

    def test_missing_providers_key(self):
        from src.config.schema import validate_config

        config = {}
        result = validate_config(config)
        assert result.valid is False
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/config/test_manager.py::TestConfigSchema -v`
预期：全部 FAIL

- [ ] **步骤 3：实现 Schema 校验**

```python
# src/config/schema.py
from __future__ import annotations

from dataclasses import dataclass, field

from jsonschema import Draft202012Validator, ValidationError

# JSON Schema for config.yaml
CONFIG_SCHEMA: dict = {
    "type": "object",
    "required": ["providers"],
    "properties": {
        "providers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "endpoint"],
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^[a-z0-9][a-z0-9_-]*$",
                        "minLength": 1,
                    },
                    "endpoint": {
                        "type": "string",
                        "format": "uri",
                        "minLength": 1,
                    },
                    "api_key": {"type": ["string", "null"]},
                    "models": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "deployment": {
                                    "type": "string",
                                    "enum": ["cloud", "local", "hybrid"],
                                },
                                "context_window": {
                                    "type": "integer",
                                    "minimum": 1,
                                },
                                "cost_input_1k": {
                                    "type": "number",
                                    "minimum": 0,
                                },
                                "cost_output_1k": {
                                    "type": "number",
                                    "minimum": 0,
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        }
    },
}


@dataclass(slots=True)
class ValidationResult:
    """配置校验结果."""

    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_config(config: dict) -> ValidationResult:
    """校验配置字典是否符合 Schema."""
    validator = Draft202012Validator(CONFIG_SCHEMA)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(config), key=lambda e: e.path):
        path = ".".join(str(p) for p in error.path) if error.path else "(root)"
        errors.append(f"{path}: {error.message}")
    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/config/test_manager.py::TestConfigSchema -v`
预期：全部 PASS

- [ ] **步骤 5：运行全量测试**

运行：`pytest tests/ -v`
预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add src/config/schema.py tests/config/test_manager.py
git commit -m "feat(config): JSON Schema 配置校验 + 全量测试通过"
```

---

### 任务 8：.gitignore 清理与最终验证

**文件：**
- 创建：`.gitignore`

- [ ] **步骤 1：创建 .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
*.egg

# 虚拟环境
.venv/
venv/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# 项目特定
config.yaml          # 实际配置文件（含密钥，不提交）
router_state.db      # 运行时 SQLite 数据库
*.key                # 加密密钥文件

# OS
.DS_Store
Thumbs.db
```

- [ ] **步骤 2：移除不应提交的文件**

运行：`git rm --cached -r .claude/ 2>/dev/null; git rm --cached CLAUDE.md 2>/dev/null; echo "done"`

- [ ] **步骤 3：重新添加正确的文件**

```bash
git add .gitignore pyproject.toml config.example.yaml src/ tests/
```

- [ ] **步骤 4：运行全量测试做最终验证**

运行：`pytest tests/ -v --cov=src --cov-report=term-missing`
预期：全部 PASS，覆盖率 > 85%

- [ ] **步骤 5：最终 Commit**

```bash
git commit -m "chore: 添加 .gitignore，清理提交，Phase 1 完成"
```

---

## 完成标准

- [ ] 所有测试通过 (`pytest tests/ -v`)
- [ ] 覆盖率 > 85%
- [ ] Provider/Model 的 CRUD 全部可用
- [ ] API Key 加密存储，明文不出现在配置文件中
- [ ] 连通性测试可对真实 API 端点返回延迟数据
- [ ] 配置 Schema 校验生效
