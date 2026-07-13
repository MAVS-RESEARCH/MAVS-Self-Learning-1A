"""Auditable Phase 5 consolidation changes and protected retention decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from mavs10d.core.hashing import stable_hash


@dataclass(frozen=True)
class ConsolidationChange:
    generation: int
    ablation_id: str
    condition: str
    action: str
    active_before: int
    active_after: int
    complexity_delta: int
    retained_replay_passed: bool
    catastrophic_interference: int
    rollback_target: str

    @property
    def change_hash(self) -> str:
        return stable_hash(asdict(self))


def consolidation_change(generation: int, ablation_id: str, condition: str, active_before: int, enabled: bool, retention_passed: bool) -> ConsolidationChange:
    active_after = max(8, int(round(active_before * 0.78))) if enabled else active_before
    action = "merge_prune_recalibrate" if enabled else "carry_all"
    return ConsolidationChange(
        generation, ablation_id, condition, action, active_before, active_after,
        active_after - active_before, retention_passed, 0 if retention_passed else 1,
        f"{ablation_id}-{condition}-g{generation}-preconsolidation",
    )
