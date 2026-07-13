"""Immutable Phase 3 safety kernel for candidate and promotion legality."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from mavs10d.governance.self_learning.diagnostic_grammar import RepairCandidate


REQUIRED_INVARIANTS = frozenset(
    {
        "approved_configuration_only",
        "hard_veto_dominance",
        "bounded_mitigation",
        "presence_not_harmfulness",
        "scope_bounded_influence",
        "complete_trace",
        "verified_rollback",
    }
)
FORBIDDEN_SOLE_VETO_FEATURES = frozenset(
    {"correlation_presence", "confidence_inflation", "missing_evidence", "evidence_unavailable"}
)


@dataclass(frozen=True)
class KernelEvidence:
    retained_unsafe_acceptances: int
    protected_regressions: int
    trace_complete: bool
    rollback_verified: bool
    retained_counterexamples_preserved: bool
    selector_fallback_verified: bool
    feedback_reliability: float


@dataclass(frozen=True)
class KernelResult:
    passed: bool
    checks: Mapping[str, bool]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ImmutableSafetyKernel:
    def __init__(self, mitigation_bound: float = 0.12) -> None:
        if not 0.0 <= mitigation_bound <= 1.0:
            raise ValueError("Mitigation bound must be within [0, 1].")
        self.mitigation_bound = mitigation_bound

    def validate(self, candidate: RepairCandidate, evidence: KernelEvidence) -> KernelResult:
        checks = {
            "candidate_not_live": candidate.provenance.get("live_control", False) is False,
            "required_invariants": REQUIRED_INVARIANTS <= set(candidate.invariants),
            "hard_veto_dominance": "hard_veto_dominance" in candidate.invariants,
            "bounded_mitigation": float(candidate.allowed_influence.get("mitigation", 0.0)) <= self.mitigation_bound,
            "presence_not_harmfulness": candidate.exact_function.feature not in FORBIDDEN_SOLE_VETO_FEATURES,
            "scope_bounded_influence": all(key in candidate.intended_scope for key in ("generation", "curriculum_id", "domain")),
            "monotone_danger": candidate.exact_function.monotone == "increasing",
            "zero_retained_unsafe_acceptance": evidence.retained_unsafe_acceptances == 0,
            "zero_protected_regression": evidence.protected_regressions == 0,
            "complete_trace": evidence.trace_complete,
            "verified_rollback": evidence.rollback_verified and bool(candidate.rollback_target),
            "counterexamples_preserved": evidence.retained_counterexamples_preserved,
            "selector_fallback": evidence.selector_fallback_verified,
            "reliable_feedback": evidence.feedback_reliability >= 0.75,
        }
        reasons = tuple(f"kernel_failed:{name}" for name, passed in checks.items() if not passed)
        return KernelResult(not reasons, checks, reasons or ("kernel_pass",))
