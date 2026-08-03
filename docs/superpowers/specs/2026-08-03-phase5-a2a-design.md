# Phase 5: A2A 通信层（CLI Driver）设计规格

> 创建日期：2026-08-03

**目标：** 构建 Agent-to-Agent 通信层，短期方案通过 asyncio.subprocess 驱动 CLI Agent（Claude Code / Codex），支持超时控制、失败检测、与 TaskController 状态联动。

**架构：** A2AGateway 作为 TaskController 的执行后端，委托 CLIDriver 通过子进程执行 Agent 任务，Driver 注册表支持运行时扩展。

**技术栈：** asyncio.subprocess、asyncio.create_task

---

## 1. 文件结构

```
src/a2a/
├── __init__.py
├── cli_driver.py         # CLIDriver 子进程管理
├── driver_registry.py    # Driver 注册表
└── gateway.py            # A2AGateway 入口 + 与 TaskController 联动

tests/a2a/
├── __init__.py
├── test_cli_driver.py
├── test_driver_registry.py
└── test_gateway.py
```

---

## 2. CLIDriver (`src/a2a/cli_driver.py`)

### 2.1 数据模型

```python
@dataclass(frozen=True, slots=True)
class DriverConfig:
    name: str                     # 显示名，如 "claude"
    command: str                  # 可执行文件路径，如 "claude" 或 "claude-internal"
    default_timeout_seconds: float = 300.0  # 默认超时（5分钟）

@dataclass(frozen=True, slots=True)
class DriverResult:
    driver_name: str              # 使用的 driver 名称
    task_id: str
    exit_code: int
    stdout: str                   # 截断后的输出
    stderr: str
    timed_out: bool
    elapsed_seconds: float
```

### 2.2 CLIDriver 接口

```python
class CLIDriver:
    def __init__(self, config: DriverConfig) -> None

    async def launch(
        self,
        task_id: str,
        prompt: str,
        workspace_root: str,
        timeout_seconds: float | None = None,   # None → 使用 config 默认值
        max_output_bytes: int = 50_000,          # stdout 截断上限
    ) -> DriverResult:
        """启动子进程执行任务。

        流程：
        1. 构建命令：config.command 追加 prompt 作为参数
        2. asyncio.create_subprocess_exec，cwd=workspace_root
        3. asyncio.wait_for 超时控制
        4. 超时 → kill + 返回 timed_out=True
        5. 捕获 stdout/stderr，截断到 max_output_bytes
        6. 返回 DriverResult
        """
```

### 2.3 子进程执行细节

- 命令格式：`claude --print "<prompt>"`（通过 stdin 传 prompt 还是命令行参数？选命令行，简单直接）
- cwd：设为 workspace_root（Agent 的工作文件夹）
- 环境变量继承：继承父进程完整 env
- 超时处理：`asyncio.wait_for(proc.wait(), timeout)`，捕获 `asyncio.TimeoutError` → kill + wait
- 输出捕获：`proc.communicate()`，stdout/stderr 各自截断到 50KB

---

## 3. DriverRegistry (`src/a2a/driver_registry.py`)

```python
class DriverRegistry:
    def __init__(self) -> None

    def register(self, driver: CLIDriver) -> None
    def get(self, name: str) -> CLIDriver | None
    def list_all(self) -> list[str]              # 返回所有注册的 driver 名称
    def remove(self, name: str) -> None           # 不存在则抛 KeyError
```

---

## 4. A2AGateway (`src/a2a/gateway.py`)

### 4.1 职责

连接 TaskController 和 CLI Agent：

1. `execute(task, driver_name)` → 调用 CLIDriver.launch()
2. 根据 DriverResult 生成 FailureInfo（反馈给 RecoveryEngine）
3. 更新 AgentTask 状态（RUNNING → SUCCESS / FAILED）

### 4.2 接口

```python
class A2AGateway:
    def __init__(self, registry: DriverRegistry) -> None

    async def execute(
        self,
        task: AgentTask,
        workspace_root: str = "",
        driver_name: str = "",
        timeout_seconds: float | None = None,
    ) -> tuple[AgentTask, DriverResult]:
        """执行任务。

        1. 将 task 置为 RUNNING
        2. 选择 driver（指定或 registry 中第一个）
        3. 调用 driver.launch(task.task_id, task.prompt, workspace_root, timeout)
        4. 根据结果更新 task 状态：
           - exit_code == 0 且 timed_out == False → SUCCESS
           - timed_out == True → 调用 task.mark_failed("timeout")
           - exit_code != 0 → 调用 task.mark_failed(f"exit_code: {exit_code}")
        5. 返回 (更新后的 task, result)
        """
```

### 4.3 默认 workspace_root

`workspace_root` 默认值来自用户配置——本阶段不实现配置读取，调用方负责传入。默认目录：`./workspaces/{task_id}`。

---

## 5. 全局约束

- 所有 dataclass 使用 `@dataclass(frozen=True, slots=True)`
- SQLite 表规则同前（本阶段不新增表）
- 所有新文件 `from __future__ import annotations`
- YAGNI：只实现上述接口
- TDD 先行
- DriverResult 不评估输出质量——那是上层系统的职责
