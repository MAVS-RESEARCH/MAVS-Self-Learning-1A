"""Independent local closure obligations for case-specific terminal authority."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from mavs10d.core.hashing import stable_hash
from mavs10d.resolution.hypotheses import GovernanceHypothesis


OBLIGATION_NAMES = (
    "hypothesis_separation",
    "witness_sufficiency",
    "executable_scope",
    "evidence_integrity",
    "counterfactual_stability",
    "interaction_safety",
    "authority",
    "risk_justification",
    "kernel_preservation",
    "replay",
)


def evaluate_local_obligations(
    terminal_action: str,
    survivors: Iterable[GovernanceHypothesis],
    evidence: Mapping[str, Mapping[str, Any]],
    active_programs: Iterable[Mapping[str, Any]],
    witness_ids: Iterable[str],
    authority: str,
    kernel_state: Mapping[str, bool],
    trace_parent_hash: str,
) -> dict[str, bool]:
    survivor_list = tuple(survivors)
    programs = tuple(active_programs)
    expected_class = "safe" if terminal_action == "ACCEPT" else "unsafe"
    witness_records = [evidence.get(item, {}) for item in witness_ids]
    obligations = {
        "hypothesis_separation": bool(survivor_list) and all(item.decision_class == expected_class for item in survivor_list),
        "witness_sufficiency": bool(witness_records) and all(item.get("available", False) and item.get("trusted", False) and item.get("provenance_valid", False) for item in witness_records),
        "executable_scope": all(item.get("scope_certified", False) for item in programs),
        "evidence_integrity": all(
            record.get("available", False)
            and record.get("trusted", False)
            and record.get("fresh", False)
            and record.get("provenance_valid", False)
            for record in witness_records
        ),
        "counterfactual_stability": all(record.get("counterfactual_stable", False) for record in witness_records),
        "interaction_safety": all(
            len(item.get("influential_basis", [])) <= 1 or bool(item.get("interaction_certificates"))
            for item in programs
        ),
        "authority": authority in {"L2", "L3"},
        "risk_justification": all(record.get("risk_justification") in {"certified_class", "validated_neighborhood", "deterministic_invariant", "approved_statistical_certificate"} for record in witness_records),
        "kernel_preservation": all(bool(kernel_state.get(name, False)) for name in ("hard_veto", "mitigation", "monotonicity", "traceability", "rollback")),
        "replay": isinstance(trace_parent_hash, str) and len(trace_parent_hash) == 64,
    }
    return obligations


def issue_local_certificate(
    case_id: str,
    terminal_action: str,
    survivors: Iterable[GovernanceHypothesis],
    evidence: Mapping[str, Mapping[str, Any]],
    active_programs: Iterable[Mapping[str, Any]],
    witness_ids: Iterable[str],
    authority: str,
    kernel_state: Mapping[str, bool],
    trace_parent_hash: str,
) -> dict[str, Any]:
    survivor_list = tuple(survivors)
    witness_list = tuple(witness_ids)
    obligations = evaluate_local_obligations(
        terminal_action,
        survivor_list,
        evidence,
        active_programs,
        witness_list,
        authority,
        kernel_state,
        trace_parent_hash,
    )
    payload = {
        "certificate_id": f"LC-{stable_hash({'case': case_id, 'parent': trace_parent_hash, 'action': terminal_action})[:20]}",
        "case_id": case_id,
        "terminal_action": terminal_action,
        "surviving_hypotheses": [item.hypothesis_id for item in survivor_list],
        "obligations": obligations,
        "all_passed": all(obligations.values()),
        "witness_ids": list(witness_list),
        "authority": authority,
        "parent_hash": trace_parent_hash,
    }
    payload["certificate_hash"] = stable_hash(payload)
    return payload


def independently_recompute_certificate(
    certificate: Mapping[str, Any],
    survivors: Iterable[GovernanceHypothesis],
    evidence: Mapping[str, Mapping[str, Any]],
    active_programs: Iterable[Mapping[str, Any]],
    kernel_state: Mapping[str, bool],
) -> dict[str, Any]:
    expected = issue_local_certificate(
        str(certificate["case_id"]),
        str(certificate["terminal_action"]),
        survivors,
        evidence,
        active_programs,
        certificate["witness_ids"],
        str(certificate["authority"]),
        kernel_state,
        str(certificate["parent_hash"]),
    )
    return {
        "obligations_match": expected["obligations"] == certificate["obligations"],
        "hash_match": expected["certificate_hash"] == certificate["certificate_hash"],
        "all_passed_match": expected["all_passed"] == certificate["all_passed"],
        "passed": expected == dict(certificate),
    }
