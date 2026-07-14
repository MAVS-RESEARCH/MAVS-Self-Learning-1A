"""Semantic, behavioral, and template-collapse detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import pandas as pd

from mavs10d.diagnostics.ast import template_signature
from mavs10d.diagnostics.behavioral_fingerprint import behavioral_hash, behaviorally_equivalent
from mavs10d.diagnostics.contracts import ExecutableDiagnostic
from mavs10d.diagnostics.semantic_hash import semantic_hash


def duplicate_classes(candidates: Iterable[ExecutableDiagnostic], fingerprints: dict[str, pd.DataFrame]) -> dict[str, Any]:
    semantic: dict[str, list[str]] = defaultdict(list)
    behavioral: dict[str, list[str]] = defaultdict(list)
    templates: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates:
        semantic[semantic_hash(candidate)].append(candidate.candidate_id)
        behavioral[behavioral_hash(fingerprints[candidate.candidate_id])].append(candidate.candidate_id)
        templates[template_signature(candidate.expression_ast)].append(candidate.candidate_id)
    return {
        "semantic_classes": [members for members in semantic.values() if len(members) > 1],
        "behavioral_classes": [members for members in behavioral.values() if len(members) > 1],
        "template_classes": list(templates.values()),
        "template_count": len(templates),
        "collapsed": len(templates) < 5,
    }


def integrity_reason(candidate: ExecutableDiagnostic, semantic_members: list[str], behavioral_members: list[str], fingerprint: pd.DataFrame) -> str | None:
    if candidate.integrity_control:
        if len(semantic_members) > 1:
            return "name_only_semantic_duplicate"
        return candidate.integrity_control
    if fingerprint["raw_output"].nunique() == 1:
        return "constant_output"
    if len(semantic_members) > 1 and candidate.candidate_id != semantic_members[0]:
        return "semantic_duplicate"
    if len(behavioral_members) > 1 and candidate.candidate_id != behavioral_members[0]:
        return "behavioral_equivalent_without_predeclared_gain"
    if not bool(fingerprint["active"].any()):
        return "behaviorally_null_no_op"
    return None


def classify_pathology(
    candidate: ExecutableDiagnostic,
    fingerprint: pd.DataFrame,
    *,
    parent: ExecutableDiagnostic | None = None,
    parent_fingerprint: pd.DataFrame | None = None,
    sibling: ExecutableDiagnostic | None = None,
    sibling_fingerprint: pd.DataFrame | None = None,
    truth: pd.DataFrame | None = None,
    certified_improvement: dict[str, Any] | None = None,
) -> str | None:
    """Classify adversarial integrity fixtures from executable identity and behavior."""
    if fingerprint["raw_output"].nunique() == 1:
        return "constant_output"
    if not bool(fingerprint["active"].any()) or not bool((fingerprint["query_influence"].abs() + fingerprint["terminal_influence"].abs()).any()):
        return "behaviorally_null_no_op"
    if parent is not None and semantic_hash(candidate) == semantic_hash(parent):
        return "parent_identical"
    if sibling is not None and semantic_hash(candidate) == semantic_hash(sibling):
        return "sibling_identical"
    comparison_frame = parent_fingerprint if parent_fingerprint is not None else sibling_fingerprint
    comparison_candidate = parent if parent_fingerprint is not None else sibling
    if comparison_frame is not None and comparison_candidate is not None and behaviorally_equivalent(fingerprint, comparison_frame):
        improvement = certified_improvement or {}
        if improvement.get("dimension") in {"cost", "calibration", "scope", "stability"} and float(improvement.get("after", 0.0)) < float(improvement.get("before", 0.0)):
            return "behavioral_equivalent_with_certified_improvement"
        return "behavioral_equivalent_without_predeclared_gain"
    if truth is not None:
        evaluated = fingerprint.merge(truth[["case_id", "unsafe"]], on="case_id", validate="one_to_one")
        evaluated["error"] = evaluated["active"] & (evaluated["discrete_output"].astype(bool) != evaluated["unsafe"].astype(bool))
        trigger = evaluated[evaluated["bank"] == "trigger"]
        holdout = evaluated[evaluated["bank"].isin(["holdout", "disjoint_analogue"])]
        trigger_error = float(trigger["error"].mean()) if len(trigger) else 1.0
        holdout_error = float(holdout["error"].mean()) if len(holdout) else 1.0
        if trigger_error <= 0.05 and holdout_error >= 0.25:
            return "trigger_only_overfit"
    return None
