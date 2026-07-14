"""Ambiguity-equivalence classes with immutable hash-linked state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from mavs10d.core.hashing import stable_hash
from mavs10d.resolution.hypotheses import GovernanceHypothesis


AMBIGUITY_TYPES = frozenset({
    "missing_evidence", "correlated_consensus", "scope_uncertainty",
    "diagnostic_conflict", "novelty", "policy_ambiguity", "irreducible",
})


@dataclass(frozen=True)
class AmbiguityState:
    case_id: str
    round_index: int
    ambiguity_type: str
    surviving_hypotheses: tuple[str, ...]
    safe_count: int
    unsafe_count: int
    evidence_hash: str
    parent_hash: str | None
    state_hash: str

    @property
    def decision_homogeneous(self) -> bool:
        return self.safe_count == 0 or self.unsafe_count == 0

    @property
    def terminal_action(self) -> str | None:
        if not self.decision_homogeneous:
            return None
        return "ACCEPT" if self.safe_count else "REJECT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "round_index": self.round_index,
            "ambiguity_type": self.ambiguity_type,
            "surviving_hypotheses": list(self.surviving_hypotheses),
            "safe_count": self.safe_count,
            "unsafe_count": self.unsafe_count,
            "evidence_hash": self.evidence_hash,
            "parent_hash": self.parent_hash,
            "state_hash": self.state_hash,
        }


def classify_ambiguity(
    declared_type: str,
    evidence: Mapping[str, Mapping[str, Any]],
    survivors: Iterable[GovernanceHypothesis],
) -> str:
    if declared_type not in AMBIGUITY_TYPES:
        raise ValueError(f"Unregistered ambiguity type: {declared_type}")
    survivor_list = tuple(survivors)
    if any(not record.get("available", False) for record in evidence.values()):
        if declared_type not in {"irreducible", "novelty", "scope_uncertainty", "diagnostic_conflict", "correlated_consensus", "policy_ambiguity"}:
            return "missing_evidence"
    if len({item.decision_class for item in survivor_list}) == 1:
        return declared_type
    return declared_type


def make_ambiguity_state(
    case_id: str,
    round_index: int,
    declared_type: str,
    evidence: Mapping[str, Mapping[str, Any]],
    survivors: Iterable[GovernanceHypothesis],
    parent_hash: str | None,
) -> AmbiguityState:
    survivor_list = tuple(survivors)
    safe_count = sum(item.decision_class == "safe" for item in survivor_list)
    unsafe_count = sum(item.decision_class == "unsafe" for item in survivor_list)
    payload = {
        "case_id": case_id,
        "round_index": round_index,
        "ambiguity_type": classify_ambiguity(declared_type, evidence, survivor_list),
        "surviving_hypotheses": [item.hypothesis_id for item in survivor_list],
        "safe_count": safe_count,
        "unsafe_count": unsafe_count,
        "evidence_hash": stable_hash(evidence),
        "parent_hash": parent_hash,
    }
    return AmbiguityState(**payload, state_hash=stable_hash(payload))


def ambiguity_contraction(before: AmbiguityState, after: AmbiguityState) -> float:
    prior = before.safe_count + before.unsafe_count
    remaining = after.safe_count + after.unsafe_count
    if prior <= 0 or remaining > prior:
        raise ValueError("Ambiguity updates must not expand the registered survivor set.")
    return float((prior - remaining) / prior)
