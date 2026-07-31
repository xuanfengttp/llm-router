# Phase 2: 延迟监控与预测模型 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建 LLM API 延迟的持续监控与 TFT 时序预测系统，输出分位数预测 + 可预测性评分

**架构：** 定期探测 → 特征工程（时间/统计/潮汐）→ TFT 分位数回归 → 可预测性评分。模型通过 Conformal Prediction 校准置信区间。

**技术栈：** Python 3.12 + NeuralForecast (TFT) + numpy/pandas + aiosqlite + aiohttp

---

## 全局约束

- **不可变模式**：D-Bus 模型层使用 `frozen=True, slots=True` dataclass（与 Phase 1 一致）
- **加密**：API Key 使用 Fernet 加密存储
- **TDD**：每个任务先写测试再写代码
- **类型注解**：所有公开函数必须有完整类型注解
- **import**：所有导入使用绝对导入（`from src.xxx import`）
- **python -m pytest**：使用此命令运行测试
- **git commit**：每个任务完成后单独提交，使用 Conventional Commits 中文格式
- **conftest.py 复用**：多个测试文件共用的 fixture 提升到 `tests/conftest.py`
- **DB 字段**：SQLite 表无需显示 `id` 自增键，除非真的有按 id 查询/更新的需求
- **表结构**：latency_history 表已存在（Phase 1），新表统一用 `CREATE TABLE IF NOT EXISTS`，列不建议用 nullable，设字段默认值

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/config/models.py` | (修改) 新增 `LatencyRecord` dataclass |
| `src/network/probe.py` | (修改) `ProbeResult.timestamp` 改为 UTC ISO 格式 |
| `src/config/store.py` | (修改) 新增 timeseries 表、`save_latency_records` / `load_latency_series` 方法 |
| `src/prediction/__init__.py` | (创建) 模块入口 |
| `src/prediction/features.py` | (创建) 特征工程：从时序数据提取时间/统计/潮汐特征 |
| `src/prediction/model.py` | (创建) TFT 模型包装器：训练、分位数预测、可预测性评分 |
| `src/prediction/engine.py` | (创建) 预测引擎：orchestrate 采集 → 特征 → 推断 → 评分 |
| `src/monitor/__init__.py` | (创建) 模块入口 |
| `src/monitor/scheduler.py` | (创建) 延迟探测调度器：定时探测 + 写入 timeseries |
| `tests/prediction/__init__.py` | (创建) |
| `tests/prediction/test_features.py` | (创建) 特征工程测试 |
| `tests/prediction/test_model.py` | (创建) TFT 模型测试 |
| `tests/prediction/test_engine.py` | (创建) 预测引擎测试 |
| `tests/monitor/__init__.py` | (创建) |
| `tests/monitor/test_scheduler.py` | (创建) 调度器测试 |
| `tests/network/test_probe.py` | (修改) 验证 UTC 时间戳 |
| `tests/config/test_store.py` | (修改) timeseries 表测试 |
| `tests/conftest.py` | (修改) 添加公共 fixture |

---

### 任务 1：数据模型 — LatencyRecord 与 UTC 时间戳

**文件：**
- 修改：`src/config/models.py`（新增 `LatencyRecord`）
- 修改：`src/network/probe.py`（`ProbeResult.timestamp` → UTC）
- 测试：`tests/config/test_models.py`（新增 `TestLatencyRecord`）
- 测试：`tests/network/test_probe.py`（修改时间戳断言）

- [ ] **步骤 1：编写失败的测试**

在 `tests/config/test_models.py` 末尾追加：

```python
from datetime import datetime, timezone

from src.config.models import LatencyRecord


class TestLatencyRecord:
    """LatencyRecord 数据模型测试."""

    def test_create_record_with_required_fields(self):
        """仅必填字段创建记录."""
        record = LatencyRecord(
            provider="openai",
            model="gpt-4o",
            latency_ms=320.5,
        )
        assert record.provider == "openai"
        assert record.model == "gpt-4o"
        assert record.latency_ms == 320.5
        assert record.success is True
        assert record.error is None

    def test_create_record_with_all_fields(self):
        """全字段创建记录."""
        ts = "2026-07-31T12:00:00Z"
        record = LatencyRecord(
            provider="anthropic",
            model="claude-opus-5",
            latency_ms=850.0,
            success=False,
            error="Connection timeout",
            timestamp=ts,
        )
        assert record.provider == "anthropic"
        assert record.model == "claude-opus-5"
        assert record.latency_ms == 850.0
        assert record.success is False
        assert record.error == "Connection timeout"
        assert record.timestamp == ts

    def test_record_default_timestamp_is_utc_now(self):
        """默认时间戳为当前 UTC 时间."""
        before = datetime.now(timezone.utc)
        record = LatencyRecord(provider="p", model="m", latency_ms=100.0)
        after = datetime.now(timezone.utc)
        ts = datetime.fromisoformat(record.timestamp)
        assert before <= ts <= after

    def test_record_is_immutable(self):
        """LatencyRecord 为不可变对象."""
        record = LatencyRecord(provider="p", model="m", latency_ms=100.0)
        with pytest.raises(Exception):
            record.latency_ms = 200.0  # type: ignore[misc]

    def test_record_equality_by_value(self):
        """同值记录相等."""
        r1 = LatencyRecord(provider="a", model="x", latency_ms=100.0, timestamp="2026-01-01T00:00:00Z")
        r2 = LatencyRecord(provider="a", model="x", latency_ms=100.0, timestamp="2026-01-01T00:00:00Z")
        assert r1 == r2

    def test_record_hashable(self):
        """记录可哈希."""
        r1 = LatencyRecord(provider="a", model="x", latency_ms=100.0, timestamp="2026-01-01T00:00:00Z")
        r2 = LatencyRecord(provider="a", model="x", latency_ms=100.0, timestamp="2026-01-01T00:00:00Z")
        assert hash(r1) == hash(r2)
