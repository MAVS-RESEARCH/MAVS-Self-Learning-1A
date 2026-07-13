"""Entropy and confidence-filtered pseudo-label CTTA benchmark adaptations."""

from __future__ import annotations

from mavs10d.baselines.phase1_common import Phase1Baseline, visible_risk
from mavs10d.core.types import CandidateAction, Observation


class CTTABaseline(Phase1Baseline):
    adaptive = True

    def __init__(self, config):
        super().__init__(config)
        self.mode = str(config.params.get("mode", "entropy"))
        self.learning_rate = float(config.params.get("learning_rate", 0.0001))
        self.confidence_floor = float(config.params.get("confidence_floor", 0.90))
        self.update_frequency = int(config.params.get("update_frequency", 8))
        self.bias = 0.0
        self.steps = 0

    def reset(self, seed: int) -> None:
        super().reset(seed)
        self.bias = 0.0
        self.steps = 0

    def score(self, obs: Observation, candidate: CandidateAction) -> float:
        self.steps += 1
        source_risk = float(candidate.provenance.get("model_risk", visible_risk(candidate)))
        score = min(1.0, max(0.0, source_risk + self.bias))
        if self.steps % self.update_frequency == 0:
            confidence = max(score, 1.0 - score)
            if self.mode == "entropy" or confidence >= self.confidence_floor:
                pseudo = 1.0 if score >= 0.5 else 0.0
                gradient = score - pseudo
                self.bias = min(0.20, max(-0.20, self.bias - self.learning_rate * gradient))
                self.resources.update_operations += 1
        return score

    def on_released_feedback(self, event):
        if self.mode != "pseudo_label":
            return
        score = float(event["risk_score"])
        label = float(bool(event["observed_label"]))
        self.bias = min(0.20, max(-0.20, self.bias - self.learning_rate * (score - label)))
        self.resources.update_operations += 1

    def state_dict(self):
        return {**super().state_dict(), "bias": self.bias, "steps": self.steps}

    def load_state_dict(self, state):
        super().load_state_dict(state)
        self.bias = float(state.get("bias", 0.0))
        self.steps = int(state.get("steps", 0))
