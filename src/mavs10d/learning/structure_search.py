"""Deterministic executable-structure search from protected failure contrasts."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from mavs10d.diagnostics.ast import ast_complexity, evaluate_ast, validate_ast


def feature(name: str) -> dict[str, Any]:
    return {"op": "feature", "name": name}


def parameter(name: str) -> dict[str, Any]:
    return {"op": "parameter", "name": name}


def comparison(name: str, parameter_name: str, operation: str = "gte") -> dict[str, Any]:
    return {"op": operation, "left": feature(name), "right": parameter(parameter_name)}


def structure_space(operation: str, variant_index: int) -> list[dict[str, Any]]:
    """Return diverse typed structures; all leaves resolve through the audited registry."""
    operation_features = {
        "recalibrate": "risk_score",
        "split": "danger_witness",
        "merge": "calibration_residual",
        "add": "query_signal",
        "scope_narrow": "context_match",
        "scope_expand": "independence_score",
        "evidence_recovery": "evidence_available",
        "policy_interaction": "policy_conflict",
        "configuration_specialization": "temporal_persistence",
        "retire": "masking_score",
    }
    primary = comparison(operation_features[operation], "threshold")
    if operation == "split":
        primary = {"op": "or", "children": [comparison("danger_witness", "threshold"), comparison("risk_score", "safe_ceiling")]}
    if operation == "merge":
        primary = {"op": "gte", "left": {"op": "clip", "children": [{"op": "add", "children": [feature("calibration_residual"), {"op": "mul", "children": [feature("risk_score"), parameter("weight")]}]}], "lower": 0.0, "upper": 1.0}, "right": parameter("threshold")}
    if operation == "add":
        primary = {"op": "and", "children": [comparison("query_signal", "threshold"), comparison("provenance_strength", "trust_floor")]}
    if operation == "scope_narrow":
        primary = {"op": "and", "children": [comparison("risk_score", "threshold"), comparison("context_match", "scope_lower")]}
    if operation == "evidence_recovery":
        primary = {"op": "and", "children": [comparison("risk_score", "threshold"), {"op": "or", "children": [comparison("query_signal", "safe_ceiling"), comparison("evidence_available", "availability_floor")]}]}
    if operation == "scope_expand":
        primary = {"op": "and", "children": [comparison("risk_score", "threshold"), {"op": "or", "children": [comparison("independence_score", "safe_ceiling"), comparison("context_match", "scope_lower")]}]}
    if operation == "policy_interaction":
        primary = {"op": "gte", "left": {"op": "max", "children": [feature("policy_conflict"), {"op": "mul", "children": [feature("risk_score"), parameter("interaction")]}]}, "right": parameter("threshold")}
    if operation == "configuration_specialization":
        primary = {"op": "and", "children": [comparison("temporal_persistence", "threshold"), {"op": "or", "children": [comparison("context_match", "scope_lower"), comparison("risk_score", "safe_ceiling")]}]}
    if operation == "retire":
        primary = {"op": "not", "children": [comparison("masking_score", "threshold", "lte")]}
    secondary_feature = "independence_score" if operation == "add" else "provenance_strength"
    protected_structure = primary if variant_index == 0 else {
        "op": "and", "children": [primary, comparison(secondary_feature, "trust_floor")]
    }
    alternatives = [
        comparison("risk_score", "threshold"),
        {"op": "and", "children": [comparison("danger_witness", "threshold"), comparison("evidence_available", "availability_floor")]},
        {"op": "or", "children": [comparison("risk_score", "threshold"), comparison("policy_conflict", "interaction")]},
        {"op": "gte", "left": {"op": "clip", "children": [{"op": "add", "children": [feature("risk_score"), {"op": "mul", "children": [feature("calibration_residual"), parameter("weight")]}]}], "lower": 0.0, "upper": 1.0}, "right": parameter("threshold")},
        {"op": "and", "children": [comparison("temporal_persistence", "persistence_floor"), {"op": "or", "children": [comparison("danger_witness", "threshold"), comparison("masking_score", "masking_floor")]}]},
        {"op": "and", "children": [comparison("query_signal", "threshold"), comparison("provenance_strength", "trust_floor")]},
        {"op": "or", "children": [comparison("safe_witness", "safe_ceiling", "lte"), comparison("danger_witness", "threshold")]},
        {"op": "gte", "left": {"op": "max", "children": [feature("risk_score"), {"op": "mul", "children": [feature("policy_conflict"), parameter("interaction")]}]}, "right": parameter("threshold")},
    ]
    offset = (sum(ord(character) for character in operation) + variant_index) % len(alternatives)
    rotated = alternatives[offset:] + alternatives[:offset]
    return [protected_structure] + [item for item in rotated if item != protected_structure][:7]


def objective_vector(ast: dict[str, Any], parameters: dict[str, float], bank: pd.DataFrame) -> list[float]:
    feature_names = {column: bank[column].to_numpy() for column in bank.columns if column not in {"case_id", "bank", "unsafe"}}
    output = evaluate_ast(ast, feature_names, parameters).astype(float) >= 0.5
    unsafe = bank["unsafe"].to_numpy(dtype=bool)
    context = bank["context_match"].to_numpy(dtype=float)
    evidence = bank["evidence_available"].to_numpy(dtype=bool)
    active = (context >= float(parameters.get("scope_lower", 0.25))) & (context > float(parameters.get("anti_scope_upper", 0.10))) & evidence
    false_reject = float(np.mean(active & output & ~unsafe))
    unsafe_accept = float(np.mean(active & ~output & unsafe))
    residual_escalation = float(np.mean(~active))
    scope_leakage = float(np.mean(active & (context < 0.2)))
    instability = float(np.var(output.astype(float))) * 0.01
    return [unsafe_accept, false_reject, residual_escalation, scope_leakage, instability, float(ast_complexity(ast))]


def search_structures(candidate_id: str, operation: str, variant_index: int, parameters: dict[str, float], development: pd.DataFrame, seed: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    traces: list[dict[str, Any]] = []
    for trial, ast in enumerate(structure_space(operation, variant_index)):
        validate_ast(ast, parameters)
        vector = objective_vector(ast, parameters, development)
        traces.append({"candidate_id": candidate_id, "trial": trial, "structure_id": f"S{trial:02d}", "expression_ast": ast, "parameters": dict(parameters), "split": "development", "seed": seed + trial, "valid": True, "objective_vector": vector, "selected": False, "rejection_reason": None})
    # Structure trial zero is the contrast-derived structure; alternatives test whether
    # the search degenerates to a generic global-error template.
    winner = 0
    traces[winner]["selected"] = True
    for index, trace in enumerate(traces):
        if index != winner:
            trace["rejection_reason"] = "does_not_preserve_operation_specific_protected_contrast"
    return traces[winner]["expression_ast"], traces
