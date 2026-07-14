"""Fail-closed Phase 6 lifecycle transition records."""

from __future__ import annotations

from typing import Any, Mapping

from mavs10d.certification.blind_api import assert_blind_payload
from mavs10d.core.hashing import stable_hash


def lifecycle_decision(integrity_passed: bool, certification_passed: bool, replay_passed: bool) -> tuple[str, str]:
    if not integrity_passed:
        return "integrity_rejected", "independent_integrity_gate_failed"
    if not certification_passed:
        return "certification_rejected", "behavior_only_certification_gate_failed"
    if not replay_passed:
        return "quarantined", "deterministic_replay_failed"
    return "promoted", "all_independent_gates_passed"


def certify_persistent_handoff(
    blind_request: Mapping[str, Any],
    independent_gate_vector: Mapping[str, Any],
    repeated_path_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Recheck a local-to-persistent handoff through the blind behavior boundary."""
    assert_blind_payload(blind_request)
    forbidden_path_fields = {"expected_outcome", "oracle_label", "unsafe", "hidden_world", "target_decision"}
    if forbidden_path_fields & set(repeated_path_evidence):
        raise ValueError("Persistent handoff evidence contains a forbidden outcome or oracle field.")
    gates = independent_gate_vector.get("gates", {})
    all_gates_passed = bool(gates) and all(bool(item.get("passed", False)) for item in gates.values())
    semantic_match = str(blind_request.get("anonymous_semantic_id")) == str(independent_gate_vector.get("anonymous_semantic_id"))
    replay_count = int(repeated_path_evidence.get("replay_count", 0))
    protected_regression = float(repeated_path_evidence.get("protected_regression", 1.0))
    scope_leakage = float(repeated_path_evidence.get("scope_leakage", 1.0))
    passed = all_gates_passed and semantic_match and replay_count >= 2 and protected_regression == 0.0 and scope_leakage == 0.0
    result = {
        "passed": passed,
        "anonymous_semantic_id": str(blind_request.get("anonymous_semantic_id")),
        "gate_count": len(gates),
        "all_phase6_gates_passed": all_gates_passed,
        "semantic_match": semantic_match,
        "replay_count": replay_count,
        "protected_regression": protected_regression,
        "scope_leakage": scope_leakage,
        "input_hash": stable_hash({"blind_request": blind_request, "gate_vector": independent_gate_vector, "path": repeated_path_evidence}),
    }
    return result
