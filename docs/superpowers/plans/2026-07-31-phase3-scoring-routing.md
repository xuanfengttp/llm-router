# Phase 3: 模型评分数据库 + 智能路由引擎 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建模型能力画像数据库（公开 benchmark 拉取 + 本地延迟融合）+ 可插拔路由策略引擎（6 种策略 + 匹配算法）

**架构：** ModelProfile（数值能力向量）→ ScoringDB（benchmark 拉取 + SQLite 本地融合）→ TaskProfile（任务需求模板）→ RoutingStrategy（可插拔策略接口）→ RouteEngine（硬约束过滤 + 加权评分 + 排序输出）

**技术栈：** Python 3.12 + aiohttp + aiosqlite + dataclasses

---

## 全局约束

- **不可变模式**：所有数据模型使用 `frozen=True, slots=True` dataclass（与 Phase 1/2 一致）
- **类型注解**：所有公开函数必须有完整类型注解
- **绝对 import**：`from src.xxx import`
- **TDD**：每个任务先写测试再写代码
- **YAGNI**：不添加计划外功能
- **python -m pytest**：使用此命令运行测试
- **git commit**：每个任务单独提交，Conventional Commits 中文格式
- **SQLite 表**：`CREATE TABLE IF NOT EXISTS`，列 NOT NULL 有默认值，无多余 id 列

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/config/models.py` | (修改) 新增 `ModelProfile` dataclass |
| `src/scoring/__init__.py` | (创建) 模块入口 |
| `src/scoring/profile.py` | (创建) ModelProfile 定义 + benchmark 数据拉取 |
| `src/scoring/database.py` | (创建) ScoringDB — 模型评分的 SQLite 读写 |
| `src/routing/__init__.py` | (创建) 模块入口 |
| `src/routing/task_profile.py` | (创建) TaskProfile 任务需求模板 |
| `src/routing/strategy.py` | (创建) RoutingStrategy 接口 + 6 种内置策略 |
| `src/routing/engine.py` | (创建) RouteEngine — 匹配算法 |
| `tests/scoring/__init__.py` | (创建) |
| `tests/scoring/test_profile.py` | (创建) ModelProfile + benchmark 测试 |
| `tests/scoring/test_database.py` | (创建) ScoringDB 测试 |
| `tests/routing/__init__.py` | (创建) |
| `tests/routing/test_task_profile.py` | (创建) TaskProfile 测试 |
| `tests/routing/test_strategy.py` | (创建) 路由策略测试 |
| `tests/routing/test_engine.py` | (创建) RouteEngine 集成测试 |
| `tests/conftest.py` | (修改) 添加公共 fixture |

---

### 任务 1：ModelProfile 数据模型 + Benchmark 拉取

**文件：**
- 创建：`src/scoring/__init__.py`
- 创建：`src/scoring/profile.py`
- 创建：`tests/scoring/__init__.py`
- 创建：`tests/scoring/test_profile.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/scoring/test_profile.py
from __future__ import annotations

import pytest

from src.scoring.profile import (
    BenchmarkData,
    BenchmarkFetcher,
    LocalMetrics,
    ModelProfile,
)


class TestBenchmarkData:
    """公开 Benchmark 数据测试."""

    def test_create_benchmark(self):
        bm = BenchmarkData(
            arena_elo=1287.5,
            coding_swebench=38.4,
            reasoning_mmlu=88.7,
            math_math=76.6,
        )
        assert bm.arena_elo == 1287.5
        assert bm.coding_swebench == 38.4
        assert bm.reasoning_mmlu == 88.7
        assert bm.math_math == 76.6
        # 可选字段默认值
        assert bm.instruction_follow == 0.0
        assert bm.multilingual == 0.0
        assert bm.tool_use == 0.0

    def test_benchmark_is_frozen(self):
        bm = BenchmarkData(arena_elo=100.0)
        with pytest.raises(Exception):
            bm.arena_elo = 200.0  # type: ignore[misc]

    def test_benchmark_to_dict(self):
        bm = BenchmarkData(arena_elo=1200.0, coding_swebench=40.0)
        d = bm.to_dict()
        assert d["arena_elo"] == 1200.0
        assert d["coding_swebench"] == 40.0


class TestLocalMetrics:
    """本地监控指标测试."""

    def test_create_local_metrics(self):
        lm = LocalMetrics(
            latency_p50_ms=320.0,
            latency_p95_ms=850.0,
            latency_p99_ms=1800.0,
            predicted_latency_ms=380.0,
            predictability=0.82,
            throughput_rpm=120.0,
            error_rate=0.003,
        )
        assert lm.latency_p50_ms == 320.0
        assert lm.predictability == 0.82
        assert lm.error_rate == 0.003

    def test_local_metrics_defaults(self):
        lm = LocalMetrics()
        assert lm.latency_p50_ms == 0.0
        assert lm.predictability == 0.0
        assert lm.error_rate == 0.0

    def test_local_metrics_update(self):
        """返回新实例（不可变模式）."""
        lm = LocalMetrics(latency_p50_ms=100.0)
        updated = lm.with_latency(p50_ms=200.0, p95_ms=300.0, p99_ms=400.0)
        assert updated.latency_p50_ms == 200.0
        assert updated.latency_p95_ms == 300.0
        assert lm.latency_p50_ms == 100.0  # 原实例不变


