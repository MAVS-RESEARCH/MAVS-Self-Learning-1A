"""Semantic, behavioral, and template-collapse detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import pandas as pd

from mavs10d.diagnostics.ast import template_signature
from mavs10d.diagnostics.behavioral_fingerprint import behavioral_hash
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
