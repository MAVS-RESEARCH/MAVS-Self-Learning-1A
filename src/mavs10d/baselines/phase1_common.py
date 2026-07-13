"""Shared GovernanceMethod implementation utilities for Phase 1 baselines."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from mavs10d.baselines.common import clamp, governance_decision
from mavs10d.core.config import MethodConfig
from mavs10d.core.types import CandidateAction, GovernanceDecision, Observation, StepResult


@dataclass
class ResourceAccount:
    calibration_examples: int = 0
    calls: int = 0
    tokens: int = 0
    latency_ms: float = 0.0
    wall_time_ms: float = 0.0
    update_operations: int = 0
    configuration_switches: int = 0

    def to_dict(self, memory_bytes: int) -> dict[str, int | float]:
        return {
            "calibration_examples": self.calibration_examples,
            "calls": self.calls,
            "tokens": self.tokens,
            "latency_ms": self.latency_ms,
            "wall_time_ms": self.wall_time_ms,
            "memory_bytes": memory_bytes,
            "update_operations": self.update_operations,
            "configuration_switches": self.configuration_switches,
        }


class Phase1Baseline:
    """Base class structurally satisfying the inherited GovernanceMethod protocol."""

    adaptive = False

    def __init__(self, config: MethodConfig):
        self.config = config
        self.method_id = config.id
        self.reject_threshold = float(config.params.get("reject_threshold", 0.65))
        self.escalate_threshold = float(config.params.get("escalate_threshold", 0.45))
        self.initial_reject_threshold = self.reject_threshold
        self.initial_escalate_threshold = self.escalate_threshold
        self.calibration_size = int(config.params.get("calibration_size", 0))
        self.latency_per_call_ms = float(config.params.get("latency_ms", 1.0))
        self.memory_budget_bytes = int(config.params.get("memory_bytes", 1_048_576))
        self.feedback_history: deque[dict[str, Any]] = deque(maxlen=int(config.params.get("window", 128)))
        self.resources = ResourceAccount(calibration_examples=self.calibration_size)
        self._seed = 0

    def reset(self, seed: int) -> None:
        self._seed = int(seed)
        self.reject_threshold = self.initial_reject_threshold
        self.escalate_threshold = self.initial_escalate_threshold
        self.feedback_history.clear()
        self.resources = ResourceAccount(calibration_examples=self.calibration_size)

    def decide(self, obs: Observation, candidate: CandidateAction) -> GovernanceDecision:
        score = self.score(obs, candidate)
        decision, threshold = self.action(score)
        self.resources.calls += 1
        self.resources.latency_ms += self.latency_per_call_ms
        self.resources.wall_time_ms += self.latency_per_call_ms
        return governance_decision(
            baseline_name=self.config.type,
            obs=obs,
            candidate=candidate,
            decision=decision,
            risk_score=score,
            severity=score,
            threshold=threshold,
            rationale=f"Phase 1 {self.config.type} fixed-representation governance rule",
            triggered_checks=[] if decision == "accept" else [f"{self.config.type}_{decision}"],
            details={
                "approved_configuration": True,
                "information_budget": "visible observation and released feedback only",
                "reject_threshold": self.reject_threshold,
                "escalate_threshold": self.escalate_threshold,
                "resource_account": self.resources.to_dict(self.memory_bytes()),
                "escalation_reason": "score in escalation band" if decision == "escalate" else None,
            },
        )

    def update(
        self,
        obs: Observation,
        candidate: CandidateAction,
        decision: GovernanceDecision,
        result: StepResult,
    ) -> None:
        for event in result.info.get("released_feedback", []):
            if int(event["release_step"]) > obs.t:
                raise RuntimeError("A baseline received feedback before its release step.")
            self.feedback_history.append(dict(event))
            self.on_released_feedback(dict(event))

    def score(self, obs: Observation, candidate: CandidateAction) -> float:
        return clamp(float(candidate.provenance["risk_proxy"]))

    def action(self, score: float) -> tuple[str, float]:
        if score >= self.reject_threshold:
            return "reject", self.reject_threshold
        if score >= self.escalate_threshold:
            return "escalate", self.escalate_threshold
        return "accept", self.escalate_threshold

    def on_released_feedback(self, event: dict[str, Any]) -> None:
        return None

    def memory_bytes(self) -> int:
        return min(self.memory_budget_bytes, 256 + len(self.feedback_history) * 96)

    def state_dict(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "type": self.config.type,
            "adaptive": self.adaptive,
            "reject_threshold": self.reject_threshold,
            "escalate_threshold": self.escalate_threshold,
            "feedback_history": list(self.feedback_history),
            "resources": self.resources.to_dict(self.memory_bytes()),
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        if not self.adaptive:
            raise ValueError("Fixed baselines cannot load learned state.")
        if state.get("type") != self.config.type:
            raise ValueError("Baseline state type mismatch.")
        self.reject_threshold = float(state["reject_threshold"])
        self.escalate_threshold = float(state["escalate_threshold"])
        self.feedback_history.extend(dict(item) for item in state.get("feedback_history", []))


def visible_risk(candidate: CandidateAction) -> float:
    return clamp(float(candidate.provenance["risk_proxy"]))
