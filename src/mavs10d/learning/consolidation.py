"""Governed consolidation that forgets eligibility without forgetting evidence."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from mavs10d.core.hashing import stable_hash


CONSOLIDATION_OPERATIONS = frozenset({"merge", "narrow", "split", "retire", "quarantine", "prohibit"})


def select_consolidation_operation(evidence: Mapping[str, Any]) -> str:
    if float(evidence.get("protected_regression", 0.0)) > 0.0 or float(evidence.get("scope_leakage", 0.0)) > 0.0:
        return "quarantine"
    if evidence.get("unsafe_interaction", False):
        return "prohibit"
    if float(evidence.get("conditional_redundancy", 0.0)) >= 0.95:
        return "merge"
    if evidence.get("neighbor_leakage", False):
        return "narrow"
    if evidence.get("mechanism_conflation", False):
        return "split"
    if float(evidence.get("conditional_perception_gain", 0.0)) <= 0.0 or evidence.get("dominated", False):
        return "retire"
    return "narrow"


def consolidate_knowledge(
    knowledge_id: str,
    lineage: Iterable[str],
    evidence: Mapping[str, Any],
    blind_certification: Mapping[str, Any],
    active_eligibility_count: int,
    active_cap: int,
) -> dict[str, Any]:
    operation = select_consolidation_operation(evidence)
    if operation not in CONSOLIDATION_OPERATIONS:
        raise RuntimeError("Invalid consolidation operation.")
    certification_passed = bool(blind_certification.get("passed", False))
    outperforms_parent = bool(evidence.get("outperforms_parent", False))
    active_eligible = (
        certification_passed
        and outperforms_parent
        and operation not in {"retire", "quarantine", "prohibit"}
        and active_eligibility_count < active_cap
    )
    status = "promoted" if active_eligible else operation + ("d" if operation.endswith("e") else "ed")
    if operation == "split":
        status = "split"
    if operation == "retire":
        status = "retired"
    if operation == "quarantine":
        status = "quarantined"
    if operation == "prohibit":
        status = "prohibited"
    payload = {
        "knowledge_id": knowledge_id,
        "kind": str(evidence.get("kind", "closure_program")),
        "semantic_distinction": str(evidence.get("semantic_distinction", "repeated protected closure path")),
        "positive_scope": list(map(str, evidence.get("positive_scope", ["registered_case_family"]))),
        "anti_scope": list(map(str, evidence.get("anti_scope", ["registered_neighbor_confounder"]))),
        "lineage": list(map(str, lineage)),
        "status": status,
        "active_eligible": active_eligible,
        "blind_certification": {
            "passed": certification_passed,
            "anonymous_semantic_id": str(blind_certification.get("anonymous_semantic_id", "")),
            "gate_count": int(blind_certification.get("gate_count", 0)),
        },
        "outperforms_parent": outperforms_parent,
        "recertification_due": bool(evidence.get("shifted_prior", False)),
    }
    payload["knowledge_hash"] = stable_hash(payload)
    return payload
