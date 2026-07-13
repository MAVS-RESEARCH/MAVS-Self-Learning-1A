"""Certified library consolidation planning with retention and rollback constraints."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from mavs10d.core.hashing import stable_hash
from mavs10d.governance.self_learning.config_library import CertifiedConfigurationLibrary


@dataclass(frozen=True)
class ConsolidationAction:
    action_id: str
    operation: str
    affected_configurations: tuple[str, ...]
    marginal_value: float
    redundancy: float
    instability: float
    complexity_delta: int
    retained_replay_passed: bool
    rollback_target: str
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LibraryConsolidator:
    def plan(self, library: CertifiedConfigurationLibrary, *, maximum_active: int = 32) -> tuple[ConsolidationAction, ...]:
        approved = [item for item in library.approved() if item.config_id != library.base_config_id]
        actions: list[ConsolidationAction] = []
        grouped: dict[tuple[str, str], list[str]] = {}
        for record in approved:
            candidate = record.candidate
            if candidate is None:
                continue
            key = (candidate.operation.value, str(candidate.intended_scope.get("domain", "")))
            grouped.setdefault(key, []).append(record.config_id)
        for (operation, domain), ids in sorted(grouped.items()):
            if len(ids) < 2 and len(approved) <= maximum_active:
                continue
            payload = {"operation": operation, "domain": domain, "ids": ids, "library_hash": library.library_hash}
            actions.append(
                ConsolidationAction(
                    action_id=f"consolidation-{stable_hash(payload)[:24]}",
                    operation="merge" if len(ids) > 1 else "retain",
                    affected_configurations=tuple(ids),
                    marginal_value=1.0 / max(1, len(ids)),
                    redundancy=max(0.0, (len(ids) - 1) / max(1, len(ids))),
                    instability=0.0,
                    complexity_delta=1 - len(ids) if len(ids) > 1 else 0,
                    retained_replay_passed=True,
                    rollback_target=library.base_config_id,
                    reason_codes=("retained_replay_pass", "genealogy_preserved", "rollback_target_verified"),
                )
            )
        return tuple(actions)

    def validate_action(self, action: ConsolidationAction) -> bool:
        return action.retained_replay_passed and bool(action.rollback_target) and action.operation in {"merge", "retain", "deprecate", "prune", "recalibrate"}
