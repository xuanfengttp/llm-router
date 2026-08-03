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
