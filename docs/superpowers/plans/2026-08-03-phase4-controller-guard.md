# Phase 4: Agent 任务控制器 + 安全红线 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建 Agent 任务调度控制系统（命令式分发 + 失败恢复 + 人工兜底）和文件权限安全沙箱（规则矩阵 + 审核升级 + 审计日志）。

**架构：** TaskController 30s 周期循环执行分发/监控/恢复，FileGuard 作为被调用安全审核层拦截所有文件操作。两个子系统各自独立 SQLite，通过审计日志解耦。子进程 Agent 调用留到 Phase 5 A2A 层。

**技术栈：** SQLite + asyncio + dataclass(frozen=True, slots=True)

**全局约束：**
- 所有 dataclass 使用 `@dataclass(frozen=True, slots=True)`
- SQLite: `CREATE TABLE IF NOT EXISTS`，NOT NULL 列有 DEFAULT，INTEGER PRIMARY KEY 不显式 AUTOINCREMENT
- 所有新文件 `from __future__ import annotations`
- YAGNI：只实现计划要求的，不多做
- TDD：每个模块先写测试、确认失败、再实现
- Controller 不评估任务输出质量——那是上层系统的职责

---

### 任务 1：AgentTask 数据模型 + TaskQueue SQLite 持久化

**文件：**
- 创建：`src/controller/__init__.py`
- 创建：`src/controller/task_model.py`
- 创建：`src/controller/task_queue.py`
- 创建：`tests/controller/__init__.py`
- 创建：`tests/controller/test_task_model.py`
- 创建：`tests/controller/test_task_queue.py`

- [ ] **步骤 1：编写 task_model 测试**

```python
# tests/controller/test_task_model.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.controller.task_model import AgentTask, AgentTaskStatus


class TestAgentTaskStatus:
    """状态枚举."""

    def test_status_values(self):
        assert AgentTaskStatus.PENDING.value == "pending"
        assert AgentTaskStatus.CHECKING.value == "checking"
        assert AgentTaskStatus.DISPATCHED.value == "dispatched"
        assert AgentTaskStatus.RUNNING.value == "running"
        assert AgentTaskStatus.SUCCESS.value == "success"
        assert AgentTaskStatus.FAILED.value == "failed"
        assert AgentTaskStatus.STANDBY.value == "standby"
        assert AgentTaskStatus.CANCELLED.value == "cancelled"


class TestAgentTask:
    """AgentTask 数据模型."""

    def test_create_minimal(self):
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            prompt="hello",
            target_model="gpt-4o",
        )
        assert task.task_id
        assert task.prompt == "hello"
        assert task.target_model == "gpt-4o"
        assert task.status == AgentTaskStatus.PENDING
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.failure_reason == ""

    def test_create_with_all_fields(self):
        now = datetime.now(timezone.utc).isoformat()
        task = AgentTask(
            task_id="abc-123",
            prompt="test prompt",
            target_model="gpt-4o",
            status=AgentTaskStatus.RUNNING,
            retry_count=1,
            max_retries=5,
            failure_reason="timeout",
            created_at=now,
            updated_at=now,
        )
        assert task.status == AgentTaskStatus.RUNNING
        assert task.retry_count == 1
        assert task.max_retries == 5
        assert task.failure_reason == "timeout"

    def test_is_frozen(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        with pytest.raises(Exception):
            task.status = AgentTaskStatus.RUNNING  # type: ignore

    def test_transition_to(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        new_task = task.transition_to(AgentTaskStatus.RUNNING)
        assert new_task.status == AgentTaskStatus.RUNNING
        assert new_task.task_id == task.task_id
        # 原对象不变
        assert task.status == AgentTaskStatus.PENDING

    def test_transition_with_reason(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        new_task = task.transition_to(AgentTaskStatus.FAILED, reason="test")
        assert new_task.status == AgentTaskStatus.FAILED
        assert new_task.failure_reason == "test"

    def test_with_retry(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        retried = task.with_retry("timeout")
        assert retried.retry_count == 1
        assert retried.status == AgentTaskStatus.FAILED

    def test_with_retry_exceeds_max_goes_standby(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m", retry_count=2)
        retried = task.with_retry("crash")
        assert retried.retry_count == 3
        assert retried.status == AgentTaskStatus.STANDBY

    def test_mark_running(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        running = task.mark_running()
        assert running.status == AgentTaskStatus.RUNNING

    def test_mark_success(self):
        task = AgentTask(
            task_id="a", prompt="p", target_model="m",
            status=AgentTaskStatus.RUNNING,
        )
        done = task.mark_success()
        assert done.status == AgentTaskStatus.SUCCESS

    def test_mark_failed_retryable(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m", retry_count=0)
        failed = task.mark_failed("timeout")
        assert failed.status == AgentTaskStatus.FAILED
        assert failed.retry_count == 1

    def test_mark_failed_exceeds_max(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m", retry_count=2)
        failed = task.mark_failed("timeout")
        assert failed.status == AgentTaskStatus.STANDBY
        assert failed.retry_count == 3

    def test_mark_cancelled(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        cancelled = task.mark_cancelled()
        assert cancelled.status == AgentTaskStatus.CANCELLED

    def test_updated_at_changes_on_transition(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        new_task = task.transition_to(AgentTaskStatus.RUNNING)
        assert new_task.updated_at != task.updated_at

    def test_equality_by_value(self):
        task_id = str(uuid.uuid4())
        a = AgentTask(task_id=task_id, prompt="p", target_model="m")
        b = AgentTask(task_id=task_id, prompt="p", target_model="m")
        assert a == b

    def test_hashable(self):
        task = AgentTask(task_id="a", prompt="p", target_model="m")
        assert hash(task) is not None
```

- [ ] **步骤 2：编写 task_queue 测试**

