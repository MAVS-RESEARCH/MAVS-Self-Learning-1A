"""Fixed visible-information comparators for the Phase 2 DS-CF gauntlet."""

from __future__ import annotations

from mavs10d.baselines.common import clamp, governance_decision
from mavs10d.core.config import MethodConfig
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult
from mavs10d.governance.ds_cf import DSCFGovernance
from mavs10d.governance.phase2_diagnostics import compute_phase2_diagnostics


class VisibleRiskThreshold:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        self.reject_threshold = float(config.params.get("reject_threshold", 0.72))
        self.escalate_threshold = float(config.params.get("escalate_threshold", 0.52))

    def reset(self, seed: int) -> None:
        return None

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        risk = clamp(float(candidate.provenance["risk_proxy"]))
        decision = "reject" if risk >= self.reject_threshold else ("escalate" if risk >= self.escalate_threshold else "accept")
        return governance_decision(
            "visible_risk_threshold", obs, candidate, decision, risk, risk,
            self.reject_threshold if decision == "reject" else self.escalate_threshold,
            "Fixed threshold over the visible risk proxy", [] if decision == "accept" else [f"visible_risk_{decision}"],
            {"information_budget": "visible risk proxy only", "escalation_reason": "visible risk band" if decision == "escalate" else None},
        )

    def update(self, obs: Observation, candidate: CandidateAction, decision: GovernanceDecision, result: StepResult) -> None:
        return None


class ProvenanceSelective:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id

    def reset(self, seed: int) -> None:
        return None

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        diagnostics = compute_phase2_diagnostics(obs, candidate)
        risk = clamp(float(candidate.provenance["risk_proxy"]))
        uncertain = diagnostics.evidence_status in {"masked", "unavailable"} or diagnostics.provenance_concentration >= 0.75 or diagnostics.source_compromise >= 0.50
        if uncertain:
            decision, reasons = "escalate", ["provenance_or_availability_uncertainty"]
        elif diagnostics.danger_witness and risk >= 0.72:
            decision, reasons = "reject", ["visible_danger_and_risk"]
        elif diagnostics.safe_witness and risk < 0.52:
            decision, reasons = "accept", []
        else:
            decision, reasons = "escalate", ["insufficient_selective_coverage"]
        return governance_decision(
            "provenance_selective", obs, candidate, decision, risk, max(risk, diagnostics.source_compromise), 0.72,
            "Selective comparator using visible provenance and evidence availability", reasons,
            {"diagnostics": diagnostics.to_dict(), "escalation_reason": reasons[0] if decision == "escalate" else None},
        )

    def update(self, obs: Observation, candidate: CandidateAction, decision: GovernanceDecision, result: StepResult) -> None:
        return None


def build_phase2_method(method_name: str):
    config = MethodConfig(method_name, method_name, {})
    if method_name == "ds_cf":
        return DSCFGovernance(config)
    if method_name == "visible_risk_threshold":
        return VisibleRiskThreshold(config)
    if method_name == "provenance_selective":
        return ProvenanceSelective(config)
    raise KeyError(f"Unknown Phase 2 method: {method_name}")


PHASE2_METHODS: tuple[str, ...] = ("ds_cf", "visible_risk_threshold", "provenance_selective")