class TestModelProfile:
    """模型能力画像测试."""

    def test_create_profile(self):
        bm = BenchmarkData(arena_elo=1200.0, coding_swebench=40.0)
        lm = LocalMetrics(latency_p50_ms=320.0)
        profile = ModelProfile(
            provider="openai",
            model="gpt-4o",
            deployment="cloud",
            context_window=128000,
            cost_input_1k=0.0025,
            cost_output_1k=0.0100,
            benchmark=bm,
            local_metrics=lm,
        )
        assert profile.provider == "openai"
        assert profile.model == "gpt-4o"
        assert profile.benchmark.arena_elo == 1200.0
        assert profile.local_metrics.latency_p50_ms == 320.0

    def test_profile_is_frozen(self):
        profile = ModelProfile(
            provider="p", model="m", deployment="cloud",
            context_window=4096, cost_input_1k=0.0, cost_output_1k=0.0,
        )
        with pytest.raises(Exception):
            profile.model = "new"  # type: ignore[misc]

    def test_profile_with_local_metrics(self):
        """更新本地监控数据."""
        profile = ModelProfile(
            provider="p", model="m", deployment="cloud",
            context_window=4096, cost_input_1k=0.0, cost_output_1k=0.0,
        )
        new_lm = LocalMetrics(latency_p50_ms=250.0, predictability=0.9)
        updated = profile.with_local_metrics(new_lm)
        assert updated.local_metrics.latency_p50_ms == 250.0
        assert profile.local_metrics.latency_p50_ms == 0.0  # 原实例不变

    def test_profile_capability_vector(self):
        """能力向量提取."""
        bm = BenchmarkData(
            arena_elo=1250.0, coding_swebench=41.0,
            reasoning_mmlu=88.0, math_math=76.0,
        )
        profile = ModelProfile(
            provider="p", model="m", deployment="cloud",
            context_window=128000, cost_input_1k=0.005, cost_output_1k=0.010,
            benchmark=bm,
        )
        vec = profile.capability_vector()
        assert "coding" in vec
        assert "reasoning" in vec
        assert "math" in vec
        assert vec["coding"] == 41.0
        assert vec["reasoning"] == 88.0
        assert vec["math"] == 76.0


class TestBenchmarkFetcher:
    """Benchmark 数据拉取器测试."""

    def test_fetcher_has_default_sources(self):
        fetcher = BenchmarkFetcher()
        assert len(fetcher.sources) >= 2  # Chatbot Arena + OpenRouter

    def test_parse_arena_response(self):
        """解析 Chatbot Arena 格式的响应."""
        fetcher = BenchmarkFetcher()
        sample = {
            "gpt-4o": {
                "arena_score": 1287,
                "coding": 81.4,
                "math": 72.3,
                "reasoning": 85.6,
            }
        }
        result = fetcher._parse_arena_data(sample)
        assert "gpt-4o" in result
        assert result["gpt-4o"].arena_elo == 1287.0
        assert result["gpt-4o"].coding_swebench == 81.4

    def test_parse_openrouter_response(self):
        """解析 OpenRouter 格式的响应."""
        fetcher = BenchmarkFetcher()
        sample = {
            "data": [
                {
                    "slug": "gpt-4o",
                    "metrics": {
                        "coding": 80.0,
                        "reasoning": 88.0,
                        "instruction_following": 91.0,
                    }
                }
            ]
        }
        result = fetcher._parse_openrouter_data(sample)
        assert "gpt-4o" in result
        assert result["gpt-4o"].coding_swebench == 80.0
        assert result["gpt-4o"].instruction_follow == 91.0

    def test_merge_sources(self):
        """多数据源融合."""
        fetcher = BenchmarkFetcher()
        arena = {"gpt-4o": BenchmarkData(arena_elo=1287.0, coding_swebench=81.0)}
        openrouter = {"gpt-4o": BenchmarkData(coding_swebench=79.0, reasoning_mmlu=88.0)}
        merged = fetcher._merge_benchmarks([arena, openrouter])
        assert "gpt-4o" in merged
        # 优先使用第一个源的 arena_elo（仅 Arena 有）
        assert merged["gpt-4o"].arena_elo == 1287.0
        # coding 取平均值
        assert merged["gpt-4o"].coding_swebench == 80.0
```

运行：`python -m pytest tests/scoring/test_profile.py -v`
预期：FAIL（模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/scoring/__init__.py
"""模型评分子系统：Benchmark 拉取 + 本地监控融合."""
```

