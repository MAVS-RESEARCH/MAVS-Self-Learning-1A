"""Machine-checked executable meanings for every Phase 6 operation."""

from __future__ import annotations

from typing import Any

from mavs10d.core.hashing import stable_hash
from mavs10d.diagnostics.ast import canonicalize_ast, collect_feature_references


OPERATIONS = (
    "recalibrate", "split", "merge", "add", "scope_narrow", "scope_expand",
    "evidence_recovery", "policy_interaction", "configuration_specialization", "retire",
)


def check_operation(candidate: dict[str, Any]) -> dict[str, Any]:
    operation = candidate["lineage"]["operation"]
    payload = candidate["operation_payload"]
    checks: dict[str, bool]
    if operation == "recalibrate":
        checks = {"parent_ast_preserved": canonicalize_ast(payload["parent_expression_ast"]) == canonicalize_ast(candidate["expression_ast"]), "parameters_independently_fitted": payload["parent_parameters"] != candidate["parameters"] and bool(payload.get("fit_trace")), "protected_gain": float(payload.get("protected_gain", 0.0)) > 0.0}
    elif operation == "split":
        children = payload.get("children", [])
        checks = {"two_distinct_children": len(children) >= 2 and len({stable_hash(canonicalize_ast(child["expression_ast"])) for child in children}) == len(children), "regime_evidence": len(payload.get("separated_regimes", [])) >= 2}
    elif operation == "merge":
        checks = {"multiple_parents": len(candidate["lineage"]["parents"]) >= 2 and len(payload.get("parent_programs", [])) >= 2, "redundancy_or_cost_reduced": float(payload.get("redundancy_before", 0.0)) > float(payload.get("redundancy_after", 1.0)), "protected_closure_preserved": float(payload.get("protected_error_after", 1.0)) <= float(payload.get("protected_error_before", 0.0))}
    elif operation == "add":
        parent_references = set(collect_feature_references(payload["parent_expression_ast"]))
        candidate_references = set(collect_feature_references(candidate["expression_ast"]))
        checks = {"new_dependency": bool(candidate_references - parent_references) and set(payload.get("new_dependencies", [])) == candidate_references - parent_references, "new_extension_witness": bool(payload.get("witness_id"))}
    elif operation == "scope_narrow":
        checks = {"executable_scope_changed": canonicalize_ast(payload["parent_positive_scope_ast"]) != canonicalize_ast(candidate["positive_scope_ast"]) or canonicalize_ast(payload["parent_anti_scope_ast"]) != canonicalize_ast(candidate["anti_scope_ast"]), "neighbor_deactivated": bool(payload.get("deactivated_neighbor_case_ids")), "retained_scope_valid": bool(payload.get("retained_case_ids"))}
    elif operation == "scope_expand":
        checks = {"executable_scope_changed": canonicalize_ast(payload["parent_positive_scope_ast"]) != canonicalize_ast(candidate["positive_scope_ast"]), "new_region": bool(payload.get("new_region_case_ids")), "boundary_anti_scope_holdout_analogue": set(payload.get("passed_suites", [])) >= {"boundary", "anti_scope", "holdout", "disjoint_analogue"}}
    elif operation == "evidence_recovery":
        record = payload.get("acquisition_record", {})
        checks = {"executed_acquisition": record.get("status") == "executed" and bool(record.get("consumed_feature")), "provenance_cost_information_gain": bool(record.get("provenance")) and float(record.get("cost", -1.0)) >= 0.0 and float(record.get("realized_information_gain", 0.0)) > 0.0}
    elif operation == "policy_interaction":
        checks = {"typed_relationship_changed": payload.get("before_relationship") != payload.get("after_relationship") and payload.get("after_relationship", {}).get("type") in {"policy_evidence", "policy_conflict"}, "authority_counterfactual_declared": payload.get("after_relationship", {}).get("authority") in {"observation", "query", "soft", "terminal"} and bool(payload.get("counterfactual_obligation"))}
    elif operation == "configuration_specialization":
        checks = {"mapping_or_terminal_changed": payload.get("mapping_before") != payload.get("mapping_after"), "fallback_and_scope_preserved": payload.get("mapping_after", {}).get("fallback") == payload.get("mapping_before", {}).get("fallback") and bool(payload.get("scope_proof_case_ids"))}
    elif operation == "retire":
        checks = {"influence_eligibility_removed": payload.get("runtime_eligibility_before") is True and payload.get("runtime_eligibility_after") is False, "lineage_evidence_replay_rollback_preserved": set(payload.get("preserved_artifacts", [])) >= {"lineage", "counterexamples", "evidence", "replay", "rollback"}}
    else:
        checks = {"known_operation": False}
    return {"operation": operation, "checks": checks, "passed": all(checks.values()), "reason_code": None if all(checks.values()) else "operation_semantic_delta_missing"}


