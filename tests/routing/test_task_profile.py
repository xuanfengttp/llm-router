from __future__ import annotations

import pytest

from src.routing.task_profile import TaskConstraints, TaskProfile


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
        # 权重传入后已归一化（总和 1.8 → 归一化到总和 1.0）
        assert task.weights["coding"] == pytest.approx(0.8 / 1.8)
        assert task.weights["reasoning"] == pytest.approx(0.6 / 1.8)

    def test_create_task_with_constraints(self):
        task = TaskProfile(
            task_id="realtime_chat",
            display_name="实时对话",
            weights={"coding": 0.2, "reasoning": 0.5},
            constraints=TaskConstraints(
                max_latency_ms=500,
                max_cost_1k=0.005,
                min_context=64000,
            ),
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
        assert "creative_writing" in DEFAULT_TASK_PROFILES
        assert "tool_automation" in DEFAULT_TASK_PROFILES
        # 每个预置模板都有权重
        for tid, task in DEFAULT_TASK_PROFILES.items():
            assert isinstance(task, TaskProfile)