```

在 `tests/network/test_probe.py` 中修改测试 `TestProbeResult.test_success_result` —— 断言 `result.timestamp` 是 UTC ISO 格式字符串（以 `Z` 结尾或 `+00:00`）：

```python
def test_timestamp_is_utc_iso_format(self):
    """ProbeResult 时间戳为 UTC ISO 8601 格式."""
    result = ProbeResult(provider="t", model="m", success=True, latency_ms=10.0)
    ts = result.timestamp
    # 必须以 Z 结尾或以 +00:00 结尾
    assert ts.endswith("Z") or ts.endswith("+00:00")
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert dt.tzinfo is not None
```

运行：`python -m pytest tests/config/test_models.py::TestLatencyRecord tests/network/test_probe.py::TestProbeResult::test_timestamp_is_utc_iso_format -v`
预期：FAIL（LatencyRecord 类不存在 / ProbeResult timestamp 格式不是 UTC）

- [ ] **步骤 3：编写最少实现代码**

在 `src/config/models.py` 末尾追加：

```python
@dataclass(frozen=True, slots=True)
class LatencyRecord:
    """单次延迟探测的持久化记录.

    Attributes:
        provider: Provider 名称
        model: 模型名称
        latency_ms: 延迟毫秒数
        success: 探测是否成功
        error: 错误信息（成功时为 None）
        timestamp: UTC ISO 8601 时间戳
    """

    provider: str
    model: str
    latency_ms: float
    success: bool = True
    error: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )
```

在 `src/network/probe.py` 中修改 `ProbeResult.timestamp` 的 default_factory：

```python
import time as _time_mod  # 不改动现有 import

# 在 ProbeResult 类中，将 timestamp 的 default_factory 改为：
timestamp: str = field(
    default_factory=lambda: _time_mod.strftime(
        "%Y-%m-%dT%H:%M:%SZ", _time_mod.gmtime()
    )
)
```

运行：`python -m pytest tests/config/test_models.py::TestLatencyRecord tests/network/test_probe.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add tests/config/test_models.py tests/network/test_probe.py src/config/models.py src/network/probe.py
git commit -m "feat(config): 新增 LatencyRecord 数据模型 + ProbeResult UTC 时间戳"
```

---

### 任务 2：SQLite timeseries 表 + LatencyStore

**文件：**
- 修改：`src/config/store.py`（新增 timeseries 表 + `save_latency_records` / `load_latency_series`）
- 测试：`tests/config/test_store.py`（新增 timeseries 相关测试）

- [ ] **步骤 1：编写失败的测试**

在 `tests/config/test_store.py` 末尾追加：

```python
from src.config.models import LatencyRecord


class TestConfigStoreTimeseries:
    """ConfigStore timeseries 表测试."""

    @pytest.fixture
    async def store_with_db(self, temp_dir):
        """创建已初始化 DB 的 ConfigStore."""
        from src.config.crypto import generate_key
        from src.config.store import ConfigStore

        key = generate_key()
        cipher = KeyCipher(key)
        store = ConfigStore(
            config_path=temp_dir / "config.yaml",
            cipher=cipher,
            db_path=temp_dir / "test_ts.db",
        )
        await store.init_db()
        yield store
        await store.close()

    @pytest.mark.asyncio
    async def test_save_latency_records(self, store_with_db):
        """批量写入延迟记录."""
        records = [
            LatencyRecord(provider="openai", model="gpt-4o", latency_ms=320.0),
            LatencyRecord(provider="openai", model="gpt-4o-mini", latency_ms=150.0),
            LatencyRecord(provider="anthropic", model="claude-opus-5", latency_ms=850.0),
        ]
        await store_with_db.save_latency_records(records)

    @pytest.mark.asyncio
    async def test_load_latency_series_default_100(self, store_with_db):
        """加载延迟时序，默认返回最近 100 条."""
        records = [
            LatencyRecord(
                provider="openai", model="gpt-4o", latency_ms=float(i),
                timestamp=f"2026-07-31T12:{i:02d}:00Z",
            )
            for i in range(150)
        ]
        await store_with_db.save_latency_records(records)
        result = await store_with_db.load_latency_series("openai", "gpt-4o")
        assert len(result) == 100
        # 应返回时间最早的 100 条（按 ASC 排序最多 100 条）
        assert result[0].latency_ms == 0.0
        assert result[-1].latency_ms == 99.0

    @pytest.mark.asyncio
    async def test_load_latency_series_custom_limit(self, store_with_db):
        """自定义返回数量."""
        records = [
            LatencyRecord(
                provider="openai", model="gpt-4o", latency_ms=float(i),
                timestamp=f"2026-07-31T12:{i:02d}:00Z",
            )
            for i in range(50)
        ]
        await store_with_db.save_latency_records(records)
        result = await store_with_db.load_latency_series("openai", "gpt-4o", limit=10)
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_load_latency_series_empty(self, store_with_db):
        """未找到记录时返回空列表."""
        result = await store_with_db.load_latency_series("unknown", "unknown")
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_save_latency_records_empty_list(self, store_with_db):
        """空列表写入不报错."""
        await store_with_db.save_latency_records([])

    @pytest.mark.asyncio
    async def test_latency_history_unchanged(self, store_with_db):
        """验证原有 latency_history 表不受影响."""
        await store_with_db.record_latency("openai", "gpt-4o", 300.0)
        history = await store_with_db.get_latency_history("openai", "gpt-4o")
        assert len(history) == 1