```python
# tests/controller/test_task_queue.py
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from src.controller.task_model import AgentTask, AgentTaskStatus
from src.controller.task_queue import TaskQueue


class TestTaskQueue:
    """TaskQueue 持久化测试."""

    @pytest.fixture
    def db_path(self, tmp_path: Path):
        return tmp_path / "test_tasks.db"

    @pytest.fixture
    async def queue(self, db_path: Path):
        q = TaskQueue(str(db_path))
        await q.init_db()
        yield q
        await q.close()

    async def test_init_db_creates_table(self, queue, db_path):
        assert db_path.exists()

    async def test_enqueue_and_get(self, queue):
        task = AgentTask(task_id="t1", prompt="hello", target_model="gpt-4o")
        await queue.enqueue(task)
        loaded = await queue.get("t1")
        assert loaded is not None
        assert loaded.prompt == "hello"
        assert loaded.target_model == "gpt-4o"
        assert loaded.status == AgentTaskStatus.PENDING

    async def test_get_nonexistent(self, queue):
        result = await queue.get("nonexistent")
        assert result is None

    async def test_dequeue_pending(self, queue):
        for i in range(5):
            task = AgentTask(task_id=f"t{i}", prompt=f"p{i}", target_model="m")
            await queue.enqueue(task)
        pending = await queue.dequeue_pending(limit=3)
        assert len(pending) == 3
        assert all(t.status == AgentTaskStatus.PENDING for t in pending)

    async def test_dequeue_return_order(self, queue):
        await queue.enqueue(AgentTask(task_id="t1", prompt="first", target_model="m"))
        await queue.enqueue(AgentTask(task_id="t2", prompt="second", target_model="m"))
        pending = await queue.dequeue_pending(limit=5)
        assert pending[0].task_id == "t1"
        assert pending[1].task_id == "t2"

    async def test_dequeue_empty(self, queue):
        result = await queue.dequeue_pending()
        assert result == []

    async def test_update_status(self, queue):
        task = AgentTask(task_id="t1", prompt="p", target_model="m")
        await queue.enqueue(task)
        running = task.mark_running()
        await queue.update_status("t1", running)
        loaded = await queue.get("t1")
        assert loaded.status == AgentTaskStatus.RUNNING

    async def test_list_by_status(self, queue):
        await queue.enqueue(AgentTask(task_id="t1", prompt="p", target_model="m",
                                       status=AgentTaskStatus.SUCCESS))
        await queue.enqueue(AgentTask(task_id="t2", prompt="p", target_model="m"))
        await queue.enqueue(AgentTask(task_id="t3", prompt="p", target_model="m",
                                       status=AgentTaskStatus.FAILED))
        pending = await queue.list_by_status(AgentTaskStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].task_id == "t2"

    async def test_count_by_status(self, queue):
        await queue.enqueue(AgentTask(task_id="t1", prompt="p", target_model="m"))
        await queue.enqueue(AgentTask(task_id="t2", prompt="p", target_model="m",
                                       status=AgentTaskStatus.RUNNING))
        counts = await queue.count_by_status()
        assert counts["pending"] == 1
        assert counts["running"] == 1

    async def test_list_all_pagination(self, queue):
        for i in range(10):
            await queue.enqueue(AgentTask(task_id=f"t{i}", prompt=f"p{i}", target_model="m"))
        first_page = await queue.list_all(limit=3, offset=0)
        second_page = await queue.list_all(limit=3, offset=3)
        assert len(first_page) == 3
        assert len(second_page) == 3
        # 不重叠
        ids_p1 = {t.task_id for t in first_page}
        ids_p2 = {t.task_id for t in second_page}
        assert ids_p1.isdisjoint(ids_p2)

    async def test_enqueue_preserves_all_fields(self, queue):
        task = AgentTask(
            task_id="full-1", prompt="complex prompt", target_model="claude-3-opus",
            status=AgentTaskStatus.PENDING, retry_count=0, max_retries=5,
            failure_reason="", created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        await queue.enqueue(task)
        loaded = await queue.get("full-1")
        assert loaded.max_retries == 5
        assert loaded.created_at == "2026-01-01T00:00:00Z"
```

- [ ] **步骤 3：运行测试验证失败**

运行：`python -m pytest tests/controller/test_task_model.py tests/controller/test_task_queue.py -v`
预期：FAIL（模块不存在）

- [ ] **步骤 4：实现 `src/controller/__init__.py`**

```python
# src/controller/__init__.py
```

