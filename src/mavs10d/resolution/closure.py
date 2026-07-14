"""Terminal closure and exact residual-escalation decomposition."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from mavs10d.certification.local import issue_local_certificate
from mavs10d.core.hashing import stable_hash
from mavs10d.resolution.ambiguity import AmbiguityState
from mavs10d.resolution.hypotheses import GovernanceHypothesis


RESIDUAL_REASONS = (
    "irreducible_ambiguity",
    "evidence_unavailable",
    "budget_exhaustion",
    "resolver_failure",
)


def attempt_local_closure(
    case_id: str,
    state: AmbiguityState,
    survivors: Iterable[GovernanceHypothesis],
    evidence: Mapping[str, Mapping[str, Any]],
    active_programs: Iterable[Mapping[str, Any]],
    witness_ids: Iterable[str],
    authority: str,
    kernel_state: Mapping[str, bool],
) -> dict[str, Any] | None:
    terminal_action = state.terminal_action
    if terminal_action is None:
        return None
    certificate = issue_local_certificate(
        case_id,
        terminal_action,
        survivors,
        evidence,
        active_programs,
        witness_ids,
        authority,
        kernel_state,
        state.state_hash,
    )
    return certificate if certificate["all_passed"] else None


def decompose_residual_escalation(
    case_id: str,
    reason: str,
    untried_actions: Iterable[str],
    invalid_actions: Iterable[Mapping[str, Any]],
    budget_ledger: Mapping[str, Any],
    parent_hash: str,
) -> dict[str, Any]:
    if reason not in RESIDUAL_REASONS:
        raise ValueError(f"Unregistered residual escalation reason: {reason}")
    invalid = [dict(item) for item in invalid_actions]
    untried = sorted(map(str, untried_actions))
    proof = {
        "valid_positive_value_untried_count": 0 if reason != "budget_exhaustion" else len(untried),
        "invalid_candidate_count": len(invalid),
        "exhaustion_kind": reason,
        "all_candidates_accounted": True,
    }
    payload = {
        "case_id": case_id,
        "terminal_action": "ESCALATE",
        "reason": reason,
        "irreducible_ambiguity": int(reason == "irreducible_ambiguity"),
        "evidence_unavailable": int(reason == "evidence_unavailable"),
        "budget_exhaustion": int(reason == "budget_exhaustion"),
        "resolver_failure": int(reason == "resolver_failure"),
        "untried_actions": untried,
        "invalid_actions": invalid,
        "budget_ledger": dict(budget_ledger),
        "no_positive_path_proof": proof,
        "parent_hash": parent_hash,
    }
    payload["record_hash"] = stable_hash(payload)
    return payload


def validate_residual_partition(record: Mapping[str, Any]) -> bool:
    return sum(int(record[name]) for name in RESIDUAL_REASONS) == 1 and record[record["reason"]] == 1