```

运行：`python -m pytest tests/config/test_store.py::TestConfigStoreTimeseries -v`
预期：FAIL（save_latency_records / load_latency_series 方法不存在）

- [ ] **步骤 3：编写最少实现代码**

在 `src/config/store.py` 的 `init_db` 方法中，在现有 `CREATE TABLE` 语句后追加：

```python
CREATE TABLE IF NOT EXISTS latency_timeseries (
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    success INTEGER NOT NULL DEFAULT 1,
    error TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_timeseries_provider_model_ts
    ON latency_timeseries(provider, model, timestamp ASC);
```

在 `ConfigStore` 类末尾追加：

```python
async def save_latency_records(self, records: list[LatencyRecord]) -> None:
    """批量写入延迟时序记录."""
    if not records:
        return
    await self._conn.executemany(
        "INSERT INTO latency_timeseries (provider, model, latency_ms, success, error, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (r.provider, r.model, r.latency_ms, int(r.success), (r.error or ""), r.timestamp)
            for r in records
        ],
    )
    await self._conn.commit()

async def load_latency_series(
    self, provider: str, model: str, limit: int = 100
) -> list[LatencyRecord]:
    """加载指定模型的延迟时序，按时间升序返回最近 N 条.

    注意：返回的是一个子查询结果 —— 先按 timestamp DESC
    取最近 limit 条，再按 timestamp ASC 排序以确保时间顺序。
    """
    cursor = await self._conn.execute(
        "SELECT provider, model, latency_ms, success, error, timestamp "
        "FROM (SELECT * FROM latency_timeseries "
        "      WHERE provider = ? AND model = ? "
        "      ORDER BY timestamp DESC LIMIT ?) "
        "ORDER BY timestamp ASC",
        (provider, model, limit),
    )
    rows = await cursor.fetchall()
    return [
        LatencyRecord(
            provider=row["provider"],
            model=row["model"],
            latency_ms=row["latency_ms"],
            success=bool(row["success"]),
            error=row["error"] if row["error"] else None,
            timestamp=row["timestamp"],
        )
        for row in rows
    ]
```

运行：`python -m pytest tests/config/test_store.py::TestConfigStoreTimeseries -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add tests/config/test_store.py src/config/store.py
git commit -m "feat(config): SQLite timeseries 表 + LatencyRecord 批量读写"
```

---

### 任务 3：延迟探测调度器 (MonitorScheduler)

**文件：**
- 创建：`src/monitor/__init__.py`
- 创建：`src/monitor/scheduler.py`
- 创建：`tests/monitor/__init__.py`
- 创建：`tests/monitor/test_scheduler.py`
- 修改：`tests/conftest.py`（提升公共 fixture）

- [ ] **步骤 1：编写失败的测试**

```python
# tests/monitor/test_scheduler.py
from __future__ import annotations

import asyncio

import pytest

from src.config.models import ProviderConfig
from src.monitor.scheduler import MonitorScheduler


class TestMonitorScheduler:
    """延迟探测调度器测试."""

    def test_create_scheduler(self):
        """创建调度器实例."""
        scheduler = MonitorScheduler(interval_seconds=60)
        assert scheduler.interval_seconds == 60
        assert scheduler.is_running is False

    def test_default_interval(self):
        """默认探测间隔."""
        scheduler = MonitorScheduler()
        assert scheduler.interval_seconds == 30

    @pytest.mark.asyncio
    async def test_probe_callback_receives_results(self):
        """探测回调收到结果."""
        results: list = []
        scheduler = MonitorScheduler(interval_seconds=0.1)

        async def collect(records):
            results.extend(records)

        scheduler.on_probe(collect)

        # 使用空 Provider 列表，验证回调机制
        task = asyncio.create_task(scheduler.start([]))
        await asyncio.sleep(0.3)
        await scheduler.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # 空 Provider 列表不产生结果，但调度器正常运行
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self):
        """调度器启动/停止生命周期."""
        scheduler = MonitorScheduler(interval_seconds=1.0)
        assert scheduler.is_running is False

        task = asyncio.create_task(scheduler.start([]))
        await asyncio.sleep(0.05)
        assert scheduler.is_running is True

        await scheduler.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_multiple_stop_is_idempotent(self):
        """重复停止不报错."""
        scheduler = MonitorScheduler(interval_seconds=1.0)
        task = asyncio.create_task(scheduler.start([]))
        await asyncio.sleep(0.05)
        await scheduler.stop()
        await scheduler.stop()  # 第二次无害
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_multiple_callbacks_invoked(self):
        """多个回调都被触发."""
        results_a: list = []
        results_b: list = []
        scheduler = MonitorScheduler(interval_seconds=0.1)

        async def cb_a(records):
            results_a.extend(records)

        async def cb_b(records):
            results_b.extend(records)

        scheduler.on_probe(cb_a)
        scheduler.on_probe(cb_b)

        task = asyncio.create_task(scheduler.start([]))
        await asyncio.sleep(0.3)
        await scheduler.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
