from __future__ import annotations

from src.controller.recovery import FailureInfo, RecoveryAction, RecoveryEngine
from src.controller.task_model import AgentTask


class TestFailureInfo:
    def test_create(self):
        fi = FailureInfo(failure_type="timeout", message="timed out after 30s")
        assert fi.failure_type == "timeout"
        assert fi.message == "timed out after 30s"
        assert fi.retry_after_seconds == 0

    def test_rate_limit_with_retry_after(self):
        fi = FailureInfo(failure_type="rate_limit", message="429", retry_after_seconds=60)
        assert fi.retry_after_seconds == 60


class TestRecoveryEngine:
    def test_timeout_retry_switch_model(self):
        engine = RecoveryEngine()
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o", retry_count=0)
        fi = FailureInfo(failure_type="timeout", message="timed out")
        action, reason = engine.decide(task, fi)
        assert action == RecoveryAction.RETRY_SWITCH_MODEL
        assert "switch" in reason.lower()

    def test_network_retry_same_model(self):
        engine = RecoveryEngine()
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o", retry_count=0)
        fi = FailureInfo(failure_type="network", message="connection refused")
        action, reason = engine.decide(task, fi)
        assert action == RecoveryAction.RETRY_SAME_MODEL
        assert "same model" in reason.lower()

    def test_rate_limit_retry_same_model(self):
        engine = RecoveryEngine()
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o", retry_count=0)
        fi = FailureInfo(failure_type="rate_limit", message="429", retry_after_seconds=30)
        action, reason = engine.decide(task, fi)
        assert action == RecoveryAction.RETRY_SAME_MODEL
        assert "30s" in reason.lower()

    def test_auth_error_immediate_standby(self):
        engine = RecoveryEngine()
        task = AgentTask(task_id="t", prompt="p", target_model="gpt-4o", retry_count=0)
        fi = FailureInfo(failure_type="auth_error", message="401")
        action, reason = engine.decide(task, fi)
        assert action == RecoveryAction.STANDBY
        assert "auth" in reason.lower()

    def test_unknown_retry_then_standby(self):
        engine = RecoveryEngine(max_retries=3)
        task_fresh = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=0)
        fi = FailureInfo(failure_type="unknown", message="something broke")
        action, _ = engine.decide(task_fresh, fi)
        assert action == RecoveryAction.RETRY_SAME_MODEL

    def test_unknown_twice_then_standby(self):
        engine = RecoveryEngine(max_retries=3)
        task = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=2)
        fi = FailureInfo(failure_type="unknown", message="error")
        action, _ = engine.decide(task, fi)
        assert action == RecoveryAction.STANDBY

    def test_consecutive_failures_total_3_standby(self):
        engine = RecoveryEngine(max_retries=3)
        task = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=2)
        fi = FailureInfo(failure_type="network", message="down")
        action, _ = engine.decide(task, fi)
        assert action == RecoveryAction.STANDBY

    def test_below_max_retries_still_retryable(self):
        engine = RecoveryEngine(max_retries=5)
        task = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=3)
        fi = FailureInfo(failure_type="timeout", message="timeout")
        action, _ = engine.decide(task, fi)
        assert action == RecoveryAction.RETRY_SWITCH_MODEL

    def test_custom_max_retries(self):
        engine = RecoveryEngine(max_retries=2)
        task = AgentTask(task_id="t", prompt="p", target_model="m", retry_count=1)
        fi = FailureInfo(failure_type="network", message="error")
        action, _ = engine.decide(task, fi)
        assert action == RecoveryAction.STANDBY
