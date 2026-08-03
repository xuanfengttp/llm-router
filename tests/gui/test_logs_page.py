from __future__ import annotations

import pytest


class TestLogsPageData:
    """测试日志页数据变换函数."""

    def test_audit_row_to_display(self):
        """审计记录 → 显示行."""
        from src.gui.pages.logs_page import audit_row_to_display

        row = {
            "id": 1,
            "timestamp": "2026-08-03T10:00:00+00:00",
            "task_id": "abc-123",
            "agent_id": "agent-1",
            "path": "/workspace/test.py",
            "operation": "read",
            "path_category": "own_workspace",
            "decision": "allow",
            "reason": "default allow",
        }
        display = audit_row_to_display(row)
        assert display["timestamp"] == "2026-08-03 10:00:00"
        assert display["task_id"] == "abc-123"
        assert display["operation"] == "read"
        assert display["decision"] == "allow"

    def test_audit_row_to_display_truncated_path(self):
        """长路径应截断显示."""
        from src.gui.pages.logs_page import audit_row_to_display

        row = {
            "id": 1, "timestamp": "2026-08-03T10:00:00",
            "task_id": "t", "agent_id": "a",
            "path": "/" + "x" * 100,
            "operation": "read", "path_category": "own_workspace",
            "decision": "allow", "reason": "",
        }
        display = audit_row_to_display(row)
        assert len(display["path"]) <= 60

    def test_decision_color(self):
        """审计决策 → 颜色."""
        from src.gui.pages.logs_page import decision_color

        assert decision_color("allow") == "green"
        assert decision_color("escalate") == "orange"
        assert decision_color("deny") == "red"

    def test_operation_cn(self):
        """操作枚举 → 中文."""
        from src.gui.pages.logs_page import operation_cn

        assert operation_cn("read") == "读取"
        assert operation_cn("write") == "写入"
        assert operation_cn("delete") == "删除"
        assert operation_cn("execute") == "执行"
