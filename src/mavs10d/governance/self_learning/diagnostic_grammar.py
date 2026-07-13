"""Explicit serializable grammar for bounded diagnostic and configuration proposals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Mapping

from mavs10d.core.hashing import stable_hash


class ProposalOperation(StrEnum):
    RECALIBRATE = "recalibrate"
    SCOPE_NARROW = "scope_narrow"
    SCOPE_EXPAND = "scope_expand"
    SPLIT = "split"
    MERGE = "merge"
    ADD = "add"
    RETIRE = "retire"
    POLICY_INTERACTION = "policy_interaction"
    CONFIGURATION_SPECIALIZATION = "configuration_specialization"
    EVIDENCE_RECOVERY = "evidence_recovery"


OPERATION_FEATURES: Mapping[ProposalOperation, str] = {
    ProposalOperation.RECALIBRATE: "calibration_corrected_risk",
    ProposalOperation.SCOPE_NARROW: "scoped_provenance_risk",
    ProposalOperation.SCOPE_EXPAND: "homologous_scope_risk",
    ProposalOperation.SPLIT: "split_correlation_risk",
    ProposalOperation.MERGE: "merged_masking_risk",
    ProposalOperation.ADD: "masked_safe_evidence_risk",
    ProposalOperation.RETIRE: "stable_shift_risk",
    ProposalOperation.POLICY_INTERACTION: "policy_interaction_risk",
    ProposalOperation.CONFIGURATION_SPECIALIZATION: "regime_specific_risk",
    ProposalOperation.EVIDENCE_RECOVERY: "alternate_view_risk",
}
ALLOWED_PRIMITIVES = frozenset(
    {
        "threshold",
        "monotone_transform",
        "conjunction",
        "disjunction",
        "bounded_weighted_combination",
        "evidence_presence",
        "evidence_provenance",
        "agreement",
        "diversity",
        "correlation",
        "entropy",
        "calibration_residual",
        "temporal_persistence",
        "change_statistic",
        "nearest_validated_support",
        "novelty",
        "counterfactual_stability",
        "scope_predicate",
        "response_routing",
        "bounded_conjunction",
    }
)


@dataclass(frozen=True)
class GrammarExpression:
    primitive: str
    feature: str
    operator: str
    threshold: float
    monotone: str
    lower_bound: float
    upper_bound: float
    weights: Mapping[str, float]

    def __post_init__(self) -> None:
        if self.primitive not in ALLOWED_PRIMITIVES:
            raise ValueError("Diagnostic expression uses a non-approved primitive.")
        if self.operator not in {">=", ">", "<=", "<", "and", "or", "weighted"}:
            raise ValueError("Diagnostic expression operator is not approved.")
        if self.monotone not in {"increasing", "decreasing", "none"}:
            raise ValueError("Monotonicity declaration is invalid.")
        if not self.lower_bound <= self.threshold <= self.upper_bound:
            raise ValueError("Diagnostic threshold lies outside declared bounds.")
        if any(value < 0.0 or value > 1.0 for value in self.weights.values()):
            raise ValueError("Diagnostic weights must be bounded within [0, 1].")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RepairCandidate:
    candidate_id: str
    proposal_id: str
    name: str
    operation: ProposalOperation
    intended_scope: Mapping[str, Any]
    exact_function: GrammarExpression
    threshold: float
    allowed_influence: Mapping[str, float]
    bounds: Mapping[str, float]
    invariants: tuple[str, ...]
    provenance: Mapping[str, Any]
    parent_id: str
    exact_delta: Mapping[str, Any]
    expected_benefit: Mapping[str, float]
    expected_failures: tuple[str, ...]
    validation_plan: Mapping[str, Any]
    rollback_target: str
    complexity: int

    def __post_init__(self) -> None:
        if not self.invariants or not self.rollback_target or not self.parent_id:
            raise ValueError("Candidate requires invariants, parent, and rollback target.")
        if self.complexity < 1:
            raise ValueError("Candidate complexity must be positive.")
        if any(value < 0.0 for value in self.allowed_influence.values()):
            raise ValueError("Allowed influence must be non-negative.")
        if self.threshold != self.exact_function.threshold:
            raise ValueError("Candidate threshold must match its exact function.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["operation"] = self.operation.value
        return payload


def make_candidate_id(payload: Mapping[str, Any]) -> str:
    return f"candidate-{stable_hash(payload)[:24]}"


def evaluate_candidate(candidate: RepairCandidate, visible_features: Mapping[str, Any], base_action: str) -> tuple[str, bool]:
    """Execute only the serialized bounded rule; return action and query-use flag."""

    scope = candidate.intended_scope
    if any(visible_features.get(key) != value for key, value in scope.items() if key != "target_context"):
        return base_action, False
    if scope.get("target_context") is True and not bool(visible_features.get("target_context", False)):
        return base_action, False
    value = float(visible_features.get(candidate.exact_function.feature, 0.5))
    action = "reject" if value >= candidate.threshold else "accept"
    return action, candidate.operation == ProposalOperation.EVIDENCE_RECOVERY
