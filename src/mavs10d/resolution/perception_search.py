"""Fail-closed conditional protected perception-extension search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from mavs10d.diagnostics.interactions import enforce_interaction_status
from mavs10d.diagnostics.ast import evaluate_ast
from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.diagnostics.semantic_hash import semantic_hash
from mavs10d.memory.negative_knowledge import NegativeKnowledge


@dataclass(frozen=True)
class SearchFinding:
    action_id: str
    valid: bool
    reason: str
    rank: tuple[float, ...] | None


@dataclass(frozen=True)
class SearchResult:
    selected: dict[str, Any] | None
    findings: tuple[SearchFinding, ...]


def indexed_library_view(library_size: int, case_action_count: int, target_contrast: str) -> dict[str, Any]:
    """Represent contrast indexing over a broad dormant persistent library."""
    if library_size < case_action_count or library_size <= 0:
        raise ValueError("Total library size cannot be smaller than the case-indexed action set.")
    return {
        "total_library_size": int(library_size),
        "conditionally_indexed_count": int(case_action_count),
        "dormant_out_of_contrast_count": int(library_size - case_action_count),
        "target_contrast": target_contrast,
        "global_cumulative_activation": False,
    }


def _eligible(action: Mapping[str, Any], evidence: Mapping[str, Mapping[str, Any]]) -> bool:
    prerequisites = action.get("prerequisites", [])
    for requirement in prerequisites:
        record = evidence.get(str(requirement["field"]))
        if not record or not record.get("available", False) or record.get("value") != requirement["value"]:
            return False
    return True


def filter_reason(
    action: Mapping[str, Any],
    evidence: Mapping[str, Mapping[str, Any]],
    negative_knowledge: NegativeKnowledge,
    seen_semantic_ids: set[str],
    seen_behavioral_ids: set[str],
) -> str | None:
    if not action.get("target_contrast"):
        return "missing_named_contrast"
    if not _eligible(action, evidence):
        return "prerequisite_not_observed"
    if float(action.get("expected_contraction", 0.0)) <= 0.0:
        return "nonpositive_conditional_perception_gain"
    if float(action.get("protected_regression", 0.0)) > 0.0:
        return "protected_regression"
    if not action.get("positive_scope", False):
        return "outside_positive_scope"
    if action.get("anti_scope", False):
        return "executable_anti_scope"
    if not action.get("provenance_valid", False):
        return "invalid_provenance"
    if float(action.get("trust", 1.0)) < float(action.get("minimum_trust", 0.0)):
        return "insufficient_trust"
    if action.get("semantic_id") and action["semantic_id"] in seen_semantic_ids:
        return "semantic_duplicate"
    if action.get("behavioral_id") and action["behavioral_id"] in seen_behavioral_ids:
        return "behavioral_redundancy"
    negative_reason = negative_knowledge.action_block_reason(dict(action))
    if negative_reason:
        return negative_reason
    try:
        influence_mode = enforce_interaction_status(
            str(action.get("interaction_status", "single")),
            bool(action.get("terminal_influence", False)),
        )
    except PermissionError:
        return "prohibited_interaction"
    if influence_mode == "observation_only" and action.get("action_type") == "DIAGNOSTIC_PROGRAM" and action.get("terminal_influence", False):
        return "untested_interaction_observation_only"
    if action.get("runtime_created", False) and not action.get("phase6_integrity_passed", False):
        return "phase6_integrity_not_passed"
    if action.get("activation_contract"):
        try:
            candidate = ExecutableDiagnostic.from_dict(action["activation_contract"])
            if semantic_hash(candidate) != str(action.get("semantic_id")):
                return "activation_contract_semantic_mismatch"
            features = {
                name: [float(evidence[name]["value"])]
                for name in candidate.all_feature_references()
                if name in evidence and evidence[name].get("available", False)
            }
            if set(features) != set(candidate.all_feature_references()):
                return "activation_contract_evidence_unavailable"
            positive = bool(evaluate_ast(candidate.positive_scope_ast, features, candidate.parameters)[0])
            anti = bool(evaluate_ast(candidate.anti_scope_ast, features, candidate.parameters)[0])
            active = bool(evaluate_ast(candidate.expression_ast, features, candidate.parameters)[0])
            if not positive or anti or not active:
                return "executable_activation_contract_inactive"
        except (KeyError, TypeError, ValueError):
            return "activation_contract_invalid"
    return None


def rank_actions(
    actions: Iterable[Mapping[str, Any]],
    evidence: Mapping[str, Mapping[str, Any]],
    negative_knowledge: NegativeKnowledge,
) -> SearchResult:
    findings: list[SearchFinding] = []
    valid: list[tuple[tuple[float, ...], dict[str, Any]]] = []
    seen_semantic: set[str] = set()
    seen_behavioral: set[str] = set()
    for raw in sorted(actions, key=lambda item: str(item["action_id"])):
        action = dict(raw)
        reason = filter_reason(action, evidence, negative_knowledge, seen_semantic, seen_behavioral)
        if reason:
            findings.append(SearchFinding(str(action["action_id"]), False, reason, None))
            continue
        if action.get("semantic_id"):
            seen_semantic.add(str(action["semantic_id"]))
        if action.get("behavioral_id"):
            seen_behavioral.add(str(action["behavioral_id"]))
        rank = (
            -float(action.get("unsafe_acceptance_protection", 0.0)),
            -float(action.get("false_rejection_protection", 0.0)),
            -float(action["expected_contraction"]),
            float(action.get("scope_risk", 0.0)),
            float(action.get("cost", 0.0)),
            float(action.get("latency_ms", 0.0)),
        )
        findings.append(SearchFinding(str(action["action_id"]), True, "valid", rank))
        valid.append((rank + (str(action["action_id"]),), action))
    selected = min(valid, key=lambda item: item[0])[1] if valid else None
    return SearchResult(selected=selected, findings=tuple(findings))
