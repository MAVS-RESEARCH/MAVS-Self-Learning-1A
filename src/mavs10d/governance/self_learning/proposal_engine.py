"""Least-complex-first proposal synthesis over the approved diagnostic grammar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from mavs10d.core.hashing import stable_hash
from mavs10d.governance.self_learning.diagnostic_grammar import (
    OPERATION_FEATURES,
    GrammarExpression,
    ProposalOperation,
    RepairCandidate,
    make_candidate_id,
)
from mavs10d.governance.self_learning.failure_attribution import AttributionResult
from mavs10d.governance.self_learning.memory import FailureCapsule
from mavs10d.governance.self_learning.meta_diagnostics import MetaDiagnosticState


SIGNAL_TO_OPERATION: Mapping[str, ProposalOperation] = {
    "calibration_residual": ProposalOperation.RECALIBRATE,
    "scope_leakage": ProposalOperation.SCOPE_NARROW,
    "coverage_gap": ProposalOperation.SCOPE_EXPAND,
    "witness_conflict": ProposalOperation.SPLIT,
    "diagnostic_redundancy": ProposalOperation.MERGE,
    "evidence_masking": ProposalOperation.ADD,
    "counterfactual_instability": ProposalOperation.RETIRE,
    "policy_conflict": ProposalOperation.POLICY_INTERACTION,
    "selector_uncertainty": ProposalOperation.CONFIGURATION_SPECIALIZATION,
    "evidence_unavailable": ProposalOperation.EVIDENCE_RECOVERY,
}
OPERATION_COMPLEXITY: Mapping[ProposalOperation, int] = {
    ProposalOperation.RECALIBRATE: 1,
    ProposalOperation.SCOPE_NARROW: 2,
    ProposalOperation.SCOPE_EXPAND: 2,
    ProposalOperation.MERGE: 3,
    ProposalOperation.SPLIT: 4,
    ProposalOperation.ADD: 4,
    ProposalOperation.RETIRE: 4,
    ProposalOperation.POLICY_INTERACTION: 5,
    ProposalOperation.CONFIGURATION_SPECIALIZATION: 6,
    ProposalOperation.EVIDENCE_RECOVERY: 7,
}


@dataclass(frozen=True)
class ProposalContext:
    generation: int
    curriculum_id: str
    domain: str
    parent_configuration_id: str
    trace_hash: str
    synthesis_manifest_hash: str


class ProposalEngine:
    """Generate machine-checkable candidates without certification or hidden labels."""

    def propose(
        self,
        capsule: FailureCapsule,
        meta: MetaDiagnosticState,
        attribution: AttributionResult,
        context: ProposalContext,
    ) -> tuple[RepairCandidate, ...]:
        ranked_signals = sorted(
            SIGNAL_TO_OPERATION,
            key=lambda name: (-meta.to_dict()[name], OPERATION_COMPLEXITY[SIGNAL_TO_OPERATION[name]], name),
        )
        if meta.evidence_unavailable >= 0.90:
            ranked_signals.remove("evidence_unavailable")
            ranked_signals.insert(0, "evidence_unavailable")
        primary = SIGNAL_TO_OPERATION[ranked_signals[0]]
        decoy = SIGNAL_TO_OPERATION[ranked_signals[1]]
        candidates = {
            operation: self._candidate(operation, capsule, attribution, context, rank)
            for rank, operation in enumerate((primary, decoy))
        }
        return tuple(sorted(candidates.values(), key=lambda item: (item.complexity, item.candidate_id)))

    def _candidate(
        self,
        operation: ProposalOperation,
        capsule: FailureCapsule,
        attribution: AttributionResult,
        context: ProposalContext,
        rank: int,
    ) -> RepairCandidate:
        feature = OPERATION_FEATURES[operation]
        primitive = _primitive_for(operation)
        expression = GrammarExpression(
            primitive=primitive,
            feature=feature,
            operator=">=",
            threshold=0.5,
            monotone="increasing",
            lower_bound=0.0,
            upper_bound=1.0,
            weights={feature: 1.0},
        )
        scope = {
            "generation": context.generation,
            "curriculum_id": context.curriculum_id,
            "domain": context.domain,
            "target_context": True,
        }
        core = {
            "operation": operation.value,
            "scope": scope,
            "function": expression.to_dict(),
            "parent": context.parent_configuration_id,
            "capsule": capsule.capsule_id,
            "rank": rank,
            "trace_hash": context.trace_hash,
        }
        candidate_id = make_candidate_id(core)
        proposal_id = f"proposal-{stable_hash({**core, 'candidate': candidate_id})[:24]}"
        return RepairCandidate(
            candidate_id=candidate_id,
            proposal_id=proposal_id,
            name=f"{operation.value}_{context.curriculum_id.lower()}_g{context.generation}",
            operation=operation,
            intended_scope=scope,
            exact_function=expression,
            threshold=0.5,
            allowed_influence={"risk": 1.0, "mitigation": 0.12 if rank == 0 else 0.30, "routing": 1.0},
            bounds={"output_min": 0.0, "output_max": 1.0, "mitigation_max": 0.12},
            invariants=(
                "approved_configuration_only",
                "hard_veto_dominance",
                "bounded_mitigation",
                "presence_not_harmfulness",
                "scope_bounded_influence",
                "complete_trace",
                "verified_rollback",
            ),
            provenance={
                "capsule_id": capsule.capsule_id,
                "trace_hash": context.trace_hash,
                "synthesis_manifest_hash": context.synthesis_manifest_hash,
                "feedback_provenance": capsule.feedback_provenance,
                "feedback_reliability": capsule.feedback_reliability,
                "attribution_rank": list(attribution.ranked_components),
            },
            parent_id=context.parent_configuration_id,
            exact_delta={"operation": operation.value, "expression": expression.to_dict(), "activation_scope": scope},
            expected_benefit={"originating_failure_reduction": round(0.9 - rank * 0.2, 6), "perception_gain": round(0.30 - rank * 0.10, 6)},
            expected_failures=("scope_leakage", "boundary_instability", "protected_regression"),
            validation_plan={
                "trigger_replay": True,
                "retained_replay": True,
                "disjoint_temporal_holdout": True,
                "boundary": True,
                "counterfactual": True,
                "independent_adversarial_search": True,
                "scope_audit": True,
                "invariant_audit": True,
                "shadow": True,
                "pareto_non_worsening": True,
                "trace_audit": True,
                "rollback_rehearsal": True,
            },
            rollback_target=context.parent_configuration_id,
            complexity=OPERATION_COMPLEXITY[operation],
        )


def _primitive_for(operation: ProposalOperation) -> str:
    return {
        ProposalOperation.RECALIBRATE: "calibration_residual",
        ProposalOperation.SCOPE_NARROW: "scope_predicate",
        ProposalOperation.SCOPE_EXPAND: "nearest_validated_support",
        ProposalOperation.SPLIT: "bounded_conjunction",
        ProposalOperation.MERGE: "bounded_weighted_combination",
        ProposalOperation.ADD: "evidence_presence",
        ProposalOperation.RETIRE: "counterfactual_stability",
        ProposalOperation.POLICY_INTERACTION: "response_routing",
        ProposalOperation.CONFIGURATION_SPECIALIZATION: "temporal_persistence",
        ProposalOperation.EVIDENCE_RECOVERY: "evidence_provenance",
    }[operation]
