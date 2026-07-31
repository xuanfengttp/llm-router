from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TaskConstraints:
    """任务硬约束."""

    max_latency_ms: float = 5000.0
    max_cost_1k: float = 1.0
    min_context: int = 4096


@dataclass(frozen=True, slots=True)
class TaskProfile:
    """任务需求模板：权重向量 + 硬约束.

    Attributes:
        task_id: 任务类型唯一标识
        display_name: 显示名称
        weights: 能力维度权重，key 与 ModelProfile.capability_vector() 对齐
        constraints: 硬约束条件
    """

    task_id: str
    display_name: str
    weights: dict[str, float] = field(default_factory=dict, hash=False)
    constraints: TaskConstraints = field(default_factory=TaskConstraints)

    def __post_init__(self):
        """归一化权重."""
        if self.weights:
            total = sum(self.weights.values())
            if total > 0 and total != 1.0:
                normalized = {k: v / total for k, v in self.weights.items()}
                object.__setattr__(self, "weights", normalized)


# 预置任务模板
DEFAULT_TASK_PROFILES: dict[str, TaskProfile] = {
    "code_review": TaskProfile(
        task_id="code_review",
        display_name="代码审查",
        weights={
            "coding": 0.8,
            "reasoning": 0.6,
            "instruction": 0.4,
        },
        constraints=TaskConstraints(
            max_latency_ms=500,
            max_cost_1k=0.005,
            min_context=64000,
        ),
    ),
    "general_chat": TaskProfile(
        task_id="general_chat",
        display_name="通用对话",
        weights={
            "instruction": 0.5,
            "arena_elo": 0.5,
            "multilingual": 0.3,
        },
        constraints=TaskConstraints(
            max_latency_ms=2000,
        ),
    ),
    "data_analysis": TaskProfile(
        task_id="data_analysis",
        display_name="数据分析",
        weights={
            "reasoning": 0.8,
            "math": 0.6,
            "coding": 0.4,
        },
        constraints=TaskConstraints(
            max_latency_ms=10000,
            min_context=64000,
        ),
    ),
    "creative_writing": TaskProfile(
        task_id="creative_writing",
        display_name="创意写作",
        weights={
            "instruction": 0.7,
            "multilingual": 0.5,
            "arena_elo": 0.3,
        },
    ),
    "tool_automation": TaskProfile(
        task_id="tool_automation",
        display_name="工具自动化",
        weights={
            "tool_use": 0.9,
            "instruction": 0.5,
            "coding": 0.3,
        },
    ),
}
