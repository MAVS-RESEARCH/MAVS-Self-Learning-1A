"""Fail-closed Phase 6 lifecycle transition records."""

from __future__ import annotations


def lifecycle_decision(integrity_passed: bool, certification_passed: bool, replay_passed: bool) -> tuple[str, str]:
    if not integrity_passed:
        return "integrity_rejected", "independent_integrity_gate_failed"
    if not certification_passed:
        return "certification_rejected", "behavior_only_certification_gate_failed"
    if not replay_passed:
        return "quarantined", "deterministic_replay_failed"
    return "promoted", "all_independent_gates_passed"