```python
# src/scoring/profile.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BenchmarkData:
    """公开 Benchmark 数值，从 Chatbot Arena / OpenRouter 自动拉取.

    所有分数归一化到 0-100 或标准 ELO 尺度。
    """

    arena_elo: float = 0.0
    coding_swebench: float = 0.0
    reasoning_mmlu: float = 0.0
    math_math: float = 0.0
    instruction_follow: float = 0.0
    multilingual: float = 0.0
    tool_use: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "arena_elo": self.arena_elo,
            "coding_swebench": self.coding_swebench,
            "reasoning_mmlu": self.reasoning_mmlu,
            "math_math": self.math_math,
            "instruction_follow": self.instruction_follow,
            "multilingual": self.multilingual,
            "tool_use": self.tool_use,
        }


@dataclass(frozen=True, slots=True)
class LocalMetrics:
    """本地持续监控指标."""

    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    predicted_latency_ms: float = 0.0
    predictability: float = 0.0
    throughput_rpm: float = 0.0
    error_rate: float = 0.0

    def with_latency(
        self, p50_ms: float, p95_ms: float, p99_ms: float
    ) -> LocalMetrics:
        return LocalMetrics(
            latency_p50_ms=p50_ms,
            latency_p95_ms=p95_ms,
            latency_p99_ms=p99_ms,
            predicted_latency_ms=self.predicted_latency_ms,
            predictability=self.predictability,
            throughput_rpm=self.throughput_rpm,
            error_rate=self.error_rate,
        )


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """模型能力画像：公开 benchmark + 本地监控 + 元信息."""

    provider: str
    model: str
    deployment: str  # "cloud" | "local" | "hybrid"
    context_window: int
    cost_input_1k: float
    cost_output_1k: float
    benchmark: BenchmarkData = field(default_factory=BenchmarkData)
    local_metrics: LocalMetrics = field(default_factory=LocalMetrics)

    def capability_vector(self) -> dict[str, float]:
        """提取能力向量，用于路由匹配."""
        bm = self.benchmark
        return {
            "coding": bm.coding_swebench,
            "reasoning": bm.reasoning_mmlu,
            "math": bm.math_math,
            "instruction": bm.instruction_follow,
            "multilingual": bm.multilingual,
            "tool_use": bm.tool_use,
            "arena_elo": bm.arena_elo,
        }

    def with_local_metrics(self, metrics: LocalMetrics) -> ModelProfile:
        return ModelProfile(
            provider=self.provider,
            model=self.model,
            deployment=self.deployment,
            context_window=self.context_window,
            cost_input_1k=self.cost_input_1k,
            cost_output_1k=self.cost_output_1k,
            benchmark=self.benchmark,
            local_metrics=metrics,
        )


class BenchmarkFetcher:
    """公开 Benchmark 数据拉取器.

    数据源：Chatbot Arena (lmsys) + OpenRouter rankings.
    支持本地缓存，避免频繁拉取。

    用法:
        fetcher = BenchmarkFetcher()
        benchmarks = await fetcher.fetch_all()
        # benchmarks: dict[str, BenchmarkData]
    """

    def __init__(self) -> None:
        self.sources = [
            "https://storage.googleapis.com/lmsys-arena-data/arena_ranking.json",
            "https://openrouter.ai/api/v1/rankings",
        ]

    def _parse_arena_data(self, raw: dict) -> dict[str, BenchmarkData]:
        """解析 Chatbot Arena JSON 格式."""
        results: dict[str, BenchmarkData] = {}
        for model_name, data in raw.items():
            results[model_name] = BenchmarkData(
                arena_elo=float(data.get("arena_score", 0)),
                coding_swebench=float(data.get("coding", 0)),
                math_math=float(data.get("math", 0)),
                reasoning_mmlu=float(data.get("reasoning", 0)),
            )
        return results

    def _parse_openrouter_data(self, raw: dict) -> dict[str, BenchmarkData]:
        """解析 OpenRouter rankings JSON 格式."""
        results: dict[str, BenchmarkData] = {}
        for item in raw.get("data", []):
            slug = item.get("slug", "")
            if not slug:
                continue
            metrics = item.get("metrics", {})
            results[slug] = BenchmarkData(
                coding_swebench=float(metrics.get("coding", 0)),
                reasoning_mmlu=float(metrics.get("reasoning", 0)),
                instruction_follow=float(metrics.get("instruction_following", 0)),
            )
        return results

    def _merge_benchmarks(
        self, sources: list[dict[str, BenchmarkData]]
    ) -> dict[str, BenchmarkData]:
        """多数据源融合：同字段取平均，独有字段保留."""
        merged: dict[str, dict[str, list[float]]] = {}
        for source in sources:
            for model_name, bm in source.items():
                if model_name not in merged:
                    merged[model_name] = {}
                for key, value in bm.to_dict().items():
                    if value > 0:  # 只累加有值的字段
                        merged[model_name].setdefault(key, []).append(value)

        result: dict[str, BenchmarkData] = {}
        for model_name, fields in merged.items():
            averaged = {
                k: sum(v) / len(v) for k, v in fields.items()
            }
            result[model_name] = BenchmarkData(**averaged)
        return result

    async def fetch_all(self) -> dict[str, BenchmarkData]:
        """拉取所有数据源并融合."""
        # 本地离线模式：返回空，由 ScoringDB 的本地缓存提供数据
        import aiohttp
        results: list[dict[str, BenchmarkData]] = []
        async with aiohttp.ClientSession() as session:
            for url in self.sources:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            raw = await resp.json()
                            if "arena_score" in str(raw) or "arena_elo" in str(raw):
                                results.append(self._parse_arena_data(raw))
                            else:
                                results.append(self._parse_openrouter_data(raw))
                except Exception:
                    continue  # 单个源失败不影响其他源
        return self._merge_benchmarks(results) if results else {}
```

运行：`python -m pytest tests/scoring/test_profile.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/scoring/ tests/scoring/
git commit -m "feat(scoring): ModelProfile 能力画像 + Benchmark 拉取器"
```

---

### 任务 2：ScoringDB — 模型评分 SQLite 持久化

**文件：**
- 创建：`src/scoring/database.py`
- 创建：`tests/scoring/test_database.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/scoring/test_database.py
from __future__ import annotations

import pytest

from src.config.crypto import KeyCipher, generate_key
from src.scoring.database import ScoringDB
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestScoringDB:
    """模型评分数据库测试."""

    @pytest.fixture
    async def db(self, temp_dir):
        """创建已初始化的 ScoringDB."""
        key = generate_key()
        cipher = KeyCipher(key)
        db_path = temp_dir / "test_scoring.db"
        scoring_db = ScoringDB(db_path)
        await scoring_db.init_db()
        yield scoring_db
        await scoring_db.close()

    @pytest.mark.asyncio
    async def test_init_db_creates_profiles_table(self, db):
        """初始化创建 profiles 表."""
        # 写入一条记录验证表存在
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
            benchmark=BenchmarkData(arena_elo=1287.0, coding_swebench=81.0),
        )
        await db.upsert_profile(profile)

    @pytest.mark.asyncio
    async def test_upsert_and_get_profile(self, db):
        """写入并读取模型画像."""
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
            benchmark=BenchmarkData(
                arena_elo=1287.0, coding_swebench=81.0,
                reasoning_mmlu=88.0, math_math=76.0,
            ),
            local_metrics=LocalMetrics(
                latency_p50_ms=320.0, predictability=0.82,
            ),
        )
        await db.upsert_profile(profile)
        loaded = await db.get_profile("openai", "gpt-4o")
        assert loaded is not None
        assert loaded.benchmark.arena_elo == 1287.0
        assert loaded.benchmark.coding_swebench == 81.0
        assert loaded.local_metrics.latency_p50_ms == 320.0

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile_returns_none(self, db):
        """不存在的画像返回 None."""
        loaded = await db.get_profile("unknown", "unknown")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, db):
        """更新已有画像."""
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
        )
        await db.upsert_profile(profile)

        # 更新 benchmark
        updated = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
            benchmark=BenchmarkData(arena_elo=1300.0),
        )
        await db.upsert_profile(updated)
        loaded = await db.get_profile("openai", "gpt-4o")
        assert loaded.benchmark.arena_elo == 1300.0

    @pytest.mark.asyncio
    async def test_list_all_profiles(self, db):
        """列出所有模型画像."""
        p1 = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
        )
        p2 = ModelProfile(
            provider="anthropic", model="claude-opus-5",
            deployment="cloud", context_window=200000,
            cost_input_1k=0.015, cost_output_1k=0.075,
        )
        await db.upsert_profile(p1)
        await db.upsert_profile(p2)
        all_profiles = await db.list_all()
        assert len(all_profiles) == 2

    @pytest.mark.asyncio
    async def test_update_local_metrics(self, db):
        """仅更新本地监控数据."""
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
        )
        await db.upsert_profile(profile)

        new_metrics = LocalMetrics(
            latency_p50_ms=450.0, predictability=0.65,
        )
        await db.update_local_metrics("openai", "gpt-4o", new_metrics)
        loaded = await db.get_profile("openai", "gpt-4o")
        assert loaded.local_metrics.latency_p50_ms == 450.0
        assert loaded.local_metrics.predictability == 0.65
        # benchmark 应保持不变
        assert loaded.benchmark.arena_elo == 0.0
```

