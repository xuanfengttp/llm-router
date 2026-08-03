# tests/gui/test_tasks_page.py
from __future__ import annotations

import pytest

from src.controller.task_model import AgentTask, AgentTaskStatus


class TestTasksPageData:
    """测试任务管理页数据变换函数."""

    def test_group_tasks_by_status(self):
        """任务按状态分组为三列."""
        from src.gui.pages.tasks_page import group_tasks_by_status

        tasks = [
            AgentTask(task_id="t1", prompt="a", target_model="m1", status=AgentTaskStatus.PENDING),
            AgentTask(task_id="t2", prompt="b", target_model="m2", status=AgentTaskStatus.RUNNING),
            AgentTask(task_id="t3", prompt="c", target_model="m3", status=AgentTaskStatus.FAILED),
            AgentTask(task_id="t4", prompt="d", target_model="m4", status=AgentTaskStatus.PENDING),
            AgentTask(task_id="t5", prompt="e", target_model="m5", status=AgentTaskStatus.STANDBY),
        ]
        groups = group_tasks_by_status(tasks)
        assert len(groups["pending"]) == 2
        assert len(groups["running"]) == 1
        assert len(groups["failed_standby"]) == 2  # FAILED + STANDBY

    def test_group_tasks_empty(self):
        """空列表返回空分组."""
        from src.gui.pages.tasks_page import group_tasks_by_status

        groups = group_tasks_by_status([])
        assert groups["pending"] == []
        assert groups["running"] == []
        assert groups["failed_standby"] == []

    def test_task_to_card(self):
        """任务 -> 卡片展示数据."""
        from src.gui.pages.tasks_page import task_to_card

        task = AgentTask(
            task_id="abc-123",
            prompt="帮我写代码",
            target_model="gpt-4o",
            status=AgentTaskStatus.PENDING,
            retry_count=1,
            max_retries=3,
        )
        card = task_to_card(task)
        assert card["task_id_short"] == "abc-123"[:8]
        assert card["prompt"] == "帮我写代码"
        assert card["target_model"] == "gpt-4o"
        assert card["status"] == "pending"
        assert card["retry_info"] == "1/3"

    def test_status_cn_label(self):
        """状态枚举 -> 中文标签."""
        from src.gui.pages.tasks_page import status_cn_label

        assert status_cn_label(AgentTaskStatus.PENDING) == "待分发"
        assert status_cn_label(AgentTaskStatus.RUNNING) == "执行中"
        assert status_cn_label(AgentTaskStatus.SUCCESS) == "成功"
        assert status_cn_label(AgentTaskStatus.FAILED) == "失败"
        assert status_cn_label(AgentTaskStatus.STANDBY) == "暂停"