```

运行：`python -m pytest tests/monitor/test_scheduler.py -v`
预期：FAIL（MonitorScheduler 模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/monitor/__init__.py
from src.monitor.scheduler import MonitorScheduler

__all__ = ["MonitorScheduler"]
```

```python
# src/monitor/scheduler.py
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from src.config.models import LatencyRecord, ProviderConfig
from src.network.probe import LatencyProbe

ProbeCallback = Callable[[list[LatencyRecord]], Awaitable[None]]


class MonitorScheduler:
    """定时延迟探测调度器.

    每 interval_seconds 秒对所有 Provider 执行连通性探测，
    结果通过回调通知，写入 timeseries 数据库。

    用法:
        scheduler = MonitorScheduler(interval_seconds=30)
        scheduler.on_probe(lambda records: store.save_latency_records(records))
        await scheduler.start(providers)
        # ... 运行中 ...
        await scheduler.stop()
    """

    def __init__(self, interval_seconds: float = 30) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._callbacks: list[ProbeCallback] = []
        self._probe = LatencyProbe(timeout_seconds=10.0)

    @property
    def is_running(self) -> bool:
        return self._running

    def on_probe(self, callback: ProbeCallback) -> None:
        """注册探测结果回调."""
        self._callbacks.append(callback)

    async def start(self, providers: list[ProviderConfig]) -> None:
        """启动定时探测循环."""
        self._running = True
        try:
            while self._running:
                if providers:
                    probe_results = await self._probe.probe_all(providers)
                    records = [
                        LatencyRecord(
                            provider=r.provider,
                            model=r.model,
                            latency_ms=r.latency_ms or 0.0,
                            success=r.success,
                            error=r.error,
                            timestamp=r.timestamp,
                        )
                        for r in probe_results
                    ]
                    for cb in self._callbacks:
                        try:
                            await cb(records)
                        except Exception:
                            pass  # 回调异常不影响调度循环

                await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    async def stop(self) -> None:
        """停止调度循环."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
```

运行：`python -m pytest tests/monitor/test_scheduler.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/monitor/ tests/monitor/
git commit -m "feat(monitor): 延迟探测调度器 — 定时探测 + 回调通知"
```

---

### 任务 4：特征工程 (FeatureExtractor)

**文件：**
- 创建：`src/prediction/__init__.py`
- 创建：`src/prediction/features.py`
- 创建：`tests/prediction/__init__.py`
- 创建：`tests/prediction/test_features.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/prediction/test_features.py
from __future__ import annotations

import pytest

from src.config.models import LatencyRecord
from src.prediction.features import FeatureExtractor


class TestFeatureExtractor:
    """特征提取器测试."""

    @pytest.fixture
    def sample_records(self) -> list[LatencyRecord]:
        """生成 48 条模拟延迟记录（每 30 分钟一条，含潮汐模式）."""
        records: list[LatencyRecord] = []
        for i in range(48):
            hour = i // 2  # 每半小时
            # 模拟潮汐模式: 白天 (8-18) 延迟高，晚上低
            base = 500.0 if 8 <= hour < 18 else 200.0
            latency = base + (i % 5) * 20.0  # 加一点噪声
            records.append(
                LatencyRecord(
                    provider="openai",
                    model="gpt-4o",
                    latency_ms=latency,
                    timestamp=f"2026-07-30T{hour:02d}:{(i%2)*30:02d}:00Z",
                )
            )
        return records

    def test_extract_features_shape(self, sample_records):
        """特征提取输出正确的行数."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        # 每条记录对应一行特征
        assert len(df) == 48

    def test_required_columns_present(self, sample_records):
        """包含所有必需的特征列."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        required = [
            "y",                     # 目标：延迟值
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "rolling_mean_6",
            "rolling_std_6",
            "lag_1",
            "lag_2",
            "lag_12",                # 约 6 小时前
        ]
        for col in required:
            assert col in df.columns, f"缺失列: {col}"

    def test_hour_of_day_feature(self, sample_records):
        """hour_of_day 特征在 0-23 范围内."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        assert df["hour_of_day"].between(0, 23).all()

    def test_is_weekend_feature(self, sample_records):
        """is_weekend 是 0 或 1."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        assert set(df["is_weekend"].unique()).issubset({0, 1})

    def test_lag_features_exist(self, sample_records):
        """lag 特征存在且部分为 NaN（前几行无法计算 lag）."""
        extractor = FeatureExtractor()
        df = extractor.extract(sample_records)
        # lag_1 的第一行是 NaN
        assert df["lag_1"].iloc[0] != df["lag_1"].iloc[0]  # NaN != NaN is True

    def test_empty_records(self):
        """空输入返回空 DataFrame."""
        extractor = FeatureExtractor()
        df = extractor.extract([])
        assert len(df) == 0

    def test_single_record(self):
        """单条记录仍有特征输出（lag/rolling 为 NaN）."""
        records = [LatencyRecord(provider="o", model="m", latency_ms=100.0)]
        extractor = FeatureExtractor()
        df = extractor.extract(records)
        assert len(df) == 1
```

