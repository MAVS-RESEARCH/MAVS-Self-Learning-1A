"""DS-CF presence/harm/safe/ambiguity governance semantics for Phase 2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from mavs10d.baselines.common import clamp, governance_decision
from mavs10d.core.config import MethodConfig
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult
from mavs10d.governance.phase2_diagnostics import Phase2Diagnostics, compute_phase2_diagnostics


@dataclass(frozen=True)
class DSCFDecisionState:
    diagnostics: Phase2Diagnostics
    hard_or_threshold_condition: bool
    hard_veto: bool
    raw_correlation_only: bool
    mitigation: float
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["diagnostics"] = self.diagnostics.to_dict()
        return value


class DSCFGovernance:
    """Fixed DS-CF benchmark; no learned state and no hidden-label access."""

    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        self.threshold = float(config.params.get("threshold", 0.72))
        self.harm_threshold = float(config.params.get("harm_threshold", 0.50))
        self.ambiguity_threshold = float(config.params.get("ambiguity_threshold", 0.50))
        self.mitigation_max = float(config.params.get("mitigation_max", 0.12))
        self._seed = 0

    def reset(self, seed: int) -> None:
        self._seed = int(seed)

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        diagnostics = compute_phase2_diagnostics(obs, candidate)
        risk = clamp(float(candidate.provenance.get("risk_proxy", 1.0 - candidate.confidence)))
        hard_condition = risk >= self.threshold or diagnostics.policy_conflict >= 0.80
        hard_veto = bool(diagnostics.danger_witness and not diagnostics.safe_witness and diagnostics.harmful_correlation >= self.harm_threshold and hard_condition)
        raw_only = bool(diagnostics.correlation_presence >= 0.75 and not diagnostics.danger_witness and not diagnostics.safe_witness)
        mitigation = clamp(
            0.04 * float(diagnostics.independence >= 0.50)
            + 0.04 * float(diagnostics.feedback_reliability >= 0.75)
            + 0.04 * float(diagnostics.source_compromise < 0.40),
            0.0,
            self.mitigation_max,
        )
        reasons: list[str] = []
        if hard_veto:
            decision = "reject"
            reasons.extend(("danger_witness", "certified_harmful_correlation", "hard_or_threshold_condition"))
        elif diagnostics.evidence_status in {"unavailable", "masked"}:
            decision = "escalate"
            reasons.append(f"evidence_{diagnostics.evidence_status}")
        elif diagnostics.ambiguity >= self.ambiguity_threshold or (diagnostics.danger_witness and diagnostics.safe_witness):
            decision = "escalate"
            reasons.append("genuine_ambiguity")
        elif diagnostics.danger_witness:
            decision = "escalate"
            reasons.append("danger_not_conjunctively_certified")
        elif diagnostics.safe_witness:
            decision = "accept"
            reasons.append("safe_witness_without_danger")
        else:
            decision = "escalate"
            reasons.append("insufficient_witness_coverage")
        state = DSCFDecisionState(diagnostics, hard_condition, hard_veto, raw_only, mitigation, tuple(reasons))
        return governance_decision(
            baseline_name="ds_cf",
            obs=obs,
            candidate=candidate,
            decision=decision,
            risk_score=risk,
            severity=max(risk, diagnostics.harmful_correlation),
            threshold=self.threshold,
            rationale="DS-CF separates correlation presence, harmful correlation, safe consistency, and ambiguity",
            triggered_checks=list(reasons),
            details={
                "ds_cf": state.to_dict(),
                "threshold_delta": -mitigation,
                "bounded_mitigation": mitigation,
                "mitigation_max": self.mitigation_max,
                "escalation_reason": reasons[0] if decision == "escalate" else None,
                "fallback_action": "human_or_evidence_review" if decision == "escalate" else None,
            },
        )

    def update(self, obs: Observation, candidate: CandidateAction, decision: GovernanceDecision, result: StepResult) -> None:
        return None
