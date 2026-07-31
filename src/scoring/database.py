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
