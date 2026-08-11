# Phase 5b: A2A SDK 升级（HTTP Client）设计

日期: 2026-08-11
前置: Phase 5 CLI Driver（已实现）

## 1. 概述

将当前 A2A 层从"纯本地子进程 CLI"升级为"标准 A2A 协议 HTTP Client"，
同时保留 CLIDriver 作为本地路径。

## 2. 架构

```
A2AGateway (不变)
├── DriverRegistry (不变接口)
    ├── CLIDriver        ← 保留，本地子进程
    └── A2ADriver (新)   ← 实现相同 launch() 接口
        └── A2AClient (新) ← HTTP/JSON-RPC 2.0
            ├── tasks/send
            ├── tasks/get
            └── tasks/cancel

AgentCardResolver (新)    ← 发现远程 agent
    └── /.well-known/agent.json → 生成 DriverConfig
```

## 3. 模块设计

### 3.1 A2AClient (`src/a2a/http_client.py`)

标准 A2A JSON-RPC 2.0 over HTTP，不依赖外部 SDK。

```python
@dataclass(frozen=True, slots=True)
class A2AConfig:
    endpoint_url: str              # https://agent.example.com/v1
    default_timeout_seconds: float = 300.0
    api_key: str = ""              # Bearer token

class A2AClient:
    def __init__(self, config: A2AConfig) -> None
    async def send_task(self, prompt: str, task_id: str) -> dict
    async def get_task(self, task_id: str) -> dict
    async def cancel_task(self, task_id: str) -> dict
```

**JSON-RPC 请求格式（tasks/send）**：
```json
{
    "jsonrpc": "2.0",
    "id": "req-<uuid>",
    "method": "tasks/send",
    "params": {
        "message": {"role": "user", "parts": [{"text": "<prompt>"}]},
        "id": "<task_id>",
        "metadata": {}
    }
}
```

**依赖**：`aiohttp`（项目已有）。

### 3.2 A2ADriver (`src/a2a/http_driver.py`)

实现与 CLIDriver 完全一致的 `launch()` 接口，对内委托 A2AClient。

```python
class A2ADriver:
    def __init__(self, config: DriverConfig, client: A2AClient) -> None
    async def launch(task_id, prompt, workspace_root,
                     timeout_seconds, max_output_bytes) -> DriverResult
```

**launch 流程**：
1. `tasks/send` 发送 prompt → 返回 task_id
2. 轮询 `tasks/get`（间隔 2s），直到 status 为完成态或超时
3. 解析 A2A 响应中的 `artifact.parts[].text` → 填入 stdout
4. 状态映射：completed → exit_code=0, failed → exit_code=1, cancelled → timed_out
5. 构造 `DriverResult` 返回

### 3.3 AgentCardResolver (`src/a2a/card_resolver.py`)

动态发现远程 agent 能力。

```python
class AgentCardResolver:
    async def resolve(self, base_url: str) -> AgentCard | None:
        """GET {base_url}/.well-known/agent.json → AgentCard"""

@dataclass(frozen=True, slots=True)
class AgentCard:
    name: str
    description: str
    url: str
    skills: list[AgentSkill]
    version: str

@dataclass(frozen=True, slots=True)
class AgentSkill:
    id: str
    name: str
    description: str
```

### 3.4 DriverRegistry 扩展

`DriverRegistry` 接口不变，仅新增便捷方法：

```python
class DriverRegistry:
    # ... existing methods unchanged ...
    def register_remote(self, card: AgentCard, client: A2AClient) -> None:
        """根据 agent card 创建 A2ADriver 并注册"""
```

## 4. 配置扩展 (`config.example.yaml`)

```yaml
agents:
  remote:
    - name: "code-explorer"
      endpoint_url: "http://localhost:8080/v1"
      api_key: ""
      timeout_seconds: 300
    - name: "security-auditor"
      endpoint_url: "https://audit.internal.example.com/v1"
      api_key: "${AGENT_API_KEY}"
```

## 5. 兼容性

| 组件 | 变更 | 影响 |
|------|------|------|
| CLIDriver | 不变 | 无 |
| DriverConfig | 不变 | 无 |
| DriverResult | 不变 | 无 |
| DriverRegistry | 新增 register_remote() | 向后兼容 |
| A2AGateway | 不变 | 无 |
| 现有测试 | 不变 | 全部通过 |

## 6. 测试策略

| 测试 | 说明 |
|------|------|
| test_http_client_send_task | 用 aioresponses mock 验证 JSON-RPC 请求格式 |
| test_http_client_get_task | 轮询状态 → 完成态返回 |
| test_http_client_cancel_task | 发送 cancel 请求 |
| test_http_driver_launch_success | 完整 launch 流程 → DriverResult |
| test_http_driver_launch_timeout | 超时 → timed_out=True |
| test_http_driver_launch_error | 失败 → exit_code!=0 |
| test_card_resolver | mock /.well-known/agent.json → AgentCard |

## 7. 依赖

- `aiohttp`（已有）
- `aioresponses`（测试用，在 `[dev]` 依赖）
- 无额外外部 SDK

## 8. CI 兼容

- `aioresponses` mock 网络，测试不依赖真实外部服务
- 带 network 标记的集成测试可选运行
