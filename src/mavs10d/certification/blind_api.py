"""Allowlisted serialization boundary between synthesis and certification."""

from __future__ import annotations

from typing import Any, Mapping

from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.diagnostics.semantic_hash import semantic_hash


FORBIDDEN_FIELDS = frozenset({
    "candidate_id", "candidate_name", "operation", "expected_outcome", "expected_class",
    "desired_promotion", "candidate_quality", "generator_truth", "curriculum", "generation",
    "hidden_world", "oracle_label", "target_promotion", "integrity_control", "certification_control",
})


def make_blind_request(candidate: ExecutableDiagnostic, suite_hashes: Mapping[str, str], incumbent_hash: str) -> dict[str, Any]:
    request = {
        "schema_version": "1.0.0",
        "anonymous_semantic_id": semantic_hash(candidate),
        "expression_ast": candidate.expression_ast,
        "parameters": candidate.parameters,
        "positive_scope_ast": candidate.positive_scope_ast,
        "anti_scope_ast": candidate.anti_scope_ast,
        "evidence_contract": candidate.evidence_contract,
        "influence_contract": candidate.influence_contract,
        "counterfactual_contract": candidate.counterfactual_contract,
        "incumbent_semantic_hash": incumbent_hash,
        "frozen_suite_hashes": dict(suite_hashes),
        "kernel_rules": {"terminal_requires_scope": True, "anti_scope_zero_influence": True, "missing_evidence_deactivates": True},
        "metric_definitions": {"protected_error": "incorrect active terminal decision / active decisions", "scope_leakage": "active anti-scope cases / anti-scope cases", "stability": "replay disagreement / cases"},
    }
    assert_blind_payload(request)
    return request


def candidate_from_blind_request(request: Mapping[str, Any]) -> ExecutableDiagnostic:
    """Reconstruct an executable anonymous candidate from allowlisted fields only."""
    assert_blind_payload(request)
    semantic_id = str(request["anonymous_semantic_id"])
    candidate = ExecutableDiagnostic(
        candidate_id=f"ANON-{semantic_id[:16]}",
        name="anonymous-executable-diagnostic",
        expression_ast=dict(request["expression_ast"]),
        parameters={str(key): float(value) for key, value in request["parameters"].items()},
        positive_scope_ast=dict(request["positive_scope_ast"]),
        anti_scope_ast=dict(request["anti_scope_ast"]),
        evidence_contract=dict(request["evidence_contract"]),
        influence_contract=dict(request["influence_contract"]),
        counterfactual_contract=dict(request["counterfactual_contract"]),
        lineage={"parents": [], "operation": "blind", "triggering_contrast": "withheld", "synthesis_evidence": ["serialized_allowlist"], "structure_trace": "withheld", "parameter_trace": "withheld", "rollback_target": "incumbent"},
        operation_payload={},
    )
    candidate.validate()
    return candidate


def assert_blind_payload(payload: Any, path: str = "$") -> None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_FIELDS or normalized.startswith("hidden_") or normalized.startswith("expected_"):
                raise ValueError(f"Forbidden field at blind boundary: {path}.{key}")
            assert_blind_payload(value, f"{path}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            assert_blind_payload(value, f"{path}[{index}]")
    elif isinstance(payload, str):
        lowered = payload.lower()
        if "phase6_evaluator_only_sentinel" in lowered:
            raise ValueError(f"Hidden-field taint at blind boundary: {path}")
