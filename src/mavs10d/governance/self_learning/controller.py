"""Certified fast loop and counterexample-driven slow-loop controller."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from mavs10d.core.contracts import ActiveGovernanceConfiguration, LearningEvent
from mavs10d.core.hashing import stable_hash
from mavs10d.governance.self_learning.config_library import CertifiedConfigurationLibrary
from mavs10d.governance.self_learning.diagnostic_grammar import RepairCandidate, evaluate_candidate
from mavs10d.governance.self_learning.failure_attribution import AttributionResult, attribute_failure
from mavs10d.governance.self_learning.memory import (
    AppendOnlyTraceMemory,
    FailureCapsule,
    FailureCapsuleStore,
    RetainedCounterexample,
    RetainedCounterexampleBank,
    UncertaintyEntry,
    UncertaintyLedger,
    nearest_contrasts,
)
from mavs10d.governance.self_learning.meta_diagnostics import MetaDiagnosticState, evaluate_meta_diagnostics
from mavs10d.governance.self_learning.ontology import FailureFamily, FailureOntology
from mavs10d.governance.self_learning.proposal_engine import ProposalContext, ProposalEngine
from mavs10d.governance.self_learning.selector import GovernedSelector, SelectionResult


@dataclass(frozen=True)
class FastLoopDecision:
    trace_id: str
    opportunity_id: str
    action: str
    config_id: str
    risk: float
    severity: float
    threshold: float
    safe_witness: bool
    danger_witness: bool
    query_used: bool
    selector_applicability: float
    selector_fallback: bool
    reason_codes: tuple[str, ...]
    meta_diagnostics: MetaDiagnosticState
    visible_features: Mapping[str, Any]
    prefeedback_record_hash: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["meta_diagnostics"] = self.meta_diagnostics.to_dict()
        return payload


@dataclass(frozen=True)
class FeedbackCompletion:
    trace_id: str
    expected_action: str
    observed_action: str
    terminal_error: bool
    uar_error: bool
    frr_error: bool
    capsule: FailureCapsule | None
    attribution: AttributionResult | None
    outcome_record_hash: str


class SelfLearningController:
    """Execute certified decisions and research candidates without live self-modification."""

    def __init__(
        self,
        *,
        condition: str,
        generation: int,
        base_configuration: ActiveGovernanceConfiguration,
        library: CertifiedConfigurationLibrary | None = None,
        ontology: FailureOntology | None = None,
    ) -> None:
        if condition not in {"cumulative", "fresh"}:
            raise ValueError("Phase 3 condition must be cumulative or fresh.")
        self.condition = condition
        self.generation = generation
        self.memory = AppendOnlyTraceMemory()
        self.retained = RetainedCounterexampleBank()
        self.capsules = FailureCapsuleStore()
        self.uncertainty = UncertaintyLedger()
        self.ontology = ontology or FailureOntology()
        self.library = library or CertifiedConfigurationLibrary(base_configuration)
        self.selector = GovernedSelector(self.library)
        self.proposal_engine = ProposalEngine()

    def fast_loop(self, row: Mapping[str, Any], *, contained: bool) -> FastLoopDecision:
        """Write an immutable decision trace before any outcome may be appended."""

        features = _visible_features(row)
        selection = self.selector.select(features)
        risk = float(features["risk_proxy"])
        base_action = _base_action(risk)
        query_used = False
        if selection.record.candidate is not None:
            action, query_used = evaluate_candidate(selection.record.candidate, features, base_action)
            reason = "certified_repair_rule"
        elif contained and bool(features.get("target_context", False)):
            action = "escalate"
            reason = "contained_pending_certification"
        else:
            action = base_action
            reason = "certified_base_configuration"
        nearest_support = float(features.get("nearest_validated_support", 0.80))
        meta = evaluate_meta_diagnostics(
            features,
            nearest_support=nearest_support,
            selector_applicability=selection.applicability,
            recurrence=0.0,
        )
        safe_witness = float(features.get("safe_witness", 0.0)) >= 0.65
        danger_witness = float(features.get("danger_witness", 0.0)) >= 0.65
        trace_core = {
            "condition": self.condition,
            "generation": self.generation,
            "opportunity_id": row["opportunity_id"],
            "world_id": row["world_id"],
            "curriculum_id": row["curriculum_id"],
            "curriculum_step": int(row["curriculum_step"]),
            "stage": row["stage"],
            "config_id": selection.record.config_id,
            "config_hash": selection.record.eta.config_hash,
            "action": action,
            "risk": risk,
            "severity": max(meta.novelty, meta.evidence_masking, meta.scope_leakage, meta.witness_conflict),
            "threshold": 0.5,
            "safe_witness": safe_witness,
            "danger_witness": danger_witness,
            "query_used": query_used,
            "selector_applicability": selection.applicability,
            "selector_fallback": selection.used_fallback,
            "selector_reason": selection.reason_code,
            "reason_codes": [reason, selection.reason_code],
            "meta_diagnostics": meta.to_dict(),
            "visible_features": features,
            "nuisance_hash": row["nuisance_hash"],
        }
        trace_id = f"trace-{stable_hash(trace_core)[:32]}"
        prefeedback = self.memory.append_decision({"trace_id": trace_id, **trace_core})
        return FastLoopDecision(
            trace_id=trace_id,
            opportunity_id=str(row["opportunity_id"]),
            action=action,
            config_id=selection.record.config_id,
            risk=risk,
            severity=float(trace_core["severity"]),
            threshold=0.5,
            safe_witness=safe_witness,
            danger_witness=danger_witness,
            query_used=query_used,
            selector_applicability=selection.applicability,
            selector_fallback=selection.used_fallback,
            reason_codes=(reason, selection.reason_code),
            meta_diagnostics=meta,
            visible_features=features,
            prefeedback_record_hash=prefeedback.record_hash,
        )

    def complete_released_feedback(
        self,
        decision: FastLoopDecision,
        row: Mapping[str, Any],
        *,
        released_unsafe_label: bool,
        feedback_provenance: str,
        feedback_reliability: float,
    ) -> FeedbackCompletion:
        if feedback_reliability < 0.75:
            raise ValueError("Unreliable feedback must be quarantined before reaching the slow loop.")
        expected = "reject" if released_unsafe_label else "accept"
        terminal_error = decision.action in {"accept", "reject"} and decision.action != expected
        uar = released_unsafe_label and decision.action == "accept"
        frr = not released_unsafe_label and decision.action == "reject"
        outcome = self.memory.append_outcome(
            decision.trace_id,
            {
                "released_label": "unsafe" if released_unsafe_label else "safe",
                "expected_action": expected,
                "observed_action": decision.action,
                "terminal_error": terminal_error,
                "feedback_provenance": feedback_provenance,
                "feedback_reliability": feedback_reliability,
            },
        )
        counterexample = RetainedCounterexample(
            counterexample_id=f"counterexample-{stable_hash({'trace': decision.trace_id, 'expected': expected})[:24]}",
            trace_id=decision.trace_id,
            family_id=f"family-{decision.meta_diagnostics.dominant()[0]}",
            expected_action=expected,
            observed_action=decision.action,
            visible_signature=decision.visible_features,
            protected=terminal_error,
        )
        self.retained.add(counterexample)
        capsule: FailureCapsule | None = None
        attribution: AttributionResult | None = None
        if terminal_error or decision.action == "escalate":
            attribution = attribute_failure(decision.meta_diagnostics)
            family_id = counterexample.family_id
            capsule_core = {
                "trace_id": decision.trace_id,
                "family_id": family_id,
                "curriculum_id": row["curriculum_id"],
                "trigger": "confirmed_terminal_error" if terminal_error else "resolved_escalation",
            }
            capsule = FailureCapsule(
                capsule_id=f"capsule-{stable_hash(capsule_core)[:24]}",
                curriculum_id=str(row["curriculum_id"]),
                family_id=family_id,
                trigger=str(capsule_core["trigger"]),
                trace_ids=(decision.trace_id,),
                context={"generation": self.generation, "domain": row["domain"], "stage": row["stage"]},
                observable_signature=decision.visible_features,
                expected_action=expected,
                observed_action=decision.action,
                severity=decision.severity,
                feedback_provenance=feedback_provenance,
                feedback_reliability=feedback_reliability,
                minimal_contrasts=nearest_contrasts(
                    decision.visible_features,
                    self.retained.contrast_candidates(decision.visible_features),
                ),
                attribution=attribution.component_scores,
            )
            self.capsules.add(capsule)
            if family_id not in {item.family_id for item in self.ontology.all()}:
                self.ontology.add(
                    FailureFamily(
                        family_id=family_id,
                        semantic_definition=f"Provisional visible failure family dominated by {decision.meta_diagnostics.dominant()[0]}",
                        context_predicates={"domain": row["domain"], "curriculum_id": row["curriculum_id"]},
                        observable_signature={decision.meta_diagnostics.dominant()[0]: decision.meta_diagnostics.dominant()[1]},
                        causal_hypotheses=(attribution.ranked_components[0], attribution.ranked_components[1]),
                        severity_scale={"observed": decision.severity},
                        permissible_responses=("escalate", "investigate", "propose_bounded_candidate"),
                        known_confounders=("feedback_delay", "evidence_reliability", "scope_collision"),
                        confidence=0.60,
                        status="provisional",
                        parent_ids=(),
                        projections=(str(row["domain"]),),
                        version=1,
                    ),
                    "counterexample_trigger",
                )
        if decision.action == "escalate":
            dominant, score = decision.meta_diagnostics.dominant()
            self.uncertainty.append(
                UncertaintyEntry(
                    entry_id=f"uncertainty-{stable_hash({'trace': decision.trace_id, 'reason': dominant})[:24]}",
                    curriculum_id=str(row["curriculum_id"]),
                    trace_ids=(decision.trace_id,),
                    reason_codes=(dominant, "epistemic_buffer"),
                    missing_evidence=("certified_distinction",),
                    novelty_score=score,
                    selector_applicability=decision.selector_applicability,
                    status="contained",
                )
            )
        return FeedbackCompletion(decision.trace_id, expected, decision.action, terminal_error, uar, frr, capsule, attribution, outcome.record_hash)

    def slow_loop_proposals(
        self,
        *,
        curriculum_id: str,
        domain: str,
        parent_configuration_id: str,
        synthesis_manifest_hash: str,
    ) -> tuple[LearningEvent, tuple[RepairCandidate, ...]]:
        capsules = self.capsules.by_curriculum(curriculum_id)
        if not capsules:
            raise ValueError("Slow loop requires a released failure or resolved-escalation capsule.")
        capsule = capsules[-1]
        meta = evaluate_meta_diagnostics(
            capsule.observable_signature,
            nearest_support=float(capsule.observable_signature.get("nearest_validated_support", 0.80)),
            selector_applicability=0.0,
            recurrence=0.0,
        )
        attribution = attribute_failure(meta)
        event = LearningEvent(
            event_id=f"learning-{stable_hash({'capsule': capsule.capsule_id, 'generation': self.generation})[:24]}",
            trigger=capsule.trigger,
            trace_ids=capsule.trace_ids,
            attributed_mechanism=attribution.ranked_components[0],
            candidate_operations=tuple(operation.value for operation in _ordered_operations(meta)),
            evidence_sufficient=True,
            feedback_provenance=capsule.feedback_provenance,
            feedback_reliability=capsule.feedback_reliability,
        )
        self.memory.append_learning("learning_event", asdict(event))
        proposals = self.proposal_engine.propose(
            capsule,
            meta,
            attribution,
            ProposalContext(
                generation=self.generation,
                curriculum_id=curriculum_id,
                domain=domain,
                parent_configuration_id=parent_configuration_id,
                trace_hash=self.memory.head_hash,
                synthesis_manifest_hash=synthesis_manifest_hash,
            ),
        )
        for candidate in proposals:
            self.memory.append_learning("proposal", candidate.to_dict())
        return event, proposals


def _ordered_operations(meta: MetaDiagnosticState) -> tuple[Any, ...]:
    from mavs10d.governance.self_learning.proposal_engine import SIGNAL_TO_OPERATION, OPERATION_COMPLEXITY

    return tuple(
        SIGNAL_TO_OPERATION[name]
        for name in sorted(SIGNAL_TO_OPERATION, key=lambda name: (OPERATION_COMPLEXITY[SIGNAL_TO_OPERATION[name]], -meta.to_dict()[name], name))
    )


def _visible_features(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("visible_features_json", {})
    if isinstance(raw, str):
        return dict(json.loads(raw))
    return dict(raw)


def _base_action(risk: float) -> str:
    if risk < 0.45:
        return "accept"
    if risk > 0.65:
        return "reject"
    return "escalate"
