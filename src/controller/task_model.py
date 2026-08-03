from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AgentTaskStatus(str, Enum):
    PENDING = "pending"
    CHECKING = "checking"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    STANDBY = "standby"
    CANCELLED = "cancelled"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class AgentTask:
    task_id: str
    prompt: str
    target_model: str
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    failure_reason: str = ""
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentTask):
            return NotImplemented
        return self.task_id == other.task_id

    def __hash__(self) -> int:
        return hash(self.task_id)

    def _replace(self, **kwargs) -> AgentTask:
        current = {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "target_model": self.target_model,
            "status": self.status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        current.update(kwargs)
        current["updated_at"] = _utc_now()
        return AgentTask(**current)

    def transition_to(self, new_status: AgentTaskStatus, reason: str = "") -> AgentTask:
        kwargs: dict = {"status": new_status}
        if reason:
            kwargs["failure_reason"] = reason
        return self._replace(**kwargs)

    def with_retry(self, reason: str) -> AgentTask:
        new_count = self.retry_count + 1
        new_status = AgentTaskStatus.STANDBY if new_count >= self.max_retries else AgentTaskStatus.FAILED
        return self._replace(
            status=new_status,
            retry_count=new_count,
            failure_reason=reason,
        )

    def mark_running(self) -> AgentTask:
        return self.transition_to(AgentTaskStatus.RUNNING)

    def mark_success(self) -> AgentTask:
        return self.transition_to(AgentTaskStatus.SUCCESS)

    def mark_failed(self, reason: str) -> AgentTask:
        new_count = self.retry_count + 1
        if new_count >= self.max_retries:
            return self._replace(
                status=AgentTaskStatus.STANDBY,
                retry_count=new_count,
                failure_reason=reason,
            )
        return self._replace(
            status=AgentTaskStatus.FAILED,
            retry_count=new_count,
            failure_reason=reason,
        )

    def mark_cancelled(self) -> AgentTask:
        return self.transition_to(AgentTaskStatus.CANCELLED)
