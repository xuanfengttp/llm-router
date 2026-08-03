# Phase 4: Agent 任务控制器 + 安全红线 设计规格

> 创建日期：2026-08-03

**目标：** 构建 Agent 任务调度控制系统（命令式分发 + 失败恢复 + 人工兜底）和文件权限安全沙箱（规则矩阵 + 审核升级 + 审计日志）。

**架构：** 两个独立子系统——TaskController 负责以 30s 周期循环执行分发/监控/恢复，FileGuard 作为被调用的安全审核层拦截所有文件操作，两者通过审计日志解耦。

**技术栈：** SQLite、asyncio、dataclass(frozen=True, slots=True)

---

## 1. 文件结构

```
src/controller/
├── __init__.py
├── task_model.py       # AgentTask + AgentTaskStatus
├── task_queue.py       # TaskQueue SQLite CRUD
├── dispatcher.py        # DispatchEngine: 条件检查 + 分发
├── recovery.py          # RecoveryEngine: 失败恢复状态机
└── controller.py        # TaskController 主控 30s 循环

src/guard/
├── __init__.py
├── rule_matrix.py       # RuleMatrix: 规则匹配 + 审核决策
├── file_guard.py        # FileGuard: 安全审核入口
└── audit_log.py         # AuditLog SQLite 持久化

tests/controller/
├── __init__.py
├── test_task_model.py
├── test_task_queue.py
├── test_dispatcher.py
├── test_recovery.py
└── test_controller.py

tests/guard/
├── __init__.py
├── test_rule_matrix.py
├── test_file_guard.py
└── test_audit_log.py
```

修改：
- `src/config/store.py`：扩展 SQLite schema，新增 `agent_tasks` 表和 `audit_log` 表

---

## 2. AgentTask 数据模型 (`src/controller/task_model.py`)

### 2.1 AgentTaskStatus 枚举

```python
class AgentTaskStatus(str, Enum):
    PENDING = "pending"          # 等待分发
    CHECKING = "checking"        # 分发前条件检查中
    DISPATCHED = "dispatched"    # 已分发，等待 Agent 执行
    RUNNING = "running"          # Agent 正在执行
    SUCCESS = "success"          # 执行成功
    FAILED = "failed"            # 执行失败（可重试）
    STANDBY = "standby"          # 连续失败，暂停等待人工
    CANCELLED = "cancelled"      # 用户取消
```

### 2.2 AgentTask frozen dataclass

```python
@dataclass(frozen=True, slots=True)
class AgentTask:
    task_id: str                    # UUID
    prompt: str                     # 任务文本
    target_model: str               # 目标模型名
    status: AgentTaskStatus         # 当前状态
    retry_count: int = 0
    max_retries: int = 3
    failure_reason: str = ""        # 最近一次失败原因
    created_at: str = ""            # ISO 8601 UTC
    updated_at: str = ""            # ISO 8601 UTC
```

状态转移方法返回新实例：

```python
def transition_to(self, new_status: AgentTaskStatus, reason: str = "") -> AgentTask
def with_retry(self, reason: str) -> AgentTask                         # retry_count+1
def mark_running(self) -> AgentTask
def mark_success(self) -> AgentTask
def mark_failed(self, reason: str) -> AgentTask                        # retry_count<max→FAILED, else→STANDBY
def mark_cancelled(self) -> AgentTask
```

---

## 3. TaskQueue SQLite (`src/controller/task_queue.py`)

### 3.1 表结构

```sql
CREATE TABLE IF NOT EXISTS agent_tasks (
    task_id TEXT NOT NULL PRIMARY KEY,
    prompt TEXT NOT NULL DEFAULT '',
    target_model TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    failure_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);
```

### 3.2 TaskQueue 接口

```python
class TaskQueue:
    def __init__(self, db_path: str) -> None
    async def init_db(self) -> None
    async def close(self) -> None

    # 入队/出队
    async def enqueue(self, task: AgentTask) -> None
    async def dequeue_pending(self, limit: int = 5) -> list[AgentTask]

    # 状态更新
    async def update_status(self, task_id: str, task: AgentTask) -> None

    # 查询
    async def get(self, task_id: str) -> AgentTask | None
    async def list_by_status(self, status: AgentTaskStatus) -> list[AgentTask]
    async def count_by_status(self) -> dict[str, int]
    async def list_all(self, limit: int = 50, offset: int = 0) -> list[AgentTask]
```

---

## 4. DispatchEngine (`src/controller/dispatcher.py`)

### 4.1 职责

执行分发前的三重检查，全部通过才分发：

1. **延迟检查**：路由引擎预测的 p50 延迟 < 配置的延迟红线（默认 5000ms），且可预测性 > 阈值（默认 0.3）
2. **时间窗口检查**：当前时间是否在自动模式时段内（默认工作日晚 21:00-早 09:00 + 周末全天）
3. **路由匹配**：将任务 profile 传入 RouteEngine，获得最佳模型

