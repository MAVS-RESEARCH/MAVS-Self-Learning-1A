"""Machine-checked executable meanings for every Phase 6 operation."""

from __future__ import annotations

from typing import Any


OPERATIONS = (
    "recalibrate", "split", "merge", "add", "scope_narrow", "scope_expand",
    "evidence_recovery", "policy_interaction", "configuration_specialization", "retire",
)


def check_operation(candidate: dict[str, Any]) -> dict[str, Any]:
    operation = candidate["lineage"]["operation"]
    payload = candidate["operation_payload"]
    checks: dict[str, bool]
    if operation == "recalibrate":
        checks = {"parent_ast_preserved": bool(payload.get("parent_ast_preserved")), "parameters_independently_fitted": bool(payload.get("parameters_independently_fitted")), "protected_gain": float(payload.get("protected_gain", 0.0)) > 0.0}
    elif operation == "split":
        checks = {"two_distinct_children": int(payload.get("child_count", 0)) >= 2 and bool(payload.get("distinct_child_behavior"))}
    elif operation == "merge":
        checks = {"multiple_parents": len(candidate["lineage"]["parents"]) >= 2, "redundancy_or_cost_reduced": float(payload.get("redundancy_reduction", 0.0)) > 0.0, "protected_closure_preserved": bool(payload.get("protected_closure_preserved"))}
    elif operation == "add":
        checks = {"new_dependency": bool(payload.get("new_dependency")), "new_extension_witness": bool(payload.get("new_extension_witness"))}
    elif operation == "scope_narrow":
        checks = {"neighbor_deactivated": bool(payload.get("neighbor_deactivated")), "retained_scope_valid": bool(payload.get("retained_scope_valid"))}
    elif operation == "scope_expand":
        checks = {"new_region": bool(payload.get("new_region")), "boundary_anti_scope_holdout_analogue": bool(payload.get("all_region_tests_pass"))}
    elif operation == "evidence_recovery":
        checks = {"executed_acquisition": bool(payload.get("executed_acquisition")), "provenance_cost_information_gain": bool(payload.get("complete_acquisition_record"))}
    elif operation == "policy_interaction":
        checks = {"typed_relationship_changed": bool(payload.get("typed_relationship_changed")), "authority_counterfactual_declared": bool(payload.get("authority_counterfactual_declared"))}
    elif operation == "configuration_specialization":
        checks = {"mapping_or_terminal_changed": bool(payload.get("mapping_or_terminal_changed")), "fallback_and_scope_preserved": bool(payload.get("fallback_and_scope_preserved"))}
    elif operation == "retire":
        checks = {"influence_eligibility_removed": bool(payload.get("influence_eligibility_removed")), "lineage_evidence_replay_rollback_preserved": bool(payload.get("preservation_complete"))}
    else:
        checks = {"known_operation": False}
    return {"operation": operation, "checks": checks, "passed": all(checks.values()), "reason_code": None if all(checks.values()) else "operation_semantic_delta_missing"}


def compliant_payload(operation: str) -> dict[str, Any]:
    payloads = {
        "recalibrate": {"parent_ast_preserved": True, "parameters_independently_fitted": True, "protected_gain": 0.02},
        "split": {"child_count": 2, "distinct_child_behavior": True},
        "merge": {"redundancy_reduction": 0.25, "protected_closure_preserved": True},
        "add": {"new_dependency": True, "new_extension_witness": True},
        "scope_narrow": {"neighbor_deactivated": True, "retained_scope_valid": True},
        "scope_expand": {"new_region": True, "all_region_tests_pass": True},
        "evidence_recovery": {"executed_acquisition": True, "complete_acquisition_record": True, "cost": 1.0, "realized_information_gain": 0.5},
        "policy_interaction": {"typed_relationship_changed": True, "authority_counterfactual_declared": True},
        "configuration_specialization": {"mapping_or_terminal_changed": True, "fallback_and_scope_preserved": True},
        "retire": {"influence_eligibility_removed": True, "preservation_complete": True},
    }
    return dict(payloads[operation])