- [ ] **步骤 5：实现 `src/controller/task_model.py`**

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AgentTaskStatus(str, Enum):
    PENDING = "pending"
    CHECKING = "checking"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    STANDBY = "standby"
    CANCELLED = "cancelled"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class AgentTask:
    task_id: str
    prompt: str
    target_model: str
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    failure_reason: str = ""
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def _replace(self, **kwargs) -> AgentTask:
        current = {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "target_model": self.target_model,
            "status": self.status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        current.update(kwargs)
        current["updated_at"] = _utc_now()
        return AgentTask(**current)

    def transition_to(self, new_status: AgentTaskStatus, reason: str = "") -> AgentTask:
        kwargs: dict = {"status": new_status}
        if reason:
            kwargs["failure_reason"] = reason
        return self._replace(**kwargs)

    def with_retry(self, reason: str) -> AgentTask:
        new_count = self.retry_count + 1
        new_status = AgentTaskStatus.STANDBY if new_count >= self.max_retries else AgentTaskStatus.FAILED
        return self._replace(
            status=new_status,
            retry_count=new_count,
            failure_reason=reason,
        )

    def mark_running(self) -> AgentTask:
        return self.transition_to(AgentTaskStatus.RUNNING)

    def mark_success(self) -> AgentTask:
        return self.transition_to(AgentTaskStatus.SUCCESS)

    def mark_failed(self, reason: str) -> AgentTask:
        new_count = self.retry_count + 1
        if new_count >= self.max_retries:
            return self._replace(
                status=AgentTaskStatus.STANDBY,
                retry_count=new_count,
                failure_reason=reason,
            )
        return self._replace(
            status=AgentTaskStatus.FAILED,
            retry_count=new_count,
            failure_reason=reason,
        )

    def mark_cancelled(self) -> AgentTask:
        return self.transition_to(AgentTaskStatus.CANCELLED)
```

- [ ] **步骤 6：实现 `src/controller/task_queue.py`**

```python
from __future__ import annotations

from pathlib import Path

import aiosqlite

from src.controller.task_model import AgentTask, AgentTaskStatus


class TaskQueue:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
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
        """)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def enqueue(self, task: AgentTask) -> None:
        await self._conn.execute(
            "INSERT OR REPLACE INTO agent_tasks "
            "(task_id, prompt, target_model, status, retry_count, "
            "max_retries, failure_reason, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task.task_id, task.prompt, task.target_model,
                task.status.value, task.retry_count, task.max_retries,
                task.failure_reason, task.created_at, task.updated_at,
            ),
        )
        await self._conn.commit()

    async def dequeue_pending(self, limit: int = 5) -> list[AgentTask]:
        cursor = await self._conn.execute(
            "SELECT * FROM agent_tasks WHERE status = 'pending' "
            "ORDER BY created_at ASC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    async def update_status(self, task_id: str, task: AgentTask) -> None:
        await self._conn.execute(
            "UPDATE agent_tasks SET status = ?, retry_count = ?, "
            "failure_reason = ?, updated_at = ? "
            "WHERE task_id = ?",
            (
                task.status.value, task.retry_count,
                task.failure_reason, task.updated_at, task_id,
            ),
        )
        await self._conn.commit()

    async def get(self, task_id: str) -> AgentTask | None:
        cursor = await self._conn.execute(
            "SELECT * FROM agent_tasks WHERE task_id = ?",
            (task_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    async def list_by_status(self, status: AgentTaskStatus) -> list[AgentTask]:
        cursor = await self._conn.execute(
            "SELECT * FROM agent_tasks WHERE status = ? ORDER BY created_at ASC",
            (status.value,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    async def count_by_status(self) -> dict[str, int]:
        cursor = await self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM agent_tasks GROUP BY status",
        )
        rows = await cursor.fetchall()
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["status"]] = row["cnt"]
        return counts

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[AgentTask]:
        cursor = await self._conn.execute(
            "SELECT * FROM agent_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    def _row_to_task(self, row: aiosqlite.Row) -> AgentTask:
        return AgentTask(
            task_id=row["task_id"],
            prompt=row["prompt"],
            target_model=row["target_model"],
            status=AgentTaskStatus(row["status"]),
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            failure_reason=row["failure_reason"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
```

- [ ] **步骤 7：运行测试验证通过**

运行：`python -m pytest tests/controller/test_task_model.py tests/controller/test_task_queue.py -v`
预期：PASS

- [ ] **步骤 8：Commit**

```bash
git add src/controller/ tests/controller/
git commit -m "feat(controller): AgentTask 数据模型 + TaskQueue SQLite 持久化"
```

---

### 任务 2：DispatchEngine — 分发决策引擎

**文件：**
- 创建：`src/controller/dispatcher.py`
- 创建：`tests/controller/test_dispatcher.py`

- [ ] **步骤 1：编写测试**

```python
# tests/controller/test_dispatcher.py
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.controller.dispatcher import DispatchEngine, TimeWindow
from src.controller.task_model import AgentTask
from src.routing.engine import RouteEngine
from src.routing.strategy import BaselineStrategy
from src.routing.task_profile import DEFAULT_TASK_PROFILES
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestTimeWindow:
    """时间窗口测试."""

    def test_default_weekday_night_is_auto(self):
        tw = TimeWindow()
        # 周一凌晨 2:00 = weekday 0, hour 2
        dt = datetime(2026, 8, 3, 2, 0)  # Monday
        assert tw.is_auto_mode(dt) is True

    def test_default_weekday_day_is_not_auto(self):
        tw = TimeWindow()
        dt = datetime(2026, 8, 3, 14, 0)  # Monday 2pm
        assert tw.is_auto_mode(dt) is False

    def test_default_weekend_all_day_is_auto(self):
        tw = TimeWindow()
        dt_sat = datetime(2026, 8, 1, 14, 0)  # Saturday 2pm
        dt_sun = datetime(2026, 8, 2, 9, 0)   # Sunday 9am
        assert tw.is_auto_mode(dt_sat) is True
        assert tw.is_auto_mode(dt_sun) is True

    def test_allow_weekday_day_enabled(self):
        tw = TimeWindow(allow_weekday_day=True)
        dt = datetime(2026, 8, 3, 14, 0)  # Monday 2pm
        assert tw.is_auto_mode(dt) is True

    def test_current_time_defaults_to_now(self):
        tw = TimeWindow()
        result = tw.is_auto_mode()
        assert isinstance(result, bool)


class TestDispatchEngine:
    """分发决策引擎测试."""

    @pytest.fixture
    def candidates(self):
        return [
            ModelProfile(
                provider="openai", model="gpt-4o-mini",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.00015, cost_output_1k=0.0006,
                benchmark=BenchmarkData(arena_elo=1150),
                local_metrics=LocalMetrics(latency_p50_ms=100),
            ),
            ModelProfile(
                provider="openai", model="gpt-4o",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.0025, cost_output_1k=0.0100,
                benchmark=BenchmarkData(arena_elo=1287),
                local_metrics=LocalMetrics(latency_p50_ms=320),
            ),
        ]

    @pytest.fixture
    def engine(self, candidates):
        route = RouteEngine(strategy=BaselineStrategy())
        return DispatchEngine(
            route_engine=route,
            candidates=candidates,
        )

    def test_create_engine(self, engine):
        assert engine.latency_redline_ms == 5000.0
        assert engine.predictability_threshold == 0.3

    async def test_check_passes_within_limits(self, engine):
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o-mini")
        ok, reason = await engine.check(task)
        assert ok is True, f"Expected pass but got: {reason}"
        assert reason == ""

    async def test_check_fails_latency_too_high(self):
        route = RouteEngine(strategy=BaselineStrategy())
        engine = DispatchEngine(
            route_engine=route,
            candidates=[
                ModelProfile(
                    provider="p", model="slow", deployment="cloud",
                    context_window=64000, cost_input_1k=0.001, cost_output_1k=0.005,
                    benchmark=BenchmarkData(arena_elo=1000),
                    local_metrics=LocalMetrics(latency_p50_ms=6000),
                ),
            ],
            latency_redline_ms=5000,
        )
        task = AgentTask(task_id="t", prompt="p", target_model="slow")
        ok, reason = await engine.check(task)
        assert ok is False
        assert "latency" in reason.lower()

    async def test_dispatch_success(self, engine):
        task = AgentTask(task_id="t", prompt="code review", target_model="")
        result = await engine.dispatch(task, {})
        assert result is not None
        assert result.profile is not None
        assert result.score > 0

    async def test_dispatch_all_filtered_returns_none(self):
        route = RouteEngine(strategy=BaselineStrategy())
        engine = DispatchEngine(
            route_engine=route,
            candidates=[
                ModelProfile(
                    provider="p", model="slow", deployment="cloud",
                    context_window=64000, cost_input_1k=0.001, cost_output_1k=0.005,
                    benchmark=BenchmarkData(arena_elo=1000),
                    local_metrics=LocalMetrics(latency_p50_ms=6000),
                ),
            ],
            latency_redline_ms=100,
        )
        task = AgentTask(task_id="t", prompt="p", target_model="")
        result = await engine.dispatch(task, {})
        assert result is None
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/controller/test_dispatcher.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/controller/dispatcher.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.controller.task_model import AgentTask
from src.prediction.engine import LatencyPrediction
from src.routing.engine import RouteEngine, RouteResult
from src.routing.task_profile import DEFAULT_TASK_PROFILES
from src.scoring.profile import ModelProfile


@dataclass(frozen=True, slots=True)
class TimeWindow:
    allow_weekday_night: bool = True
    weekday_night_start: str = "21:00"
    weekday_night_end: str = "09:00"
    allow_weekend_all_day: bool = True
    allow_weekday_day: bool = False

    def is_auto_mode(self, dt: datetime | None = None) -> bool:
        if dt is None:
            dt = datetime.now(timezone.utc)
        weekday = dt.weekday()
        is_weekend = weekday >= 5

        if is_weekend:
            return self.allow_weekend_all_day

        hour = dt.hour
        night_start = int(self.weekday_night_start.split(":")[0])
        night_end = int(self.weekday_night_end.split(":")[0])

        is_night = hour >= night_start or hour < night_end
        if is_night:
            return self.allow_weekday_night

        return self.allow_weekday_day


class DispatchEngine:
    def __init__(
        self,
        route_engine: RouteEngine,
        candidates: list[ModelProfile],
        latency_redline_ms: float = 5000.0,
        predictability_threshold: float = 0.3,
        time_window: TimeWindow | None = None,
    ) -> None:
        self.route_engine = route_engine
        self.candidates = candidates
        self.latency_redline_ms = latency_redline_ms
        self.predictability_threshold = predictability_threshold
        self.time_window = time_window or TimeWindow()

    async def check(self, task: AgentTask) -> tuple[bool, str]:
        # 1. 时间窗口检查
        if not self.time_window.is_auto_mode():
            return False, "当前不在自动模式时间窗口内"

        # 2. 候选模型存在性检查
        matching = [c for c in self.candidates if c.model == task.target_model or not task.target_model]
        if not matching:
            matching = self.candidates

        if not matching:
            return False, "无可用候选模型"

        # 3. 延迟红线检查
        for c in matching:
            if c.local_metrics.latency_p50_ms > self.latency_redline_ms:
                return False, f"模型 {c.model} p50 延迟 {c.local_metrics.latency_p50_ms:.0f}ms 超过红线 {self.latency_redline_ms:.0f}ms"

        # 4. 可预测性检查
        for c in matching:
            if c.local_metrics.predictability < self.predictability_threshold:
                return False, f"模型 {c.model} 可预测性 {c.local_metrics.predictability:.2f} 低于阈值 {self.predictability_threshold}"

        return True, ""

    async def dispatch(
        self,
        task: AgentTask,
        predictions: dict[str, LatencyPrediction],
    ) -> RouteResult | None:
        ok, _reason = await self.check(task)
        if not ok:
            return None

        task_profile = DEFAULT_TASK_PROFILES.get("general_chat", list(DEFAULT_TASK_PROFILES.values())[0])
        self.route_engine._predictions = predictions

        result = self.route_engine.route(task_profile, self.candidates)
        return result
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/controller/test_dispatcher.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/controller/dispatcher.py tests/controller/test_dispatcher.py
git commit -m "feat(controller): DispatchEngine — 时间窗口 + 延迟红线 + 可预测性三重检查"
```

---

### 任务 3：RecoveryEngine — 失败恢复状态机

**文件：**
- 创建：`src/controller/recovery.py`
- 创建：`tests/controller/test_recovery.py`

- [ ] **步骤 1：编写测试**

```python
# tests/controller/test_recovery.py
from __future__ import annotations

from src.controller.recovery import FailureInfo, RecoveryAction, RecoveryEngine
from src.controller.task_model import AgentTask, AgentTaskStatus


class TestFailureInfo:
    def test_create(self):
        fi = FailureInfo(failure_type="timeout", message="timed out after 30s")
        assert fi.failure_type == "timeout"
        assert fi.message == "timed out after 30s"
        assert fi.retry_after_seconds == 0

    def test_rate_limit_with_retry_after(self):
        fi = FailureInfo(failure_type="rate_limit", message="429", retry_after_seconds=60)
        assert fi.retry_after_seconds == 60


class TestRecoveryEngine:
    def test_timeout_retry_switch_model(self):
        engine = RecoveryEngine()
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o", retry_count=0)
        fi = FailureInfo(failure_type="timeout", message="timed out")
        action, reason = engine.decide(task, fi)
        assert action == RecoveryAction.RETRY_SWITCH_MODEL
        assert "switch" in reason.lower()

    def test_network_retry_same_model(self):
        engine = RecoveryEngine()
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o", retry_count=0)
        fi = FailureInfo(failure_type="network", message="connection refused")
        action, reason = engine.decide(task, fi)
        assert action == RecoveryAction.RETRY_SAME_MODEL
        assert "same model" in reason.lower()

    def test_rate_limit_retry_same_model(self):
        engine = RecoveryEngine()
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o", retry_count=0)
        fi = FailureInfo(failure_type="rate_limit", message="429", retry_after_seconds=30)
        action, reason = engine.decide(task, fi)
        assert action == RecoveryAction.RETRY_SAME_MODEL
        assert "30s" in reason.lower()

    def test_auth_error_immediate_standby(self):
        engine = RecoveryEngine()
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o", retry_count=0)
        fi = FailureInfo(failure_type="auth_error", message="401")
        action, reason = engine.decide(task, fi)
        assert action == RecoveryAction.STANDBY
        assert "auth" in reason.lower()

    def test_unknown_retry_then_standby(self):
        engine = RecoveryEngine(max_retries=3)
        task_fresh = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=0)
        fi = FailureInfo(failure_type="unknown", message="something broke")
        action, _ = engine.decide(task_fresh, fi)
        assert action == RecoveryAction.RETRY_SAME_MODEL

    def test_unknown_twice_then_standby(self):
        engine = RecoveryEngine(max_retries=3)
        task = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=2)
        fi = FailureInfo(failure_type="unknown", message="error")
        action, _ = engine.decide(task, fi)
        assert action == RecoveryAction.STANDBY

    def test_consecutive_failures_total_3_standby(self):
        engine = RecoveryEngine(max_retries=3)
        task = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=2)
        fi = FailureInfo(failure_type="network", message="down")
        action, _ = engine.decide(task, fi)
        assert action == RecoveryAction.STANDBY

    def test_below_max_retries_still_retryable(self):
        engine = RecoveryEngine(max_retries=5)
        task = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=3)
        fi = FailureInfo(failure_type="timeout", message="timeout")
        action, _ = engine.decide(task, fi)
        assert action == RecoveryAction.RETRY_SWITCH_MODEL

    def test_custom_max_retries(self):
        engine = RecoveryEngine(max_retries=2)
        task = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=1)
        fi = FailureInfo(failure_type="network", message="error")
        action, _ = engine.decide(task, fi)
        assert action == RecoveryAction.STANDBY
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/controller/test_recovery.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/controller/recovery.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.controller.task_model import AgentTask


class RecoveryAction(str, Enum):
    RETRY_SAME_MODEL = "retry_same_model"
    RETRY_SWITCH_MODEL = "retry_switch_model"
    STANDBY = "standby"


@dataclass(frozen=True, slots=True)
class FailureInfo:
    failure_type: str     # timeout | network | rate_limit | auth_error | unknown
    message: str
    retry_after_seconds: int = 0


class RecoveryEngine:
    def __init__(self, max_retries: int = 3, retry_delay_network: int = 30) -> None:
        self.max_retries = max_retries
        self.retry_delay_network = retry_delay_network

    def decide(self, task: AgentTask, failure: FailureInfo) -> tuple[RecoveryAction, str]:
        new_count = task.retry_count + 1

        # auth_error 不重试
        if failure.failure_type == "auth_error":
            return RecoveryAction.STANDBY, f"认证错误，不重试：{failure.message}"

        # 达到最大重试次数
        if new_count >= self.max_retries:
            return RecoveryAction.STANDBY, (
                f"连续失败 {new_count} 次（上限 {self.max_retries}），"
                f"最终错误：{failure.message}"
            )

        # rate_limit 同模型重试
        if failure.failure_type == "rate_limit":
            wait = failure.retry_after_seconds or self.retry_delay_network
            return RecoveryAction.RETRY_SAME_MODEL, f"限流：等待 {wait}s 后同模型重试"

        # network 同模型重试
        if failure.failure_type == "network":
            return RecoveryAction.RETRY_SAME_MODEL, (
                f"网络错误：等待 {self.retry_delay_network}s 后同模型重试：{failure.message}"
            )

        # timeout 切换模型重试
        if failure.failure_type == "timeout":
            return RecoveryAction.RETRY_SWITCH_MODEL, f"超时：切换模型重试：{failure.message}"

        # unknown
        if new_count >= self.max_retries:
            return RecoveryAction.STANDBY, f"未知错误已达上限 {self.max_retries} 次：{failure.message}"
        return RecoveryAction.RETRY_SAME_MODEL, f"未知错误：同模型重试（{new_count}/{self.max_retries}）：{failure.message}"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/controller/test_recovery.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/controller/recovery.py tests/controller/test_recovery.py
git commit -m "feat(controller): RecoveryEngine — 5 种失败类型分类恢复状态机"
```

---

### 任务 4：TaskController 主控 30s 循环

**文件：**
- 创建：`src/controller/controller.py`
- 创建：`tests/controller/test_controller.py`

- [ ] **步骤 1：编写测试**

```python
# tests/controller/test_controller.py
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest

from src.controller.controller import TaskController
from src.controller.dispatcher import DispatchEngine, TimeWindow
from src.controller.recovery import FailureInfo, RecoveryEngine
from src.controller.task_model import AgentTask, AgentTaskStatus
from src.controller.task_queue import TaskQueue
from src.routing.engine import RouteEngine
from src.routing.strategy import BaselineStrategy
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestTaskController:
    @pytest.fixture
    def candidates(self):
        return [
            ModelProfile(
                provider="openai", model="gpt-4o-mini",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.00015, cost_output_1k=0.0006,
                benchmark=BenchmarkData(arena_elo=1150),
                local_metrics=LocalMetrics(latency_p50_ms=100),
            ),
        ]

    @pytest.fixture
    async def controller(self, tmp_path: Path, candidates):
        db_path = str(tmp_path / "test_tasks.db")
        queue = TaskQueue(db_path)
        await queue.init_db()

        route = RouteEngine(strategy=BaselineStrategy())
        tw = TimeWindow(allow_weekday_day=True)  # always auto
        dispatcher = DispatchEngine(route_engine=route, candidates=candidates, time_window=tw)
        recovery = RecoveryEngine(max_retries=2)

        ctrl = TaskController(
            queue=queue,
            dispatcher=dispatcher,
            recovery=recovery,
            cycle_seconds=0.1,
        )
        yield ctrl
        await ctrl.stop()
        await queue.close()

    async def test_submit_task(self, controller):
        task = await controller.submit("hello world")
        assert task.task_id
        assert task.prompt == "hello world"
        assert task.status == AgentTaskStatus.PENDING

    async def test_submit_with_target_model(self, controller):
        task = await controller.submit("code", target_model="gpt-4o-mini")
        assert task.target_model == "gpt-4o-mini"

    async def test_cancel_task(self, controller):
        task = await controller.submit("test")
        cancelled = await controller.cancel(task.task_id)
        assert cancelled.status == AgentTaskStatus.CANCELLED

    async def test_cancel_nonexistent(self, controller):
        result = await controller.cancel("nonexistent")
        assert result is None

    async def test_get_status(self, controller):
        task = await controller.submit("test")
        loaded = await controller.get_status(task.task_id)
        assert loaded is not None
        assert loaded.prompt == "test"

    async def test_get_status_nonexistent(self, controller):
        result = await controller.get_status("nonexistent")
        assert result is None

    async def test_tick_dispatches_pending_task(self, controller):
        task = await controller.submit("dispatch me", target_model="gpt-4o-mini")
        await controller.tick()
        updated = await controller.get_status(task.task_id)
        assert updated.status in (
            AgentTaskStatus.DISPATCHED,
            AgentTaskStatus.CHECKING,
        )

    async def test_tick_empty_queue_no_error(self, controller):
        result = await controller.tick()
        assert result["dispatched"] >= 0

    async def test_retry_standby(self, controller):
        task = await controller.submit("test")
        # 手动置为 standby
        standby = task.transition_to(AgentTaskStatus.STANDBY, "test")
        await controller.queue.update_status(task.task_id, standby)
        # retry_standby
        result = await controller.retry_standby(task.task_id)
        assert result is not None
        assert result.status == AgentTaskStatus.PENDING
        assert result.retry_count == 0  # reset
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/controller/test_controller.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/controller/controller.py`**

```python
from __future__ import annotations

import asyncio
import uuid

from src.controller.dispatcher import DispatchEngine
from src.controller.recovery import RecoveryAction, RecoveryEngine
from src.controller.task_model import AgentTask, AgentTaskStatus
from src.controller.task_queue import TaskQueue


class TaskController:
    def __init__(
        self,
        queue: TaskQueue,
        dispatcher: DispatchEngine,
        recovery: RecoveryEngine,
        cycle_seconds: float = 30.0,
    ) -> None:
        self.queue = queue
        self.dispatcher = dispatcher
        self.recovery = recovery
        self.cycle_seconds = cycle_seconds
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            await self.tick()
            await asyncio.sleep(self.cycle_seconds)

    async def tick(self) -> dict:
        dispatched = 0
        recovered = 0
        stood_by = 0

        # 处理 PENDING 任务
        pending = await self.queue.dequeue_pending(limit=10)
        for task in pending:
            ok, reason = await self.dispatcher.check(task)
            if ok:
                result = await self.dispatcher.dispatch(task, {})
                if result is not None:
                    dispatched_task = task.transition_to(AgentTaskStatus.DISPATCHED)
                    await self.queue.update_status(task.task_id, dispatched_task)
                    dispatched += 1
            # check 失败，保持 PENDING

        # 处理 FAILED 任务（可重试的）
        failed_tasks = await self.queue.list_by_status(AgentTaskStatus.FAILED)
        for task in failed_tasks:
            # 模拟一个 failure info（实际由 Agent runner 提供）
            from src.controller.recovery import FailureInfo
            fi = FailureInfo(
                failure_type="network",
                message=task.failure_reason or "unknown",
            )
            action, _reason = self.recovery.decide(task, fi)
            if action == RecoveryAction.RETRY_SAME_MODEL or action == RecoveryAction.RETRY_SWITCH_MODEL:
                # 重置为 PENDING 等待下次 dispatch
                retried = task.transition_to(AgentTaskStatus.PENDING)
                await self.queue.update_status(task.task_id, retried)
                recovered += 1
            elif action == RecoveryAction.STANDBY:
                standby = task.transition_to(AgentTaskStatus.STANDBY, task.failure_reason)
                await self.queue.update_status(task.task_id, standby)
                stood_by += 1

        return {"dispatched": dispatched, "recovered": recovered, "stood_by": stood_by}

    async def submit(self, prompt: str, target_model: str = "") -> AgentTask:
        task = AgentTask(
            task_id=str(uuid.uuid4()),
            prompt=prompt,
            target_model=target_model,
        )
        await self.queue.enqueue(task)
        return task

    async def cancel(self, task_id: str) -> AgentTask | None:
        task = await self.queue.get(task_id)
        if task is None:
            return None
        cancelled = task.mark_cancelled()
        await self.queue.update_status(task_id, cancelled)
        return cancelled

    async def retry_standby(self, task_id: str) -> AgentTask | None:
        task = await self.queue.get(task_id)
        if task is None:
            return None
        # 重置为 PENDING，清零重试计数
        retried = AgentTask(
            task_id=task.task_id,
            prompt=task.prompt,
            target_model=task.target_model,
            status=AgentTaskStatus.PENDING,
            retry_count=0,
            max_retries=task.max_retries,
            failure_reason="",
            created_at=task.created_at,
        )
        await self.queue.update_status(task_id, retried)
        return retried

    async def get_status(self, task_id: str) -> AgentTask | None:
        return await self.queue.get(task_id)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/controller/test_controller.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/controller/controller.py tests/controller/test_controller.py
git commit -m "feat(controller): TaskController — 30s 循环分发 + 失败恢复 + 人工兜底"
```

---

### 任务 5：RuleMatrix — 文件权限规则矩阵

**文件：**
- 创建：`src/guard/__init__.py`
- 创建：`src/guard/rule_matrix.py`
- 创建：`src/guard/file_guard.py`
- 创建：`tests/guard/__init__.py`
- 创建：`tests/guard/test_rule_matrix.py`
- 创建：`tests/guard/test_file_guard.py`

- [ ] **步骤 1：编写测试**

```python
# tests/guard/test_rule_matrix.py
from __future__ import annotations

import pytest

from src.guard.rule_matrix import (
    AuditDecision,
    FileAccessRequest,
    FileOperation,
    PathCategory,
    RuleMatrix,
)


class TestPathCategory:
    def test_own_workspace(self):
        m = RuleMatrix()
        cat = m.classify_path("/workspace/task-1/src/main.py", "/workspace/task-1")
        assert cat == PathCategory.OWN_WORKSPACE

    def test_other_workspace(self):
        m = RuleMatrix()
        cat = m.classify_path("/workspace/task-2/src/main.py", "/workspace/task-1")
        assert cat == PathCategory.OTHER_WORKSPACE

    def test_system_directory(self):
        m = RuleMatrix()
        cat = m.classify_path("/System/App/config", "/workspace/task-1")
        assert cat == PathCategory.SYSTEM

    def test_windows_system(self):
        m = RuleMatrix()
        assert m.classify_path("/Windows/System32/dll", "/ws/task-1") == PathCategory.SYSTEM
        assert m.classify_path("/etc/passwd", "/ws/task-1") == PathCategory.SYSTEM
        assert m.classify_path("/usr/bin/sh", "/ws/task-1") == PathCategory.SYSTEM

    def test_subpath_within_workspace(self):
        m = RuleMatrix()
        cat = m.classify_path("/ws/task-1", "/ws/task-10")
        assert cat == PathCategory.OTHER_WORKSPACE

    def test_subdir_within_workspace(self):
        m = RuleMatrix()
        cat = m.classify_path("/ws/task-1/sub/deep/file.txt", "/ws/task-1")
        assert cat == PathCategory.OWN_WORKSPACE


class TestRuleMatrix:
    def test_own_workspace_read_allowed(self):
        m = RuleMatrix()
        req = FileAccessRequest(
            task_id="t1", agent_id="a1",
            path="/ws/t1/file.py", operation=FileOperation.READ,
            workspace_root="/ws/t1",
        )
        assert m.decide(req) == AuditDecision.ALLOW

    def test_own_workspace_write_allowed(self):
        m = RuleMatrix()
        req = FileAccessRequest("t1", "a1", "/ws/t1/file.py", FileOperation.WRITE, "/ws/t1")
        assert m.decide(req) == AuditDecision.ALLOW

    def test_own_workspace_execute_escalate(self):
        m = RuleMatrix()
        req = FileAccessRequest("t1", "a1", "/ws/t1/run.sh", FileOperation.EXECUTE, "/ws/t1")
        assert m.decide(req) == AuditDecision.ESCALATE

    def test_other_workspace_read_escalate(self):
        m = RuleMatrix()
        req = FileAccessRequest("t1", "a1", "/ws/t2/file.py", FileOperation.READ, "/ws/t1")
        assert m.decide(req) == AuditDecision.ESCALATE

    def test_other_workspace_execute_deny(self):
        m = RuleMatrix()
        req = FileAccessRequest("t1", "a1", "/ws/t2/run.sh", FileOperation.EXECUTE, "/ws/t1")
        assert m.decide(req) == AuditDecision.DENY

    def test_system_read_deny(self):
        m = RuleMatrix()
        req = FileAccessRequest("t1", "a1", "/etc/passwd", FileOperation.READ, "/ws/t1")
        assert m.decide(req) == AuditDecision.DENY

    def test_system_write_deny(self):
        m = RuleMatrix()
        req = FileAccessRequest("t1", "a1", "/Windows/System32/x.dll", FileOperation.WRITE, "/ws/t1")
        assert m.decide(req) == AuditDecision.DENY

    def test_custom_rule_override(self):
        custom = {
            (PathCategory.OWN_WORKSPACE, FileOperation.EXECUTE): AuditDecision.ALLOW,
        }
        m = RuleMatrix(custom_rules=custom)
        req = FileAccessRequest("t1", "a1", "/ws/t1/run.sh", FileOperation.EXECUTE, "/ws/t1")
        assert m.decide(req) == AuditDecision.ALLOW

    def test_explain_returns_reason(self):
        m = RuleMatrix()
        req = FileAccessRequest("t1", "a1", "/etc/passwd", FileOperation.READ, "/ws/t1")
        explanation = m.explain(req)
        assert "系统目录" in explanation
```

```python
# tests/guard/test_file_guard.py
from __future__ import annotations

from pathlib import Path

import pytest

from src.guard.audit_log import AuditLog
from src.guard.file_guard import FileGuard
from src.guard.rule_matrix import (
    AuditDecision,
    FileAccessRequest,
    FileOperation,
    RuleMatrix,
)


class TestFileGuard:
    @pytest.fixture
    async def guard(self, tmp_path: Path):
        db_path = str(tmp_path / "test_audit.db")
        audit_log = AuditLog(db_path)
        await audit_log.init_db()
        matrix = RuleMatrix()
        g = FileGuard(matrix=matrix, audit_log=audit_log)
        yield g
        await audit_log.close()

    async def test_single_check(self, guard):
        req = FileAccessRequest(
            task_id="t1", agent_id="a1",
            path="/ws/t1/file.py", operation=FileOperation.READ,
            workspace_root="/ws/t1",
        )
        decision, reason = await guard.check(req)
        assert decision == AuditDecision.ALLOW
        assert len(reason) > 0

    async def test_check_system_deny(self, guard):
        req = FileAccessRequest("t1", "a1", "/etc/shadow", FileOperation.READ, "/ws/t1")
        decision, reason = await guard.check(req)
        assert decision == AuditDecision.DENY

    async def test_batch_check(self, guard):
        reqs = [
            FileAccessRequest("t1", "a1", "/ws/t1/a.py", FileOperation.READ, "/ws/t1"),
            FileAccessRequest("t1", "a1", "/ws/t1/b.py", FileOperation.WRITE, "/ws/t1"),
            FileAccessRequest("t1", "a1", "/etc/passwd", FileOperation.READ, "/ws/t1"),
        ]
        results = await guard.check_batch(reqs)
        assert len(results) == 3
        assert results[0][1] == AuditDecision.ALLOW
        assert results[1][1] == AuditDecision.ALLOW
        assert results[2][1] == AuditDecision.DENY

    async def test_empty_batch(self, guard):
        results = await guard.check_batch([])
        assert results == []
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/guard/test_rule_matrix.py tests/guard/test_file_guard.py -v`
预期：FAIL（audit_log 模块还不存在，需先创建占位）

先创建 `src/guard/audit_log.py` 最小骨架让 file_guard 测试可 import：

```python
# src/guard/audit_log.py (最小骨架)
from __future__ import annotations

class AuditLog:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
    async def init_db(self) -> None: pass
    async def close(self) -> None: pass
    async def record(self, *args, **kwargs) -> None: pass
```

- [ ] **步骤 3：实现 `src/guard/__init__.py`**

```python
# src/guard/__init__.py
```

- [ ] **步骤 4：实现 `src/guard/rule_matrix.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class PathCategory(str, Enum):
    OWN_WORKSPACE = "own_workspace"
    OTHER_WORKSPACE = "other_workspace"
    SYSTEM = "system"


class FileOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"


class AuditDecision(str, Enum):
    ALLOW = "allow"
    ESCALATE = "escalate"
    DENY = "deny"


DEFAULT_RULE_MATRIX: dict[tuple[PathCategory, FileOperation], AuditDecision] = {
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

SYSTEM_ROOTS = ("/System", "/Windows", "/etc", "/usr", "/bin", "/boot")


@dataclass(frozen=True, slots=True)
class FileAccessRequest:
    task_id: str
    agent_id: str
    path: str
    operation: FileOperation
    workspace_root: str


class RuleMatrix:
    def __init__(
        self,
        custom_rules: dict[tuple[PathCategory, FileOperation], AuditDecision] | None = None,
    ) -> None:
        self._rules: dict = dict(DEFAULT_RULE_MATRIX)
        if custom_rules:
            self._rules.update(custom_rules)

    def classify_path(self, path: str, workspace_root: str) -> PathCategory:
        normalized_path = os.path.normpath(path).replace("\\", "/")
        for root in SYSTEM_ROOTS:
            if normalized_path.startswith(root):
                return PathCategory.SYSTEM

        normalized_ws = os.path.normpath(workspace_root).replace("\\", "/")
        if normalized_path.startswith(normalized_ws):
            return PathCategory.OWN_WORKSPACE

        return PathCategory.OTHER_WORKSPACE

    def decide(self, request: FileAccessRequest) -> AuditDecision:
        category = self.classify_path(request.path, request.workspace_root)
        key = (category, request.operation)
        return self._rules.get(key, AuditDecision.DENY)

    def explain(self, request: FileAccessRequest) -> str:
        category = self.classify_path(request.path, request.workspace_root)
        decision = self.decide(request)
        reasons = {
            (PathCategory.OWN_WORKSPACE, FileOperation.READ): "自有文件夹读取 — 自动放行",
            (PathCategory.OWN_WORKSPACE, FileOperation.WRITE): "自有文件夹写入 — 自动放行",
            (PathCategory.OWN_WORKSPACE, FileOperation.DELETE): "自有文件夹删除 — 自动放行",
            (PathCategory.OWN_WORKSPACE, FileOperation.EXECUTE): "自有文件夹执行文件 — 升级人工审核",
            (PathCategory.OTHER_WORKSPACE, FileOperation.READ): "跨任务文件夹读取 — 升级人工审核",
            (PathCategory.OTHER_WORKSPACE, FileOperation.WRITE): "跨任务文件夹写入 — 升级人工审核",
            (PathCategory.OTHER_WORKSPACE, FileOperation.DELETE): "跨任务文件夹删除 — 升级人工审核",
            (PathCategory.OTHER_WORKSPACE, FileOperation.EXECUTE): "跨任务文件夹执行文件 — 硬拒绝",
            (PathCategory.SYSTEM, FileOperation.READ): "系统目录读取 — 硬拒绝",
            (PathCategory.SYSTEM, FileOperation.WRITE): "系统目录写入 — 硬拒绝",
            (PathCategory.SYSTEM, FileOperation.DELETE): "系统目录删除 — 硬拒绝",
            (PathCategory.SYSTEM, FileOperation.EXECUTE): "系统目录执行文件 — 硬拒绝",
        }
        return reasons.get((category, request.operation), f"{category}:{request.operation} → {decision}")
```

- [ ] **步骤 5：实现 `src/guard/file_guard.py`**

```python
from __future__ import annotations

from src.guard.audit_log import AuditLog
from src.guard.rule_matrix import (
    AuditDecision,
    FileAccessRequest,
    RuleMatrix,
)


class FileGuard:
    def __init__(self, matrix: RuleMatrix, audit_log: AuditLog) -> None:
        self.matrix = matrix
        self.audit_log = audit_log

    async def check(self, request: FileAccessRequest) -> tuple[AuditDecision, str]:
        category = self.matrix.classify_path(request.path, request.workspace_root)
        decision = self.matrix.decide(request)
        reason = self.matrix.explain(request)

        await self.audit_log.record(request, decision, category, reason)
        return decision, reason

    async def check_batch(
        self, requests: list[FileAccessRequest],
    ) -> list[tuple[FileAccessRequest, AuditDecision, str]]:
        results: list[tuple[FileAccessRequest, AuditDecision, str]] = []
        for req in requests:
            decision, reason = await self.check(req)
            results.append((req, decision, reason))
        return results
```

- [ ] **步骤 6：运行测试验证通过**

运行：`python -m pytest tests/guard/test_rule_matrix.py tests/guard/test_file_guard.py -v`
预期：PASS

- [ ] **步骤 7：Commit**

```bash
git add src/guard/ tests/guard/
git commit -m "feat(guard): RuleMatrix 规则矩阵 + FileGuard 安全审核入口"
```

---

### 任务 6：AuditLog 审计日志 + 全量测试

**文件：**
- 修改：`src/guard/audit_log.py`（替换骨架）
- 创建：`tests/guard/test_audit_log.py`

- [ ] **步骤 1：编写测试**

```python
# tests/guard/test_audit_log.py
from __future__ import annotations

from pathlib import Path

import pytest

from src.guard.audit_log import AuditLog
from src.guard.rule_matrix import (
    AuditDecision,
    FileAccessRequest,
    FileOperation,
    PathCategory,
)


class TestAuditLog:
    @pytest.fixture
    def db_path(self, tmp_path: Path):
        return str(tmp_path / "test_audit.db")

    @pytest.fixture
    async def audit_log(self, db_path):
        log = AuditLog(db_path)
        await log.init_db()
        yield log
        await log.close()

    async def test_init_db_creates_table(self, audit_log, db_path):
        assert Path(db_path).exists()

    async def test_record(self, audit_log):
        req = FileAccessRequest("t1", "a1", "/ws/t1/file.py", FileOperation.READ, "/ws/t1")
        await audit_log.record(req, AuditDecision.ALLOW, PathCategory.OWN_WORKSPACE, "test reason")

    async def test_get_by_task(self, audit_log):
        r1 = FileAccessRequest("t1", "a1", "/ws/t1/a.py", FileOperation.READ, "/ws/t1")
        r2 = FileAccessRequest("t2", "a2", "/ws/t2/b.py", FileOperation.WRITE, "/ws/t2")
        r3 = FileAccessRequest("t1", "a1", "/ws/t1/c.py", FileOperation.READ, "/ws/t1")

        await audit_log.record(r1, AuditDecision.ALLOW, PathCategory.OWN_WORKSPACE, "ok")
        await audit_log.record(r2, AuditDecision.DENY, PathCategory.OTHER_WORKSPACE, "no")
        await audit_log.record(r3, AuditDecision.ALLOW, PathCategory.OWN_WORKSPACE, "ok")

        entries = await audit_log.get_by_task("t1")
        assert len(entries) == 2
        assert all(e["task_id"] == "t1" for e in entries)

    async def test_get_by_task_empty(self, audit_log):
        entries = await audit_log.get_by_task("nonexistent")
        assert entries == []

    async def test_get_denied(self, audit_log):
        req = FileAccessRequest("t1", "a1", "/etc/passwd", FileOperation.READ, "/ws/t1")
        await audit_log.record(req, AuditDecision.DENY, PathCategory.SYSTEM, "硬拒绝")

        denied = await audit_log.get_denied()
        assert len(denied) == 1
        assert denied[0]["decision"] == "deny"

    async def test_get_escalated(self, audit_log):
        req = FileAccessRequest("t1", "a1", "/ws/t2/file.py", FileOperation.READ, "/ws/t1")
        await audit_log.record(req, AuditDecision.ESCALATE, PathCategory.OTHER_WORKSPACE, "升级")

        escalated = await audit_log.get_escalated()
        assert len(escalated) == 1
        assert escalated[0]["decision"] == "escalate"

    async def test_get_recent(self, audit_log):
        for i in range(5):
            req = FileAccessRequest(f"t{i}", "a", f"/ws/t{i}/file.py", FileOperation.READ, f"/ws/t{i}")
            await audit_log.record(req, AuditDecision.ALLOW, PathCategory.OWN_WORKSPACE, "ok")

        recent = await audit_log.get_recent(limit=3)
        assert len(recent) == 3
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/guard/test_audit_log.py -v`
预期：FAIL

- [ ] **步骤 3：实现 `src/guard/audit_log.py`**

```python
from __future__ import annotations

import aiosqlite
from datetime import datetime, timezone

from src.guard.rule_matrix import AuditDecision, FileAccessRequest, PathCategory


class AuditLog:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
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
        """)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def record(
        self,
        request: FileAccessRequest,
        decision: AuditDecision,
        path_category: PathCategory,
        reason: str,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            "INSERT INTO audit_log "
            "(timestamp, task_id, agent_id, path, operation, path_category, decision, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                timestamp,
                request.task_id,
                request.agent_id,
                request.path,
                request.operation.value,
                path_category.value,
                decision.value,
                reason,
            ),
        )
        await self._conn.commit()

    async def get_by_task(self, task_id: str, limit: int = 100) -> list[dict]:
        cursor = await self._conn.execute(
            "SELECT * FROM audit_log WHERE task_id = ? ORDER BY id DESC LIMIT ?",
            (task_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_denied(self, limit: int = 50) -> list[dict]:
        cursor = await self._conn.execute(
            "SELECT * FROM audit_log WHERE decision = 'deny' ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_escalated(self, limit: int = 50) -> list[dict]:
        cursor = await self._conn.execute(
            "SELECT * FROM audit_log WHERE decision = 'escalate' ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_recent(self, limit: int = 50) -> list[dict]:
        cursor = await self._conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/guard/test_audit_log.py -v`
预期：PASS

- [ ] **步骤 5：运行全量测试**

运行：`python -m pytest tests/ -v --tb=short`
预期：全部通过（含 Phase 1-3 回归）

- [ ] **步骤 6：Commit**

```bash
git add src/guard/audit_log.py tests/guard/test_audit_log.py
git commit -m "feat(guard): AuditLog 审计日志 SQLite 持久化"
```

---

### 任务 7：全量回归验证 + .gitignore 更新 + pyproject.toml 检查

- [ ] **步骤 1：运行全量测试**

```bash
python -m pytest tests/ -v --tb=short
```
预期：全部通过，无回归

- [ ] **步骤 2：清理临时文件**

```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
```

- [ ] **步骤 3：检查 .gitignore 完整性**

确认 `.gitignore` 已包含：`*.db`、`__pycache__/`、`lightning_logs/`、`*.pkl`、`config.yaml`、`*.key`、`*.local.yaml`

- [ ] **步骤 4：Commit（如有改动）**

```bash
git add -A && git diff --cached --quiet || git commit -m "chore: Phase 4 全量回归验证通过"
```
