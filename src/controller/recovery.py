from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.controller.task_model import AgentTask


class RecoveryAction(str, Enum):
    RETRY_SAME_MODEL = "retry_same_model"
    RETRY_SWITCH_MODEL = "retry_switch_model"
    STANDBY = "standby"


@dataclass(frozen=True, slots=True)
class FailureInfo:
    failure_type: str  # timeout | network | rate_limit | auth_error | unknown
    message: str
    retry_after_seconds: int = 0


class RecoveryEngine:
    def __init__(self, max_retries: int = 3, retry_delay_network: int = 30) -> None:
        self.max_retries = max_retries
        self.retry_delay_network = retry_delay_network

    def decide(self, task: AgentTask, failure: FailureInfo) -> tuple[RecoveryAction, str]:
        new_count = task.retry_count + 1

        # auth_error — no retry, immediate standby
        if failure.failure_type == "auth_error":
            return RecoveryAction.STANDBY, f"auth error, no retry: {failure.message}"

        # max retries reached
        if new_count >= self.max_retries:
            return RecoveryAction.STANDBY, (
                f"consecutive {new_count} failures (max {self.max_retries}), "
                f"final error: {failure.message}"
            )

        # rate_limit — retry same model after waiting
        if failure.failure_type == "rate_limit":
            wait = failure.retry_after_seconds or self.retry_delay_network
            return RecoveryAction.RETRY_SAME_MODEL, f"rate limited: wait {wait}s then retry same model"

        # network — retry same model after delay
        if failure.failure_type == "network":
            return RecoveryAction.RETRY_SAME_MODEL, (
                f"network error: wait {self.retry_delay_network}s then retry same model: {failure.message}"
            )

        # timeout — switch model
        if failure.failure_type == "timeout":
            return RecoveryAction.RETRY_SWITCH_MODEL, f"timeout: switch model and retry: {failure.message}"

        # unknown — retry same model until max retries
        if new_count >= self.max_retries:
            return RecoveryAction.STANDBY, f"unknown error reached max {self.max_retries} retries: {failure.message}"
        return RecoveryAction.RETRY_SAME_MODEL, f"unknown error: retry same model ({new_count}/{self.max_retries}): {failure.message}"
