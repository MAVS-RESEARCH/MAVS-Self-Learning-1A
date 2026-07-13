from __future__ import annotations

from mavs10d.baselines.common import clamp, governance_decision
from mavs10d.core.config import MethodConfig
from mavs10d.core.trace_logging import console_log
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult


class ConfidenceGateBaseline:
    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        self.reject_below = float(config.params.get("reject_below", 0.35))
        self.escalate_below = float(config.params.get("escalate_below", 0.55))

    def reset(self, seed: int) -> None:
        self._seed = int(seed)

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        # console.log: phase3.confidence_gate.decide.start
        console_log(
            "phase3.confidence_gate.decide.start",
            method_id=self.method_id,
            episode_id=obs.episode_id,
            t=obs.t,
            confidence=candidate.confidence,
        )
        confidence = clamp(candidate.confidence)
        if confidence < self.reject_below:
            decision = "reject"
            threshold = self.reject_below
            triggered = ["confidence_reject_gate"]
            escalation_reason = None
        elif confidence < self.escalate_below:
            decision = "escalate"
            threshold = self.escalate_below
            triggered = ["confidence_escalation_gate"]
            escalation_reason = "confidence below escalation threshold"
        else:
            decision = "accept"
            threshold = self.escalate_below
            triggered = []
            escalation_reason = None
        risk = clamp(1.0 - confidence)
        # console.log: phase3.confidence_gate.decide.complete
        console_log(
            "phase3.confidence_gate.decide.complete",
            method_id=self.method_id,
            t=obs.t,
            decision=decision,
            risk_score=risk,
        )
        return governance_decision(
            baseline_name="confidence_gate",
            obs=obs,
            candidate=candidate,
            decision=decision,
            risk_score=risk,
            severity=risk,
            threshold=threshold,
            rationale="confidence threshold gate",
            triggered_checks=triggered,
            details={
                "confidence": confidence,
                "reject_below": self.reject_below,
                "escalate_below": self.escalate_below,
                "escalation_reason": escalation_reason,
            },
        )

    def update(
        self,
        obs: Observation,
        candidate: CandidateAction,
        decision: GovernanceDecision,
        result: StepResult,
    ) -> None:
        return None

