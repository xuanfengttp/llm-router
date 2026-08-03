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