### 4.2 自动模式时间窗口

```python
@dataclass(frozen=True, slots=True)
class TimeWindow:
    allow_weekday_night: bool = True       # 工作日晚间自动
    weekday_night_start: str = "21:00"
    weekday_night_end: str = "09:00"
    allow_weekend_all_day: bool = True     # 周末全天自动
    allow_weekday_day: bool = False        # 白天需人工确认

    def is_auto_mode(self, dt: datetime | None = None) -> bool
```

### 4.3 DispatchEngine 接口

```python
class DispatchEngine:
    def __init__(
        self,
        route_engine: RouteEngine,
        latency_redline_ms: float = 5000.0,
        predictability_threshold: float = 0.3,
        time_window: TimeWindow | None = None,
    ) -> None

    async def check(self, task: AgentTask) -> tuple[bool, str]:
        """三重检查。返回 (可分发, 拒绝原因)。"""

    async def dispatch(self, task: AgentTask, predictions: dict) -> RouteResult | None:
        """分发决策：check + route，返回最佳路由结果。"""
```

---

## 5. RecoveryEngine (`src/controller/recovery.py`)

### 5.1 失败分类与恢复动作

| 失败类型 | 检测方式 | 恢复动作 |
|----------|----------|----------|
| timeout | 执行时间 > 超时阈值 | 切换模型重试，最多 3 次 |
| network | 连接错误/超时 | 等待 30s 后重试，同模型 |
| rate_limit (429) | HTTP 429 | 等待 Retry-After 后重试 |
| auth_error (401/403) | HTTP 401/403 | 不重试 → 立即 STANDBY |
| unknown | 其他异常 | 重试 1 次，仍失败 → STANDBY |

连续失败 3 次（任意类型累计）→ 任务进入 STANDBY，等待人工。

### 5.2 RecoveryEngine 接口

```python
@dataclass(frozen=True, slots=True)
class FailureInfo:
    failure_type: str       # "timeout" | "network" | "rate_limit" | "auth_error" | "unknown"
    message: str
    retry_after_seconds: int = 0   # 仅 rate_limit

class RecoveryEngine:
    def __init__(self, max_retries: int = 3, retry_delay_network: int = 30) -> None

    def decide(self, task: AgentTask, failure: FailureInfo) -> tuple[RecoveryAction, str]:
        """返回 (动作, 理由)。

        RecoveryAction = "retry_same_model" | "retry_switch_model" | "standby" | "noop"
        """
```

---

## 6. TaskController 主控 (`src/controller/controller.py`)

### 6.1 30s 决策循环

```
每 30 秒：
  for each PENDING task:
    1. DispatchEngine.check(task)
    2. if pass → DispatchEngine.dispatch(task) → 更新 task 为 DISPATCHED
    3. if fail → 保持 PENDING，记录原因

  for each RUNNING task:
    1. 检查是否超时/失败
    2. if 失败 → RecoveryEngine.decide(task, failure)
    3. if retry → 更新 task 为 FAILED（等待下次循环重试）
    4. if standby → 更新 task 为 STANDBY

  for each FAILED task（可重试的）:
    1. RecoveryEngine.decide(task) → retry_same 或 retry_switch
    2. 更新 task 为 PENDING
```

### 6.2 TaskController 接口

```python
class TaskController:
    def __init__(
        self,
        queue: TaskQueue,
        dispatcher: DispatchEngine,
        recovery: RecoveryEngine,
        cycle_seconds: float = 30.0,
    ) -> None

    async def start(self) -> None       # 启动循环
    async def stop(self) -> None        # 停止循环
    async def tick(self) -> dict        # 单次决策（供测试/手动触发）

    async def submit(self, prompt: str, target_model: str = "") -> AgentTask
    async def cancel(self, task_id: str) -> AgentTask | None
    async def retry_standby(self, task_id: str) -> AgentTask | None
    async def get_status(self, task_id: str) -> AgentTask | None
```

---

## 7. RuleMatrix 规则矩阵 (`src/guard/rule_matrix.py`)

### 7.1 规则定义

```python
class PathCategory(str, Enum):
    OWN_WORKSPACE = "own_workspace"     # 自有文件夹
    OTHER_WORKSPACE = "other_workspace" # 其他任务文件夹
    SYSTEM = "system"                   # 系统目录

class FileOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"

class AuditDecision(str, Enum):
    ALLOW = "allow"           # 自动放行
    ESCALATE = "escalate"     # 升级人工审核
    DENY = "deny"             # 硬拒绝
```

### 7.2 规则矩阵

