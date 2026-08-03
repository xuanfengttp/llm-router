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
