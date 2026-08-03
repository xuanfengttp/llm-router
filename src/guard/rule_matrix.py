from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class PathCategory(str, Enum):
    OWN_WORKSPACE = "own_workspace"
    OTHER_WORKSPACE = "other_workspace"
    SYSTEM = "system"


class FileOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"


class AuditDecision(str, Enum):
    ALLOW = "allow"
    ESCALATE = "escalate"
    DENY = "deny"


DEFAULT_RULE_MATRIX: dict[tuple[PathCategory, FileOperation], AuditDecision] = {
    (PathCategory.OWN_WORKSPACE, FileOperation.READ):     AuditDecision.ALLOW,
    (PathCategory.OWN_WORKSPACE, FileOperation.WRITE):    AuditDecision.ALLOW,
    (PathCategory.OWN_WORKSPACE, FileOperation.DELETE):   AuditDecision.ALLOW,
    (PathCategory.OWN_WORKSPACE, FileOperation.EXECUTE):  AuditDecision.ESCALATE,

    (PathCategory.OTHER_WORKSPACE, FileOperation.READ):   AuditDecision.ESCALATE,
    (PathCategory.OTHER_WORKSPACE, FileOperation.WRITE):  AuditDecision.ESCALATE,
    (PathCategory.OTHER_WORKSPACE, FileOperation.DELETE): AuditDecision.ESCALATE,
    (PathCategory.OTHER_WORKSPACE, FileOperation.EXECUTE): AuditDecision.DENY,

    (PathCategory.SYSTEM, FileOperation.READ):            AuditDecision.DENY,
    (PathCategory.SYSTEM, FileOperation.WRITE):           AuditDecision.DENY,
    (PathCategory.SYSTEM, FileOperation.DELETE):          AuditDecision.DENY,
    (PathCategory.SYSTEM, FileOperation.EXECUTE):         AuditDecision.DENY,
}

SYSTEM_ROOTS = ("/System", "/Windows", "/etc", "/usr", "/bin", "/boot")


@dataclass(frozen=True, slots=True)
class FileAccessRequest:
    task_id: str
    agent_id: str
    path: str
    operation: FileOperation
    workspace_root: str


class RuleMatrix:
    def __init__(
        self,
        custom_rules: dict[tuple[PathCategory, FileOperation], AuditDecision] | None = None,
    ) -> None:
        self._rules: dict = dict(DEFAULT_RULE_MATRIX)
        if custom_rules:
            self._rules.update(custom_rules)

    def classify_path(self, path: str, workspace_root: str) -> PathCategory:
        normalized_path = os.path.normpath(path).replace("\\", "/")
        for root in SYSTEM_ROOTS:
            if normalized_path.startswith(root):
                return PathCategory.SYSTEM

        normalized_ws = os.path.normpath(workspace_root).replace("\\", "/")
        if normalized_path.startswith(normalized_ws):
            return PathCategory.OWN_WORKSPACE

        return PathCategory.OTHER_WORKSPACE

    def decide(self, request: FileAccessRequest) -> AuditDecision:
        category = self.classify_path(request.path, request.workspace_root)
        key = (category, request.operation)
        return self._rules.get(key, AuditDecision.DENY)

    def explain(self, request: FileAccessRequest) -> str:
        category = self.classify_path(request.path, request.workspace_root)
        decision = self.decide(request)
        reasons = {
            (PathCategory.OWN_WORKSPACE, FileOperation.READ): "自有文件夹读取 — 自动放行",
            (PathCategory.OWN_WORKSPACE, FileOperation.WRITE): "自有文件夹写入 — 自动放行",
            (PathCategory.OWN_WORKSPACE, FileOperation.DELETE): "自有文件夹删除 — 自动放行",
            (PathCategory.OWN_WORKSPACE, FileOperation.EXECUTE): "自有文件夹执行文件 — 升级人工审核",
            (PathCategory.OTHER_WORKSPACE, FileOperation.READ): "跨任务文件夹读取 — 升级人工审核",
            (PathCategory.OTHER_WORKSPACE, FileOperation.WRITE): "跨任务文件夹写入 — 升级人工审核",
            (PathCategory.OTHER_WORKSPACE, FileOperation.DELETE): "跨任务文件夹删除 — 升级人工审核",
            (PathCategory.OTHER_WORKSPACE, FileOperation.EXECUTE): "跨任务文件夹执行文件 — 硬拒绝",
            (PathCategory.SYSTEM, FileOperation.READ): "系统目录读取 — 硬拒绝",
            (PathCategory.SYSTEM, FileOperation.WRITE): "系统目录写入 — 硬拒绝",
            (PathCategory.SYSTEM, FileOperation.DELETE): "系统目录删除 — 硬拒绝",
            (PathCategory.SYSTEM, FileOperation.EXECUTE): "系统目录执行文件 — 硬拒绝",
        }
        return reasons.get((category, request.operation), f"{category}:{request.operation} → {decision}")
