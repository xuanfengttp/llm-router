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
