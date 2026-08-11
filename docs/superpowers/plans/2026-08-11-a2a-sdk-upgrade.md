# A2A SDK 升级 — 实现计划

规格: `docs/superpowers/specs/2026-08-11-a2a-sdk-upgrade-design.md`
分支: `feature/a2a-sdk-upgrade`

## 任务清单

### 任务 1: A2AClient — HTTP/JSON-RPC 客户端 [TDD]

文件: `src/a2a/http_client.py` + `tests/a2a/test_http_client.py`

测试:
- test_send_task_format → mock 验证 JSON-RPC 请求结构正确
- test_send_task_response → mock 返回 {jsonrpc, id, result: {task: {id, status}}}
- test_get_task_completed → status="completed" 解析正确
- test_get_task_pending → status="working" 可轮询
- test_cancel_task → 发送 tasks/cancel 请求
- test_timeout → 超时异常处理
- test_auth_header → api_key 作为 Bearer token

实现:
```python
class A2AClient:
    def __init__(self, config: A2AConfig):
        self.endpoint = config.endpoint_url
        self.timeout = aiohttp.ClientTimeout(total=config.default_timeout_seconds)
        self.session: aiohttp.ClientSession | None = None
        if config.api_key:
            self._headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
        else:
            self._headers = {"Content-Type": "application/json"}

    async def send_task(self, prompt, task_id) -> dict: ...
    async def get_task(self, task_id) -> dict: ...
    async def cancel_task(self, task_id) -> dict: ...
    async def close(self) -> None: ...
    async def __aenter__ / __aexit__: ...  # context manager
```

用 `aioresponses` mock HTTP。

### 任务 2: A2ADriver — 轮询包装器 [TDD]

文件: `src/a2a/http_driver.py` + `tests/a2a/test_http_driver.py`

测试:
- test_launch_success → 发送 + 轮询完成 → DriverResult(exit_code=0)
- test_launch_failure → A2A 返回 failed → exit_code=1
- test_launch_timeout → 轮询超时 → timed_out=True
- test_launch_cancelled → A2A 返回 cancelled → timed_out=True
- test_elapsed_time_recorded → elapsed_seconds > 0

实现:
```python
class A2ADriver:
    def __init__(self, config: DriverConfig, client: A2AClient): ...
    async def launch(task_id, prompt, workspace_root, timeout_seconds, max_output_bytes) -> DriverResult:
        # 1. await client.send_task(prompt, task_id)
        # 2. poll loop: while True: await asyncio.sleep(2); resp = await client.get_task(task_id)
        # 3. status 完成 → 解析 artifact text → stdout
        # 4. status 失败 → exit_code=1
        # 5. 超时 → timed_out=True
```

### 任务 3: AgentCardResolver — 服务发现 [TDD]

文件: `src/a2a/card_resolver.py` + `tests/a2a/test_card_resolver.py`

测试:
- test_resolve_success → mock /.well-known/agent.json → AgentCard
- test_resolve_not_found → HTTP 404 → None
- test_resolve_invalid_json → 解析失败 → None
- test_card_contains_skills → AgentCard.skills 非空

### 任务 4: DriverRegistry 扩展 + 全量验证

修改 `src/a2a/driver_registry.py`: 新增 `register_remote()` 方法
```python
def register_remote(self, card: AgentCard, client: A2AClient) -> None:
    driver_config = DriverConfig(name=card.name, command=card.url)
    self.register(A2ADriver(config=driver_config, client=client))
```

全量验证: `python -m pytest tests/a2a/ -v`

## 执行

任务 1 + 2 + 3 可并行，任务 4 最后做。
