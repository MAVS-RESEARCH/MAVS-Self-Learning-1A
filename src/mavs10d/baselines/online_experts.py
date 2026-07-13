"""Hedge/Exponentiated-Weights selection over approved fixed policies."""

from __future__ import annotations

import math

from mavs10d.baselines.phase1_common import Phase1Baseline, visible_risk
from mavs10d.core.types import CandidateAction, Observation


class OnlineExpertsBaseline(Phase1Baseline):
    adaptive = True

    def __init__(self, config):
        super().__init__(config)
        self.eta = float(config.params.get("eta", 0.05))
        self.expert_thresholds = tuple(float(value) for value in config.params.get("expert_thresholds", [0.40, 0.55, 0.70]))
        self.weights = [1.0] * len(self.expert_thresholds)
        self.active_expert = 0

    def reset(self, seed: int) -> None:
        super().reset(seed)
        self.weights = [1.0] * len(self.expert_thresholds)
        self.active_expert = 0

    def score(self, obs: Observation, candidate: CandidateAction) -> float:
        selected = max(range(len(self.weights)), key=lambda index: (self.weights[index], -index))
        if selected != self.active_expert:
            self.resources.configuration_switches += 1
            self.active_expert = selected
        threshold = self.expert_thresholds[selected]
        self.reject_threshold = threshold
        self.escalate_threshold = max(0.15, threshold - 0.15)
        return visible_risk(candidate)

    def on_released_feedback(self, event):
        risk = float(event["risk_score"])
        label = bool(event["observed_label"])
        for index, threshold in enumerate(self.expert_thresholds):
            accept = risk < threshold
            loss = 1.0 if (label and accept) else (0.35 if (not label and not accept) else 0.0)
            self.weights[index] *= math.exp(-self.eta * loss)
        total = sum(self.weights)
        self.weights = [value / total for value in self.weights]
        self.resources.update_operations += len(self.weights)

    def state_dict(self):
        return {**super().state_dict(), "weights": self.weights, "active_expert": self.active_expert}

    def load_state_dict(self, state):
        super().load_state_dict(state)
        self.weights = [float(value) for value in state.get("weights", self.weights)]
        self.active_expert = int(state.get("active_expert", 0))