运行：`python -m pytest tests/scoring/test_database.py -v`
预期：FAIL（ScoringDB 模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/scoring/database.py
from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class ScoringDB:
    """模型评分数据库.

    SQLite 持久化 ModelProfile：公开 benchmark + 本地监控指标。
    benchmark 数据以 JSON 字符串存储，便于字段扩展。

    用法:
        db = ScoringDB(Path("scoring.db"))
        await db.init_db()
        await db.upsert_profile(profile)
        loaded = await db.get_profile("openai", "gpt-4o")
        await db.close()
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        """初始化数据库表."""
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS model_profiles (
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                deployment TEXT NOT NULL DEFAULT 'cloud',
                context_window INTEGER NOT NULL DEFAULT 4096,
                cost_input_1k REAL NOT NULL DEFAULT 0.0,
                cost_output_1k REAL NOT NULL DEFAULT 0.0,
                benchmark_json TEXT NOT NULL DEFAULT '{}',
                local_metrics_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (provider, model)
            );
        """)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def upsert_profile(self, profile: ModelProfile) -> None:
        """插入或更新模型画像."""
        benchmark_json = json.dumps(profile.benchmark.to_dict())
        local_json = json.dumps({
            "latency_p50_ms": profile.local_metrics.latency_p50_ms,
            "latency_p95_ms": profile.local_metrics.latency_p95_ms,
            "latency_p99_ms": profile.local_metrics.latency_p99_ms,
            "predicted_latency_ms": profile.local_metrics.predicted_latency_ms,
            "predictability": profile.local_metrics.predictability,
            "throughput_rpm": profile.local_metrics.throughput_rpm,
            "error_rate": profile.local_metrics.error_rate,
        })
        await self._conn.execute(
            "INSERT OR REPLACE INTO model_profiles "
            "(provider, model, deployment, context_window, "
            "cost_input_1k, cost_output_1k, benchmark_json, local_metrics_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                profile.provider, profile.model, profile.deployment,
                profile.context_window, profile.cost_input_1k,
                profile.cost_output_1k, benchmark_json, local_json,
            ),
        )
        await self._conn.commit()

    async def get_profile(
        self, provider: str, model: str
    ) -> ModelProfile | None:
        """获取指定模型的画像."""
        cursor = await self._conn.execute(
            "SELECT * FROM model_profiles WHERE provider = ? AND model = ?",
            (provider, model),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    async def list_all(self) -> list[ModelProfile]:
        """列出所有模型画像."""
        cursor = await self._conn.execute("SELECT * FROM model_profiles")
        rows = await cursor.fetchall()
        return [self._row_to_profile(row) for row in rows]

    async def update_local_metrics(
        self,
        provider: str,
        model: str,
        metrics: LocalMetrics,
    ) -> None:
        """仅更新本地监控指标（不覆盖 benchmark）."""
        local_json = json.dumps({
            "latency_p50_ms": metrics.latency_p50_ms,
            "latency_p95_ms": metrics.latency_p95_ms,
            "latency_p99_ms": metrics.latency_p99_ms,
            "predicted_latency_ms": metrics.predicted_latency_ms,
            "predictability": metrics.predictability,
            "throughput_rpm": metrics.throughput_rpm,
            "error_rate": metrics.error_rate,
        })
        await self._conn.execute(
            "UPDATE model_profiles SET local_metrics_json = ?, "
            "updated_at = datetime('now') "
            "WHERE provider = ? AND model = ?",
            (local_json, provider, model),
        )
        await self._conn.commit()

    def _row_to_profile(self, row: aiosqlite.Row) -> ModelProfile:
        """将数据库行转换为 ModelProfile."""
        bm_raw = json.loads(row["benchmark_json"])
        benchmark = BenchmarkData(
            arena_elo=bm_raw.get("arena_elo", 0.0),
            coding_swebench=bm_raw.get("coding_swebench", 0.0),
            reasoning_mmlu=bm_raw.get("reasoning_mmlu", 0.0),
            math_math=bm_raw.get("math_math", 0.0),
            instruction_follow=bm_raw.get("instruction_follow", 0.0),
            multilingual=bm_raw.get("multilingual", 0.0),
            tool_use=bm_raw.get("tool_use", 0.0),
        )

        lm_raw = json.loads(row["local_metrics_json"])
        local_metrics = LocalMetrics(
            latency_p50_ms=lm_raw.get("latency_p50_ms", 0.0),
            latency_p95_ms=lm_raw.get("latency_p95_ms", 0.0),
            latency_p99_ms=lm_raw.get("latency_p99_ms", 0.0),
            predicted_latency_ms=lm_raw.get("predicted_latency_ms", 0.0),
            predictability=lm_raw.get("predictability", 0.0),
            throughput_rpm=lm_raw.get("throughput_rpm", 0.0),
            error_rate=lm_raw.get("error_rate", 0.0),
        )

        return ModelProfile(
            provider=row["provider"],
            model=row["model"],
            deployment=row["deployment"],
            context_window=row["context_window"],
            cost_input_1k=row["cost_input_1k"],
            cost_output_1k=row["cost_output_1k"],
            benchmark=benchmark,
            local_metrics=local_metrics,
        )
```

运行：`python -m pytest tests/scoring/test_database.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/scoring/database.py tests/scoring/test_database.py
git commit -m "feat(scoring): ScoringDB — 模型评分 SQLite 持久化"
```

---

### 任务 3：TaskProfile 任务需求模板

**文件：**
- 创建：`src/routing/__init__.py`
- 创建：`src/routing/task_profile.py`
- 创建：`tests/routing/__init__.py`
- 创建：`tests/routing/test_task_profile.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/routing/test_task_profile.py
from __future__ import annotations

import pytest

from src.routing.task_profile import TaskProfile


class TestTaskProfile:
    """任务需求模板测试."""

    def test_create_minimal_task(self):
        task = TaskProfile(
            task_id="code_review",
            display_name="代码审查",
        )
        assert task.task_id == "code_review"
        assert task.display_name == "代码审查"
        assert task.weights == {}
        assert task.constraints.max_latency_ms == 5000  # 默认宽松

    def test_create_task_with_weights(self):
        task = TaskProfile(
            task_id="code_review",
            display_name="代码审查",
            weights={
                "coding": 0.8,
                "reasoning": 0.6,
                "instruction": 0.4,
            },
        )
        assert task.weights["coding"] == 0.8
        assert task.weights["reasoning"] == 0.6

    def test_create_task_with_constraints(self):
        task = TaskProfile(
            task_id="realtime_chat",
            display_name="实时对话",
            weights={"coding": 0.2, "reasoning": 0.5},
            max_latency_ms=500,
            max_cost_1k=0.005,
            min_context=64000,
        )
        assert task.constraints.max_latency_ms == 500
        assert task.constraints.max_cost_1k == 0.005
        assert task.constraints.min_context == 64000

    def test_task_is_frozen(self):
        task = TaskProfile(task_id="t", display_name="T")
        with pytest.raises(Exception):
            task.task_id = "new"  # type: ignore[misc]

    def test_weight_sum_normalized(self):
        """权重自动归一化."""
        task = TaskProfile(
            task_id="t",
            display_name="T",
            weights={"a": 4.0, "b": 6.0},
        )
        assert task.weights["a"] == 0.4
        assert task.weights["b"] == 0.6

    def test_empty_weights_handled(self):
        """空权重不报错."""
        task = TaskProfile(task_id="t", display_name="T", weights={})
        assert task.weights == {}

    def test_default_task_profiles(self):
        """预置任务模板."""
        from src.routing.task_profile import DEFAULT_TASK_PROFILES
        assert "code_review" in DEFAULT_TASK_PROFILES
        assert "general_chat" in DEFAULT_TASK_PROFILES
        assert "data_analysis" in DEFAULT_TASK_PROFILES
        # 每个预置模板都有权重
        for tid, task in DEFAULT_TASK_PROFILES.items():
            assert isinstance(task, TaskProfile)
```

运行：`python -m pytest tests/routing/test_task_profile.py -v`
预期：FAIL（模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/routing/__init__.py
"""智能路由引擎：任务画像 + 可插拔策略 + 匹配算法."""
```

```python
# src/routing/task_profile.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TaskConstraints:
    """任务硬约束."""

    max_latency_ms: float = 5000.0
    max_cost_1k: float = 1.0
    min_context: int = 4096


@dataclass(frozen=True, slots=True)
class TaskProfile:
    """任务需求模板：权重向量 + 硬约束.

    Attributes:
        task_id: 任务类型唯一标识
        display_name: 显示名称
        weights: 能力维度权重，key 与 ModelProfile.capability_vector() 对齐
        constraints: 硬约束条件
    """

    task_id: str
    display_name: str
    weights: dict[str, float] = field(default_factory=dict, hash=False)
    constraints: TaskConstraints = field(default_factory=TaskConstraints)

    def __post_init__(self):
        """归一化权重."""
        if self.weights:
            total = sum(self.weights.values())
            if total > 0 and total != 1.0:
                normalized = {k: v / total for k, v in self.weights.items()}
                object.__setattr__(self, "weights", normalized)


# 预置任务模板
DEFAULT_TASK_PROFILES: dict[str, TaskProfile] = {
    "code_review": TaskProfile(
        task_id="code_review",
        display_name="代码审查",
        weights={
            "coding": 0.8,
            "reasoning": 0.6,
            "instruction": 0.4,
        },
        constraints=TaskConstraints(
            max_latency_ms=500,
            max_cost_1k=0.005,
            min_context=64000,
        ),
    ),
    "general_chat": TaskProfile(
        task_id="general_chat",
        display_name="通用对话",
        weights={
            "instruction": 0.5,
            "arena_elo": 0.5,
            "multilingual": 0.3,
        },
        constraints=TaskConstraints(
            max_latency_ms=2000,
        ),
    ),
    "data_analysis": TaskProfile(
        task_id="data_analysis",
        display_name="数据分析",
        weights={
            "reasoning": 0.8,
            "math": 0.6,
            "coding": 0.4,
        },
        constraints=TaskConstraints(
            max_latency_ms=10000,
            min_context=64000,
        ),
    ),
    "creative_writing": TaskProfile(
        task_id="creative_writing",
        display_name="创意写作",
        weights={
            "instruction": 0.7,
            "multilingual": 0.5,
            "arena_elo": 0.3,
        },
    ),
    "tool_automation": TaskProfile(
        task_id="tool_automation",
        display_name="工具自动化",
        weights={
            "tool_use": 0.9,
            "instruction": 0.5,
            "coding": 0.3,
        },
    ),
}
```

运行：`python -m pytest tests/routing/test_task_profile.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/routing/ tests/routing/
git commit -m "feat(routing): TaskProfile 任务需求模板 + 5 种预置模板"
```

---

### 任务 4：可插拔路由策略引擎

**文件：**
- 创建：`src/routing/strategy.py`
- 创建：`tests/routing/test_strategy.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/routing/test_strategy.py
from __future__ import annotations

import pytest

from src.routing.strategy import (
    BaselineStrategy,
    CostFirstStrategy,
    LatencyAwareStrategy,
    QualityFirstStrategy,
    TaskSpecificStrategy,
)
from src.routing.task_profile import DEFAULT_TASK_PROFILES, TaskConstraints, TaskProfile
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestBaselineStrategy:
    """均衡评分策略测试."""

    @pytest.fixture
    def strategy(self):
        return BaselineStrategy()

    @pytest.fixture
    def candidates(self):
        return [
            ModelProfile(
                provider="openai", model="gpt-4o",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.0025, cost_output_1k=0.0100,
                benchmark=BenchmarkData(arena_elo=1287, coding_swebench=81, reasoning_mmlu=88),
                local_metrics=LocalMetrics(latency_p50_ms=320),
            ),
            ModelProfile(
                provider="openai", model="gpt-4o-mini",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.00015, cost_output_1k=0.0006,
                benchmark=BenchmarkData(arena_elo=1150, coding_swebench=60, reasoning_mmlu=72),
                local_metrics=LocalMetrics(latency_p50_ms=100),
            ),
        ]

    def test_strategy_id_and_name(self, strategy):
        assert strategy.strategy_id == "baseline"
        assert strategy.display_name == "均衡评分"

    def test_score_returns_sorted_list(self, strategy, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        predictions: dict[str, object] = {}
        results = strategy.score(task, candidates, predictions)
        assert len(results) == 2
        # 按分数降序排列
        assert results[0][1] >= results[1][1]

    def test_score_each_element_is_model_score_tuple(self, strategy, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        predictions: dict[str, object] = {}
        results = strategy.score(task, candidates, predictions)
        for model, score in results:
            assert isinstance(model, ModelProfile)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_explain_returns_string(self, strategy, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        explanation = strategy.explain(task, candidates[0], 0.85)
        assert isinstance(explanation, str)
        assert len(explanation) > 0


class TestCostFirstStrategy:
    """成本优先策略."""

    def test_cheaper_model_scores_higher(self):
        strategy = CostFirstStrategy()
        expensive = ModelProfile(
            provider="p", model="expensive", deployment="cloud",
            context_window=128000, cost_input_1k=0.10, cost_output_1k=0.50,
            benchmark=BenchmarkData(arena_elo=1300),
        )
        cheap = ModelProfile(
            provider="p", model="cheap", deployment="cloud",
            context_window=128000, cost_input_1k=0.001, cost_output_1k=0.005,
            benchmark=BenchmarkData(arena_elo=1100),
        )
        task = TaskProfile(task_id="t", display_name="T")
        predictions: dict[str, object] = {}
        results = strategy.score(task, [expensive, cheap], predictions)
        # 便宜模型得分更高
        assert results[0][0].model == "cheap"


class TestQualityFirstStrategy:
    """质量优先策略."""

    def test_better_benchmark_scores_higher(self):
        strategy = QualityFirstStrategy()
        good = ModelProfile(
            provider="p", model="good", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(arena_elo=1400, coding_swebench=90, reasoning_mmlu=92),
        )
        bad = ModelProfile(
            provider="p", model="bad", deployment="cloud",
            context_window=128000, cost_input_1k=0.001, cost_output_1k=0.005,
            benchmark=BenchmarkData(arena_elo=900, coding_swebench=30, reasoning_mmlu=40),
        )
        task = TaskProfile(task_id="t", display_name="T", weights={"coding": 1.0, "reasoning": 1.0})
        predictions: dict[str, object] = {}
        results = strategy.score(task, [bad, good], predictions)
        assert results[0][0].model == "good"


class TestLatencyAwareStrategy:
    """延迟感知策略."""

    def test_lower_latency_scores_higher(self):
        strategy = LatencyAwareStrategy()
        fast = ModelProfile(
            provider="p", model="fast", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(arena_elo=1200),
            local_metrics=LocalMetrics(latency_p50_ms=50),
        )
        slow = ModelProfile(
            provider="p", model="slow", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(arena_elo=1250),
            local_metrics=LocalMetrics(latency_p50_ms=5000),
        )
        task = TaskProfile(task_id="t", display_name="T")
        predictions: dict[str, object] = {}
        results = strategy.score(task, [slow, fast], predictions)
        assert results[0][0].model == "fast"


class TestTaskSpecificStrategy:
    """任务分域策略."""

    def test_different_tasks_get_different_rankings(self):
        strategy = TaskSpecificStrategy()
        coder = ModelProfile(
            provider="p", model="coder", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(coding_swebench=95, reasoning_mmlu=50),
        )
        reasoner = ModelProfile(
            provider="p", model="reasoner", deployment="cloud",
            context_window=128000, cost_input_1k=0.01, cost_output_1k=0.05,
            benchmark=BenchmarkData(coding_swebench=50, reasoning_mmlu=95),
        )
        code_task = DEFAULT_TASK_PROFILES["code_review"]
        analysis_task = DEFAULT_TASK_PROFILES["data_analysis"]
        predictions: dict[str, object] = {}

        code_results = strategy.score(code_task, [coder, reasoner], predictions)
        analysis_results = strategy.score(analysis_task, [coder, reasoner], predictions)

        # 代码任务 coder 排第一
        assert code_results[0][0].model == "coder"
        # 分析任务 reasoner 排第一
        assert analysis_results[0][0].model == "reasoner"
```

运行：`python -m pytest tests/routing/test_strategy.py -v`
预期：FAIL（strategy 模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/routing/strategy.py
from __future__ import annotations

from typing import Protocol

from src.prediction.engine import LatencyPrediction
from src.routing.task_profile import TaskProfile
from src.scoring.profile import ModelProfile


class RoutingStrategy(Protocol):
    """可插拔路由策略接口.

    所有策略必须实现此接口。GUI 设置页可即时切换。
    """

    strategy_id: str
    display_name: str

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        """对候选模型评分并降序排列."""
        ...

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        """解释评分依据."""
        ...


def _capability_score(task: TaskProfile, profile: ModelProfile) -> float:
    """加权能力得分: Σ(能力_i × 权重_i) / Σ(权重_i).

    若任务无权重，使用 arena_elo 作为默认维度。
    """
    caps = profile.capability_vector()
    weights = task.weights or {"arena_elo": 1.0}

    numerator = 0.0
    denominator = 0.0
    for dim, weight in weights.items():
        value = caps.get(dim, 0.0)
        # 归一化 arena_elo 到 0-100
        if dim == "arena_elo":
            value = max(0.0, min(100.0, value / 15.0))
        numerator += value * weight
        denominator += weight

    if denominator == 0:
        return 0.0
    return numerator / denominator / 100.0  # 归一化到 [0, 1]


def _latency_score(latency_p50: float, max_latency: float = 5000.0) -> float:
    """延迟得分：延迟越低得分越高."""
    if latency_p50 <= 0:
        return 1.0
    return max(0.0, 1.0 - (latency_p50 / max_latency))


def _cost_score(cost_input: float, cost_output: float, max_cost: float = 0.1) -> float:
    """成本得分：成本越低得分越高."""
    avg_cost = (cost_input + cost_output) / 2
    if avg_cost <= 0:
        return 1.0
    return max(0.0, 1.0 - (avg_cost / max_cost))


class BaselineStrategy:
    """均衡评分 (w_cap=0.4, w_lat=0.3, w_cost=0.3)."""

    strategy_id = "baseline"
    display_name = "均衡评分"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = 0.4 * cap + 0.3 * lat + 0.3 * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return (
            f"[{self.display_name}] {model.model}: 最终得分 {score:.4f} "
            f"(能力={_capability_score(task, model):.4f}, "
            f"延迟={_latency_score(model.local_metrics.latency_p50_ms):.4f}, "
            f"成本={_cost_score(model.cost_input_1k, model.cost_output_1k):.4f})"
        )


class CostFirstStrategy:
    """成本优先 (w_cap=0.2, w_lat=0.2, w_cost=0.6)."""

    strategy_id = "cost_first"
    display_name = "成本优先"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = 0.2 * cap + 0.2 * lat + 0.6 * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return (
            f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"
        )


class QualityFirstStrategy:
    """质量优先 (w_cap=0.7, w_lat=0.1, w_cost=0.2)."""

    strategy_id = "quality_first"
    display_name = "质量优先"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = 0.7 * cap + 0.2 * lat + 0.1 * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"


class LatencyAwareStrategy:
    """延迟感知 (w_cap=0.3, w_lat=0.6, w_cost=0.1)."""

    strategy_id = "latency_aware"
    display_name = "延迟感知"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = 0.3 * cap + 0.6 * lat + 0.1 * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"


class TaskSpecificStrategy:
    """任务分域 — 按 TaskProfile.weights 动态分配能力:延迟:成本权重.

    权重大 → 能力导向；权重小 → 成本/延迟优先。
    """

    strategy_id = "task_specific"
    display_name = "任务分域"

    def score(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        predictions: dict[str, LatencyPrediction],
    ) -> list[tuple[ModelProfile, float]]:
        # 动态权重：平均权重大 → 更重视能力
        avg_weight = sum(task.weights.values()) / max(len(task.weights), 1)
        w_cap = 0.3 + 0.4 * avg_weight
        w_lat = 0.4 * (1.0 - avg_weight)
        w_cost = 0.3 * (1.0 - avg_weight)
        total = w_cap + w_lat + w_cost
        w_cap /= total
        w_lat /= total
        w_cost /= total

        scored = []
        for p in candidates:
            cap = _capability_score(task, p)
            lat = _latency_score(p.local_metrics.latency_p50_ms)
            cost = _cost_score(p.cost_input_1k, p.cost_output_1k)
            final = w_cap * cap + w_lat * lat + w_cost * cost
            scored.append((p, final))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def explain(self, task: TaskProfile, model: ModelProfile, score: float) -> str:
        return f"[{self.display_name}] {model.model}: 最终得分 {score:.4f}"


# 策略注册表
BUILTIN_STRATEGIES: dict[str, RoutingStrategy] = {
    "baseline": BaselineStrategy(),
    "cost_first": CostFirstStrategy(),
    "quality_first": QualityFirstStrategy(),
    "latency_aware": LatencyAwareStrategy(),
    "task_specific": TaskSpecificStrategy(),
}
```

运行：`python -m pytest tests/routing/test_strategy.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/routing/strategy.py tests/routing/test_strategy.py
git commit -m "feat(routing): 5 种可插拔路由策略 — 均衡/成本/质量/延迟/任务分域"
```

---

### 任务 5：RouteEngine — 路由匹配引擎

**文件：**
- 创建：`src/routing/engine.py`
- 创建：`tests/routing/test_engine.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/routing/test_engine.py
from __future__ import annotations

import pytest

from src.routing.engine import RouteEngine, RouteResult
from src.routing.strategy import BaselineStrategy
from src.routing.task_profile import DEFAULT_TASK_PROFILES, TaskProfile
from src.scoring.profile import BenchmarkData, LocalMetrics, ModelProfile


class TestRouteResult:
    """路由结果测试."""

    def test_create_result(self):
        profile = ModelProfile(
            provider="openai", model="gpt-4o",
            deployment="cloud", context_window=128000,
            cost_input_1k=0.0025, cost_output_1k=0.0100,
        )
        result = RouteResult(
            profile=profile,
            score=0.85,
            filtered_out=[],
        )
        assert result.profile == profile
        assert result.score == 0.85
        assert result.filtered_out == []


class TestRouteEngine:
    """路由引擎集成测试."""

    @pytest.fixture
    def candidates(self):
        return [
            ModelProfile(
                provider="openai", model="gpt-4o",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.0025, cost_output_1k=0.0100,
                benchmark=BenchmarkData(arena_elo=1287, coding_swebench=81, reasoning_mmlu=88),
                local_metrics=LocalMetrics(latency_p50_ms=320, latency_p95_ms=850),
            ),
            ModelProfile(
                provider="openai", model="gpt-4o-mini",
                deployment="cloud", context_window=128000,
                cost_input_1k=0.00015, cost_output_1k=0.0006,
                benchmark=BenchmarkData(arena_elo=1150, coding_swebench=60, reasoning_mmlu=72),
                local_metrics=LocalMetrics(latency_p50_ms=100, latency_p95_ms=200),
            ),
            ModelProfile(
                provider="local", model="qwen2.5:7b",
                deployment="local", context_window=32768,
                cost_input_1k=0.0, cost_output_1k=0.0,
                benchmark=BenchmarkData(arena_elo=800, coding_swebench=40),
                local_metrics=LocalMetrics(latency_p50_ms=1500, latency_p95_ms=3000),
            ),
        ]

    @pytest.fixture
    def engine(self):
        return RouteEngine(strategy=BaselineStrategy())

    def test_create_engine(self, engine):
        assert engine.strategy.strategy_id == "baseline"

    def test_route_returns_best_match(self, engine, candidates):
        task = DEFAULT_TASK_PROFILES["code_review"]
        result = engine.route(task, candidates)

        assert result is not None
        assert result.profile is not None
        assert result.score > 0
        # gpt-4o 能力最强 → 排第一
        assert result.profile.model == "gpt-4o"

    def test_route_applies_hard_constraints(self, candidates):
        """硬约束过滤."""
        engine = RouteEngine(strategy=BaselineStrategy())
        task = TaskProfile(
            task_id="t", display_name="T",
            max_latency_ms=200,  # 强制低延迟
        )
        result = engine.route(task, candidates)
        # gpt-4o (320ms) 被过滤，应选中 gpt-4o-mini (100ms)
        assert result.profile.model == "gpt-4o-mini"

    def test_route_max_cost_filter(self, candidates):
        """最大成本约束."""
        engine = RouteEngine(strategy=BaselineStrategy())
        task = TaskProfile(
            task_id="t", display_name="T",
            max_cost_1k=0.001,  # 极低成本
        )
        result = engine.route(task, candidates)
        # gpt-4o-mini (0.00015+0.0006)/2=0.000375 通过，qwen 免费通过
        assert result.profile.model in ("gpt-4o-mini", "qwen2.5:7b")

    def test_route_min_context_filter(self, candidates):
        """最小上下文约束."""
        engine = RouteEngine(strategy=BaselineStrategy())
        task = TaskProfile(
            task_id="t", display_name="T",
            min_context=100000,
        )
        result = engine.route(task, candidates)
        # qwen 只有 32k，被过滤
        assert result.profile.model in ("gpt-4o", "gpt-4o-mini")

    def test_route_all_candidates_filtered_returns_none(self, candidates):
        """所有候选都不满足硬约束时返回 None."""
        engine = RouteEngine(strategy=BaselineStrategy())
        task = TaskProfile(
            task_id="t", display_name="T",
            max_latency_ms=10,  # 所有模型都被过滤
        )
        result = engine.route(task, candidates)
        assert result is None

    def test_route_empty_candidates_returns_none(self, engine):
        task = DEFAULT_TASK_PROFILES["code_review"]
        result = engine.route(task, [])
        assert result is None

    def test_route_top_n(self, engine, candidates):
        """获取 Top-N 推荐."""
        task = DEFAULT_TASK_PROFILES["code_review"]
        results = engine.route_top_n(task, candidates, n=2)
        assert len(results) == 2
        assert results[0].score >= results[1].score
```

运行：`python -m pytest tests/routing/test_engine.py -v`
预期：FAIL（RouteEngine 模块不存在）

- [ ] **步骤 3：编写最少实现代码**

```python
# src/routing/engine.py
from __future__ import annotations

from dataclasses import dataclass, field

from src.prediction.engine import LatencyPrediction
from src.routing.strategy import RoutingStrategy
from src.routing.task_profile import TaskProfile
from src.scoring.profile import ModelProfile


@dataclass(frozen=True, slots=True)
class RouteResult:
    """单次路由匹配结果."""

    profile: ModelProfile
    score: float
    filtered_out: list[ModelProfile] = field(default_factory=list, hash=False)


class RouteEngine:
    """路由匹配引擎.

    执行四步匹配算法：
    Step 1: 硬约束过滤 → 候选模型集
    Step 2: Σ(模型能力_i × 任务权重_i) / Σ(权重_i) → 能力得分
    Step 3: + 延迟性价比修正 - 成本惩罚 → 最终得分
    Step 4: 排序输出最佳匹配

    用法:
        engine = RouteEngine(strategy=BaselineStrategy())
        result = engine.route(task_profile, candidates)
        if result:
            print(f"最佳模型: {result.profile.model}, 得分: {result.score:.4f}")
    """

    def __init__(
        self,
        strategy: RoutingStrategy,
        predictions: dict[str, LatencyPrediction] | None = None,
    ) -> None:
        self.strategy = strategy
        self._predictions: dict[str, LatencyPrediction] = predictions or {}

    def _apply_constraints(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
    ) -> tuple[list[ModelProfile], list[ModelProfile]]:
        """Step 1: 硬约束过滤.

        Returns:
            (通过约束的候选, 被过滤的候选)
        """
        passed: list[ModelProfile] = []
        filtered: list[ModelProfile] = []

        for p in candidates:
            constraints = task.constraints

            # 延迟约束
            if p.local_metrics.latency_p50_ms > constraints.max_latency_ms:
                filtered.append(p)
                continue

            # 成本约束
            avg_cost = (p.cost_input_1k + p.cost_output_1k) / 2
            if avg_cost > constraints.max_cost_1k:
                filtered.append(p)
                continue

            # 上下文长度约束
            if p.context_window < constraints.min_context:
                filtered.append(p)
                continue

            passed.append(p)

        return passed, filtered

    def route(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
    ) -> RouteResult | None:
        """路由匹配：返回最佳模型和评分.

        Returns:
            RouteResult 或 None（无候选满足约束时）
        """
        if not candidates:
            return None

        # Step 1: 硬约束过滤
        passed, filtered = self._apply_constraints(task, candidates)
        if not passed:
            return None

        # Step 2-4: 策略评分 + 排序
        scored = self.strategy.score(task, passed, self._predictions)

        return RouteResult(
            profile=scored[0][0],
            score=scored[0][1],
            filtered_out=filtered,
        )

    def route_top_n(
        self,
        task: TaskProfile,
        candidates: list[ModelProfile],
        n: int = 3,
    ) -> list[RouteResult]:
        """路由匹配：返回 Top-N 推荐."""
        if not candidates:
            return []

        passed, filtered = self._apply_constraints(task, candidates)
        if not passed:
            return []

        scored = self.strategy.score(task, passed, self._predictions)

        results: list[RouteResult] = []
        for model, score in scored[:n]:
            results.append(RouteResult(
                profile=model,
                score=score,
                filtered_out=[f for f in filtered if f not in [r.profile for r in results]],
            ))
        return results

    def with_predictions(
        self, predictions: dict[str, LatencyPrediction]
    ) -> RouteEngine:
        """返回绑定了预测数据的新引擎实例."""
        return RouteEngine(strategy=self.strategy, predictions=predictions)
```

运行：`python -m pytest tests/routing/test_engine.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add src/routing/engine.py tests/routing/test_engine.py
git commit -m "feat(routing): RouteEngine — 硬约束过滤 + 策略评分 + 排序输出"
```

---

### 任务 6：全量测试验证 + pyproject.toml 更新

- [ ] **步骤 1：运行全量测试**

```bash
python -m pytest tests/ -v
```

预期：全部通过

- [ ] **步骤 2：检查 .gitignore 是否需要更新**

确认 `*.db` 已覆盖 ScoringDB 的 `scoring.db` 等。

- [ ] **步骤 3：更新 pyproject.toml 依赖（如有新增）**

本阶段无新增 pip 依赖（aiohttp, aiosqlite 已在 Phase 1/2 安装）。

- [ ] **步骤 4：Commit**

```bash
git add -A
git commit -m "chore: Phase 3 全量测试验证 + 配置更新"
```