运行：`python -m pytest tests/prediction/test_features.py -v`
预期：FAIL（FeatureExtractor 模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/prediction/__init__.py
"""延迟预测模块：特征工程 + TFT 模型 + 预测引擎."""
```

```python
# src/prediction/features.py
from __future__ import annotations

import pandas as pd

from src.config.models import LatencyRecord


class FeatureExtractor:
    """从延迟时序数据提取特征用于 TFT 模型.

    特征分类:
    - 时间特征: hour_of_day, day_of_week, is_weekend
    - 统计特征: rolling_mean_6, rolling_std_6 (6点窗口 ≈ 3小时，按30分钟间隔)
    - lag特征: lag_1, lag_2, lag_12

    用法:
        records = await store.load_latency_series("openai", "gpt-4o", limit=500)
        df = FeatureExtractor().extract(records)
    """

    def extract(self, records: list[LatencyRecord]) -> pd.DataFrame:
        """从延迟记录中提取特征矩阵."""
        if not records:
            return pd.DataFrame()

        # 转为 DataFrame
        df = pd.DataFrame(
            [
                {"timestamp": r.timestamp, "y": r.latency_ms}
                for r in records
            ]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)

        # ── 时间特征 ──
        df["hour_of_day"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # ── 统计特征 (滚动窗口) ──
        df["rolling_mean_6"] = df["y"].rolling(window=6, min_periods=1).mean()
        df["rolling_std_6"] = df["y"].rolling(window=6, min_periods=1).std().fillna(0.0)

        # ── Lag 特征 ──
        df["lag_1"] = df["y"].shift(1)   # 上一次
        df["lag_2"] = df["y"].shift(2)   # 前两次
        df["lag_12"] = df["y"].shift(12) # 约 6 小时前（30分钟 * 12 = 6h）

        return df
```

运行：`python -m pytest tests/prediction/test_features.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/prediction/ tests/prediction/
git commit -m "feat(prediction): 特征工程 — 时间/统计/lag 特征提取"
```

---

### 任务 5：TFT 预测模型 (LatencyPredictor)

**文件：**
- 创建：`src/prediction/model.py`
- 测试：`tests/prediction/test_model.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/prediction/test_model.py
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.prediction.model import LatencyPredictor, PredictabilityScore


class TestPredictabilityScore:
    """可预测性评分测试."""

    def test_perfect_prediction(self):
        """完美预测得分为 1.0."""
        result = PredictabilityScore.compute(
            actual=np.array([1.0, 2.0, 3.0]),
            predicted=np.array([1.0, 2.0, 3.0]),
        )
        assert result == pytest.approx(1.0)

    def test_no_predictability(self):
        """无预测能力时得分接近 0."""
        # 残差方差 ≈ 总方差 → 得分 ≈ 0
        actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        # 总是预测均值
        predicted = np.array([3.0, 3.0, 3.0, 3.0, 3.0])
        result = PredictabilityScore.compute(actual, predicted)
        assert result == pytest.approx(0.0)

    def test_partial_predictability(self):
        """部分可预测."""
        actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        predicted = np.array([1.5, 2.5, 3.0, 3.5, 4.5])
        result = PredictabilityScore.compute(actual, predicted)
        assert 0.0 < result < 1.0

    def test_empty_input_returns_zero(self):
        """空输入返回 0."""
        result = PredictabilityScore.compute(
            actual=np.array([]), predicted=np.array([])
        )
        assert result == 0.0


class TestLatencyPredictor:
    """TFT 延迟预测器测试."""

    @pytest.fixture
    def sample_features(self) -> pd.DataFrame:
        """生成模拟特征数据（含潮汐模式）."""
        np.random.seed(42)
        n = 200  # 需要足够多数据让 TFT 学习
        hours = np.tile(np.arange(24), (n // 24) + 1)[:n]
        # 潮汐模式：白天高延迟，晚上低延迟
        y = np.where((hours >= 8) & (hours < 18), 500, 200).astype(float)
        y += np.random.normal(0, 30, n)  # 噪声

        df = pd.DataFrame({
            "y": y,
            "hour_of_day": hours,
            "day_of_week": hours % 7,
            "is_weekend": (hours % 7 >= 5).astype(int),
            "rolling_mean_6": pd.Series(y).rolling(6, min_periods=1).mean(),
            "rolling_std_6": pd.Series(y).rolling(6, min_periods=1).std().fillna(0.0),
            "lag_1": pd.Series(y).shift(1).fillna(y[0]),
            "lag_2": pd.Series(y).shift(2).fillna(y[0]),
            "lag_12": pd.Series(y).shift(12).fillna(y[0]),
        })
        # 添加 timestamp（TFT 需要）
        df["timestamp"] = pd.date_range(
            "2026-07-30", periods=n, freq="30min", tz="UTC"
        )
        # 添加 unique_id（NeuralForecast 要求）
        df["unique_id"] = "gpt-4o"
        return df

    def test_create_predictor(self):
        """创建预测器实例."""
        predictor = LatencyPredictor(horizon=6, lookback=24)
        assert predictor.horizon == 6
        assert predictor.lookback == 24
        assert not predictor.is_trained

    def test_default_horizon_lookback(self):
        """默认 horizon=6, lookback=48."""
        p = LatencyPredictor()
        assert p.horizon == 6
        assert p.lookback == 48

    def test_train_updates_trained_flag(self, sample_features):
        """训练后 is_trained 为 True."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        assert predictor.is_trained

    def test_predict_returns_quantiles(self, sample_features):
        """预测返回分位数字典."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        result = predictor.predict(sample_features)

        assert isinstance(result, dict)
        for q in ["p10", "p25", "p50", "p75", "p90"]:
            assert q in result
            assert isinstance(result[q], float)

    def test_predict_quantiles_monotonic(self, sample_features):
        """分位数单调递增: p10 < p25 < p50 < p75 < p90."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        result = predictor.predict(sample_features)

        assert result["p10"] <= result["p25"] <= result["p50"] <= result["p75"] <= result["p90"]

    def test_predict_without_train_raises(self):
        """未训练就预测应抛出异常."""
        predictor = LatencyPredictor()
        df = pd.DataFrame({"y": [100.0], "unique_id": ["test"], "timestamp": pd.Timestamp.now(tz="UTC")})
        with pytest.raises(RuntimeError, match="not trained"):
            predictor.predict(df)

    def test_compute_predictability(self, sample_features):
        """计算可预测性得分."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        score = predictor.compute_predictability(sample_features)
        assert 0.0 <= score <= 1.0

    def test_save_and_load(self, temp_dir, sample_features):
        """模型保存后重新加载."""
        predictor = LatencyPredictor(horizon=3, lookback=24)
        predictor.train(sample_features)
        predict_before = predictor.predict(sample_features)

        path = temp_dir / "model.pkl"
        predictor.save(path)

        loaded = LatencyPredictor.load(path)
        assert loaded.is_trained
        predict_after = loaded.predict(sample_features)
        assert predict_after["p50"] == pytest.approx(predict_before["p50"])
```

运行：`python -m pytest tests/prediction/test_model.py -v`
预期：FAIL（LatencyPredictor 模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/prediction/model.py
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from neuralforecast import NeuralForecast
from neuralforecast.models import TFT


class PredictabilityScore:
    """可预测性评分：1 - (残差方差 / 总方差).

    得分 0 = 完全随机不可预测
    得分 1 = 完美可预测
    """

    @staticmethod
    def compute(actual: np.ndarray, predicted: np.ndarray) -> float:
        if len(actual) == 0 or len(predicted) == 0:
            return 0.0
        residual_var = np.var(actual - predicted)
        total_var = np.var(actual)
        if total_var == 0:
            return 1.0  # 常数信号，完美可预测
        score = 1.0 - (residual_var / total_var)
        return float(max(0.0, min(1.0, score)))


class LatencyPredictor:
    """TFT 延迟预测器.

    封装 NeuralForecast TFT 模型，提供训练、预测、可预测性评分、
    模型持久化等能力。

    用法:
        predictor = LatencyPredictor(horizon=6, lookback=48)
        df = feature_extractor.extract(records)
        df["unique_id"] = "gpt-4o"
        predictor.train(df)
        prediction = predictor.predict(df)
        print(f"p50 预测: {prediction['p50']:.1f}ms")
        print(f"可预测性: {predictor.compute_predictability(df):.2f}")
    """

    def __init__(self, horizon: int = 6, lookback: int = 48) -> None:
        self.horizon = horizon
        self.lookback = lookback
        self._model: NeuralForecast | None = None
        self._trained = False

    @property
    def is_trained(self) -> bool:
        return self._trained

    def train(self, df: pd.DataFrame) -> None:
        """训练 TFT 模型.

        Args:
            df: 包含 'unique_id', 'timestamp', 'y' 及特征列的数据集
        """
        n_rows = len(df)
        # TFT 需要合理的数据量，自适应调整 horizon
        if n_rows < self.lookback + self.horizon:
            # 数据不足：缩小 horizon
            effective_horizon = max(1, (n_rows - self.lookback) // 2)
        else:
            effective_horizon = self.horizon

        if effective_horizon < 1:
            effective_horizon = 1

        model = TFT(
            h=effective_horizon,
            input_size=self.lookback,
            hidden_size=32,
            n_head=4,
            dropout=0.1,
            loss="quantile",
            learning_rate=1e-3,
            max_steps=100,
            val_check_steps=10,
            early_stop_patience_steps=5,
            scaler_type="standard",
        )
        self._model = NeuralForecast(models=[model], freq="30min")
        self._model.fit(df=df)
        self._trained = True

    def predict(self, df: pd.DataFrame) -> dict[str, float]:
        """预测下一个 horizon 步的延迟分位数.

        Returns:
            {"p10": ..., "p25": ..., "p50": ..., "p75": ..., "p90": ...}
            各分位数的预测值（取第一个预测步）
        """
        if not self._trained or self._model is None:
            raise RuntimeError("模型尚未训练，请先调用 train()")

        forecast = self._model.predict(df)
        # TFT 量级回归输出多列，取第一个预测步 (step 0)
        # 列名格式: TFT-median, TFT-lo-90, TFT-lo-75, TFT-lo-50, TFT-hi-75, TFT-hi-90
        # TFT-median ≈ p50
        # TFT-lo-90 ≈ p10, TFT-lo-75 ≈ p25, TFT-lo-50 ≈ p50? -> 这是正太分布的约定
        # 实际上 NeuralForecast TFT quantile 输出：
        # TFT-median: p50
        # TFT-lo-90: p10 (90%概率高于此值 → 下10分位)
        # TFT-lo-75: p25 (75%概率高于此值 → 下25分位)
        # TFT-hi-75: p75 (75%概率低于此值 → 上75分位)
        # TFT-hi-90: p90 (90%概率低于此值 → 上90分位)

        try:
            p50 = float(forecast["TFT-median"].iloc[0])
            p10 = float(forecast["TFT-lo-90"].iloc[0])
            p25 = float(forecast["TFT-lo-75"].iloc[0])
            p75 = float(forecast["TFT-hi-75"].iloc[0])
            p90 = float(forecast["TFT-hi-90"].iloc[0])
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"预测结果解析失败: {e}") from e

        return {"p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90}

    def compute_predictability(self, df: pd.DataFrame) -> float:
        """计算可预测性得分 (0-1).

        使用训练数据的残差方差 / 总方差。
        """
        if not self._trained or self._model is None:
            raise RuntimeError("模型尚未训练，请先调用 train()")

        forecast = self._model.predict(df)
        try:
            predicted = forecast["TFT-median"].values
            # 需要对齐：预测输出长度可能小于输入
            actual = df["y"].values[-len(predicted):]
            return PredictabilityScore.compute(actual, predicted)
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"可预测性计算失败: {e}") from e

    def save(self, path: Path) -> None:
        """保存模型到文件."""
        if self._model is None:
            raise RuntimeError("无模型可保存")
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "horizon": self.horizon,
                    "lookback": self.lookback,
                    "model": self._model,
                },
                f,
            )

    @classmethod
    def load(cls, path: Path) -> LatencyPredictor:
        """从文件加载模型."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        predictor = cls(
            horizon=data["horizon"],
            lookback=data["lookback"],
        )
        predictor._model = data["model"]
        predictor._trained = True
        return predictor
```

在 `pyproject.toml` 添加依赖：
```
"neuralforecast>=1.7",
"pandas>=2.0",
```

运行：`python -m pytest tests/prediction/test_model.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/prediction/model.py tests/prediction/test_model.py pyproject.toml
git commit -m "feat(prediction): TFT 延迟预测器 — 训练/分位数预测/可预测性评分"
```

---

### 任务 6：预测引擎 (PredictionEngine)

**文件：**
- 创建：`src/prediction/engine.py`
- 测试：`tests/prediction/test_engine.py`
- 修改：`tests/conftest.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/prediction/test_engine.py
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.config.models import LatencyRecord
from src.prediction.engine import LatencyPrediction, PredictionEngine


class TestLatencyPrediction:
    """预测结果数据类测试."""

    def test_create_prediction(self):
        pred = LatencyPrediction(
            provider="openai",
            model="gpt-4o",
            quantiles={"p10": 200.0, "p25": 280.0, "p50": 350.0, "p75": 450.0, "p90": 550.0},
            predictability=0.82,
            data_points_used=200,
        )
        assert pred.provider == "openai"
        assert pred.model == "gpt-4o"
        assert pred.p50 == 350.0
        assert pred.predictability == 0.82
        assert pred.quantiles is not None
        assert pred.data_points_used == 200


class TestPredictionEngine:
    """预测引擎测试."""

    @pytest.fixture
    def sample_records(self) -> list[LatencyRecord]:
        """生成足够多的训练数据."""
        records: list[LatencyRecord] = []
        for i in range(300):
            hour = i % 24
            base = 500.0 if 8 <= hour < 18 else 200.0
            latency = base + (i % 7) * 15.0
            timestamp = datetime(2026, 7, 30, 0, 0, 0, tzinfo=timezone.utc)
            timestamp = timestamp.replace(
                hour=hour, minute=(i % 4) * 15
            )
            records.append(
                LatencyRecord(
                    provider="openai",
                    model="gpt-4o",
                    latency_ms=latency,
                    timestamp=timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
            )
        records.sort(key=lambda r: r.timestamp)
        return records

    def test_create_engine(self):
        """创建预测引擎."""
        engine = PredictionEngine(horizon=3, lookback=24, min_data_points=50)
        assert engine.min_data_points == 50

    def test_predict_for_model(self, sample_records):
        """对单个模型执行预测."""
        engine = PredictionEngine(horizon=3, lookback=24, min_data_points=50)
        result = engine.predict_for_model("openai", "gpt-4o", sample_records)

        assert result is not None
        assert result.provider == "openai"
        assert result.model == "gpt-4o"
        assert result.p50 > 0
        assert 0.0 <= result.predictability <= 1.0

    def test_insufficient_data_returns_none(self):
        """数据不足返回 None."""
        engine = PredictionEngine(min_data_points=1000)
        few_records = [
            LatencyRecord(provider="o", model="m", latency_ms=100.0)
            for _ in range(5)
        ]
        result = engine.predict_for_model("o", "m", few_records)
        assert result is None

    def test_predict_providers(self, sample_records):
        """批量 Provider 预测."""
        engine = PredictionEngine(horizon=3, lookback=24, min_data_points=50)
        results = engine.predict_all(
            {"openai": {"gpt-4o": sample_records}}
        )
        assert "openai" in results
        assert "gpt-4o" in results["openai"]
```

运行：`python -m pytest tests/prediction/test_engine.py -v`
预期：FAIL（PredictionEngine 模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/prediction/engine.py
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.config.models import LatencyRecord
from src.prediction.features import FeatureExtractor
from src.prediction.model import LatencyPredictor


@dataclass(slots=True)
class LatencyPrediction:
    """单次延迟预测结果."""

    provider: str
    model: str
    quantiles: dict[str, float]
    predictability: float
    data_points_used: int

    @property
    def p50(self) -> float:
        return self.quantiles["p50"]

    @property
    def p90(self) -> float:
        return self.quantiles["p90"]


class PredictionEngine:
    """预测引擎：orchestrate 特征提取 → TFT 训练 → 预测 → 评分.

    对每个模型独立建模，因为不同模型有不同的延迟特性。

    用法:
        engine = PredictionEngine(horizon=6, lookback=48)
        records = await store.load_latency_series("openai", "gpt-4o", limit=500)
        prediction = engine.predict_for_model("openai", "gpt-4o", records)
        if prediction:
            print(f"p50 预测延迟: {prediction.p50:.1f}ms")
            print(f"可预测性: {prediction.predictability:.2f}")
    """

    def __init__(
        self,
        horizon: int = 6,
        lookback: int = 48,
        min_data_points: int = 100,
    ) -> None:
        self.horizon = horizon
        self.lookback = lookback
        self.min_data_points = min_data_points
        self._extractor = FeatureExtractor()
        self._predictors: dict[tuple[str, str], LatencyPredictor] = {}

    def predict_for_model(
        self,
        provider: str,
        model: str,
        records: list[LatencyRecord],
    ) -> LatencyPrediction | None:
        """对指定模型执行延迟预测.

        Returns:
            LatencyPrediction 或 None（数据不足时）
        """
        if len(records) < self.min_data_points:
            return None

        key = (provider, model)

        # 1. 特征工程
        df = self._extractor.extract(records)
        df["unique_id"] = f"{provider}/{model}"
        df = df.dropna(subset=["lag_1", "lag_2", "lag_12"])

        if len(df) < self.min_data_points:
            return None

        # 2. 训练 TFT
        predictor = LatencyPredictor(
            horizon=self.horizon, lookback=min(self.lookback, len(df) // 4)
        )
        predictor.train(df)

        # 3. 预测
        quantiles = predictor.predict(df)

        # 4. 可预测性评分
        predictability = predictor.compute_predictability(df)

        self._predictors[key] = predictor

        return LatencyPrediction(
            provider=provider,
            model=model,
            quantiles=quantiles,
            predictability=predictability,
            data_points_used=len(df),
        )

    def predict_all(
        self,
        data: dict[str, dict[str, list[LatencyRecord]]],
    ) -> dict[str, dict[str, LatencyPrediction | None]]:
        """对所有 Provider 的所有模型执行预测."""
        results: dict[str, dict[str, LatencyPrediction | None]] = {}
        for provider, models in data.items():
            results[provider] = {}
            for model_name, records in models.items():
                results[provider][model_name] = self.predict_for_model(
                    provider, model_name, records
                )
        return results
```

运行：`python -m pytest tests/prediction/test_engine.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/prediction/engine.py tests/prediction/test_engine.py
git commit -m "feat(prediction): 预测引擎 — 特征→训练→预测→评分全流程"
```

---

### 任务 7：依赖安装验证 + 全量测试 + .gitignore 更新

- [ ] **步骤 1：安装 Phase 2 新增依赖**

```bash
pip install neuralforecast pandas
```

- [ ] **步骤 2：运行全量测试**

```bash
python -m pytest tests/ -v
```

预期：全部通过

- [ ] **步骤 3：检查 .gitignore 是否需要更新**

确认 `*.pkl` 已在 gitignore 中（模型缓存文件），如果没有则添加。

- [ ] **步骤 4：Commit**

```bash
git add -A
git commit -m "chore: 安装 Phase 2 依赖 + 更新 .gitignore"
```