```python
# 矩阵: (PathCategory, FileOperation) → AuditDecision
RULE_MATRIX = {
    (PathCategory.OWN_WORKSPACE, FileOperation.READ):     AuditDecision.ALLOW,
    (PathCategory.OWN_WORKSPACE, FileOperation.WRITE):    AuditDecision.ALLOW,
    (PathCategory.OWN_WORKSPACE, FileOperation.DELETE):   AuditDecision.ALLOW,
    (PathCategory.OWN_WORKSPACE, FileOperation.EXECUTE):  AuditDecision.ESCALATE,

    (PathCategory.OTHER_WORKSPACE, FileOperation.READ):   AuditDecision.ESCALATE,
    (PathCategory.OTHER_WORKSPACE, FileOperation.WRITE):  AuditDecision.ESCALATE,
    (PathCategory.OTHER_WORKSPACE, FileOperation.DELETE): AuditDecision.ESCALATE,
    (PathCategory.OTHER_WORKSPACE, FileOperation.EXECUTE): AuditDecision.DENY,

    (PathCategory.SYSTEM, FileOperation.READ):            AuditDecision.DENY,
    (PathCategory.SYSTEM, FileOperation.WRITE):           AuditDecision.DENY,
    (PathCategory.SYSTEM, FileOperation.DELETE):          AuditDecision.DENY,
    (PathCategory.SYSTEM, FileOperation.EXECUTE):         AuditDecision.DENY,
}
```

### 7.3 RuleMatrix 接口

```python
@dataclass(frozen=True, slots=True)
class FileAccessRequest:
    task_id: str
    agent_id: str
    path: str
    operation: FileOperation
    workspace_root: str         # 任务自有文件夹根路径

class RuleMatrix:
    def __init__(self, custom_rules: dict | None = None) -> None   # 可覆盖默认规则

    def classify_path(self, path: str, workspace_root: str) -> PathCategory
    def decide(self, request: FileAccessRequest) -> AuditDecision
    def explain(self, request: FileAccessRequest) -> str       # 解释决策理由
```

`classify_path` 逻辑：
- path 以系统保留目录开头（`/System`, `/Windows`, `/etc`, `/usr`, `/bin`, `/boot`）→ SYSTEM
- path 不以 workspace_root 开头 → OTHER_WORKSPACE
- otherwise → OWN_WORKSPACE

---

## 8. FileGuard 安全入口 (`src/guard/file_guard.py`)

```python
class FileGuard:
    def __init__(self, matrix: RuleMatrix, audit_log: AuditLog) -> None

    async def check(self, request: FileAccessRequest) -> tuple[AuditDecision, str]:
        """审核文件操作请求，写入审计日志，返回 (决策, 理由)。"""

    async def check_batch(
        self, requests: list[FileAccessRequest]
    ) -> list[tuple[FileAccessRequest, AuditDecision, str]]:
        """批量审核（一个 Agent 可能同时操作多个文件）。"""
```

---

## 9. AuditLog (`src/guard/audit_log.py`)

### 9.1 表结构

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER NOT NULL PRIMARY KEY,
    timestamp TEXT NOT NULL DEFAULT '',
    task_id TEXT NOT NULL DEFAULT '',
    agent_id TEXT NOT NULL DEFAULT '',
    path TEXT NOT NULL DEFAULT '',
    operation TEXT NOT NULL DEFAULT '',
    path_category TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT ''
);
```

注意：这里用了 `id INTEGER NOT NULL PRIMARY KEY`（等价于 SQLite rowid），与计划中 "no auto-increment id" 约束一致（`INTEGER PRIMARY KEY` 在 SQLite 中自动递增，但不显式写 AUTOINCREMENT）。

### 9.2 AuditLog 接口

```python
class AuditLog:
    def __init__(self, db_path: str) -> None
    async def init_db(self) -> None
    async def close(self) -> None

    async def record(self, request: FileAccessRequest, decision: AuditDecision, path_category: PathCategory, reason: str) -> None

    # 查询
    async def get_by_task(self, task_id: str, limit: int = 100) -> list[dict]
    async def get_denied(self, limit: int = 50) -> list[dict]
    async def get_escalated(self, limit: int = 50) -> list[dict]
    async def get_recent(self, limit: int = 50) -> list[dict]
```

---

## 10. 全局约束

- 所有 dataclass 使用 `@dataclass(frozen=True, slots=True)`
- SQLite 使用 `CREATE TABLE IF NOT EXISTS`，NOT NULL 列有 DEFAULT，SQLite rowid 非显式 AUTOINCREMENT
- 所有新文件 `from __future__ import annotations`
- YAGNI：只实现上述接口，不添加未要求的功能
- TDD：每个模块先写测试、确认失败、再实现
- Controller 不评估任务输出质量——那是上层系统的职责
- 子进程调用 Agent 不在本阶段实现（Phase 5 A2A 层实现）
