# src/guard/audit_log.py (最小骨架 — Task 6 将填充)
from __future__ import annotations


class AuditLog:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init_db(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def record(self, *args, **kwargs) -> None:
        pass
