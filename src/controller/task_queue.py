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
