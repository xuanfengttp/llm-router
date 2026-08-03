from __future__ import annotations

from src.guard.audit_log import AuditLog
from src.guard.rule_matrix import (
    AuditDecision,
    FileAccessRequest,
    RuleMatrix,
)


class FileGuard:
    def __init__(self, matrix: RuleMatrix, audit_log: AuditLog) -> None:
        self.matrix = matrix
        self.audit_log = audit_log

    async def check(self, request: FileAccessRequest) -> tuple[AuditDecision, str]:
        category = self.matrix.classify_path(request.path, request.workspace_root)
        decision = self.matrix.decide(request)
        reason = self.matrix.explain(request)

        await self.audit_log.record(request, decision, category, reason)
        return decision, reason

    async def check_batch(
        self, requests: list[FileAccessRequest],
    ) -> list[tuple[FileAccessRequest, AuditDecision, str]]:
        results: list[tuple[FileAccessRequest, AuditDecision, str]] = []
        for req in requests:
            decision, reason = await self.check(req)
            results.append((req, decision, reason))
        return results