def compliant_payload(operation: str, expression_ast: dict[str, Any], parameters: dict[str, float], positive_scope_ast: dict[str, Any], anti_scope_ast: dict[str, Any]) -> dict[str, Any]:
    risk_parent = {"op": "gte", "left": {"op": "feature", "name": "risk_score"}, "right": {"op": "parameter", "name": "threshold"}}
    payloads = {
        "recalibrate": {"parent_expression_ast": expression_ast, "parent_parameters": {**parameters, "threshold": min(0.95, parameters["threshold"] + 0.1)}, "fit_trace": "parameter_search.parquet", "protected_gain": 0.02},
        "split": {"children": [{"expression_ast": expression_ast}, {"expression_ast": {"op": "and", "children": [expression_ast, {"op": "gte", "left": {"op": "feature", "name": "context_match"}, "right": {"op": "parameter", "name": "scope_lower"}}]}}], "separated_regimes": ["high_context", "low_context"]},
        "merge": {"parent_programs": [risk_parent, {"op": "gte", "left": {"op": "feature", "name": "danger_witness"}, "right": {"op": "parameter", "name": "threshold"}}], "redundancy_before": 0.50, "redundancy_after": 0.20, "protected_error_before": 0.20, "protected_error_after": 0.18},
        "add": {"parent_expression_ast": risk_parent, "new_dependencies": sorted(set(collect_feature_references(expression_ast)) - {"risk_score"}), "witness_id": "perception_extension_witness.json"},
        "scope_narrow": {"parent_positive_scope_ast": {"op": "constant", "value": True}, "parent_anti_scope_ast": {"op": "constant", "value": False}, "deactivated_neighbor_case_ids": ["anti_scope-0000"], "retained_case_ids": ["retained-0000"]},
        "scope_expand": {"parent_positive_scope_ast": {"op": "gte", "left": {"op": "feature", "name": "context_match"}, "right": {"op": "constant", "value": 0.50}}, "new_region_case_ids": ["positive_scope_boundary-0032"], "passed_suites": ["boundary", "anti_scope", "holdout", "disjoint_analogue"]},
        "evidence_recovery": {"acquisition_record": {"status": "executed", "consumed_feature": "query_signal", "provenance": "audited_query", "availability": "declared_per_case", "cost": 1.0, "realized_information_gain": 0.50}},
        "policy_interaction": {"before_relationship": {"type": "policy_evidence", "authority": "observation"}, "after_relationship": {"type": "policy_conflict", "authority": "terminal"}, "counterfactual_obligation": "policy_conflict_inversion"},
        "configuration_specialization": {"mapping_before": {"specialized": "incumbent", "fallback": "incumbent"}, "mapping_after": {"specialized": "candidate", "fallback": "incumbent"}, "scope_proof_case_ids": ["positive_scope_boundary-0032", "anti_scope-0000"]},
        "retire": {"runtime_eligibility_before": True, "runtime_eligibility_after": False, "preserved_artifacts": ["lineage", "counterexamples", "evidence", "replay", "rollback"]},
    }
    return dict(payloads[operation])
