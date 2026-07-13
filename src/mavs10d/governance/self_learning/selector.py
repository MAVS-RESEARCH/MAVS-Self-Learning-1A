"""Governed selector over approved configurations with certified fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from mavs10d.governance.self_learning.config_library import CertifiedConfigurationLibrary, ConfigurationRecord


@dataclass(frozen=True)
class SelectionResult:
    record: ConfigurationRecord
    applicability: float
    used_fallback: bool
    reason_code: str


class GovernedSelector:
    def __init__(self, library: CertifiedConfigurationLibrary, applicability_threshold: float = 1.0) -> None:
        self.library = library
        self.applicability_threshold = applicability_threshold

    def select(self, context: Mapping[str, Any]) -> SelectionResult:
        candidates: list[tuple[float, int, ConfigurationRecord]] = []
        for record in self.library.approved():
            record.eta.validate(require_approved=True)
            if record.config_id == self.library.base_config_id:
                continue
            score = _applicability(record.eta.activation_scope, context)
            candidates.append((score, record.created_sequence, record))
        if candidates:
            score, _, record = max(candidates, key=lambda item: (item[0], item[1]))
            if score >= self.applicability_threshold:
                return SelectionResult(record, score, False, "approved_scope_match")
        fallback = self.library.record(self.library.base_config_id)
        fallback.eta.validate(require_approved=True)
        best = max((item[0] for item in candidates), default=0.0)
        return SelectionResult(fallback, best, True, "low_applicability_certified_fallback")


def _applicability(scope: Mapping[str, Any], context: Mapping[str, Any]) -> float:
    if not scope:
        return 1.0
    matches = sum(1 for key, value in scope.items() if context.get(key) == value)
    return matches / len(scope)
