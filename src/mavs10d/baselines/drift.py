"""ADWIN-style and Page-Hinkley drift-triggered configuration selectors."""

from __future__ import annotations

import math

from mavs10d.baselines.phase1_common import Phase1Baseline


class DriftBaseline(Phase1Baseline):
    adaptive = True

    def __init__(self, config):
        super().__init__(config)
        self.mode = str(config.params.get("mode", "adwin"))
        self.delta = float(config.params.get("delta", 0.025))
        self.running_mean = 0.0
        self.cumulative_deviation = 0.0
        self.minimum_deviation = 0.0
        self.feedback_count = 0

    def reset(self, seed: int) -> None:
        super().reset(seed)
        self.running_mean = 0.0
        self.cumulative_deviation = 0.0
        self.minimum_deviation = 0.0
        self.feedback_count = 0

    def on_released_feedback(self, event):
        error = abs(float(event["risk_score"]) - float(bool(event["observed_label"])))
        self.feedback_count += 1
        previous = self.running_mean
        self.running_mean += (error - self.running_mean) / self.feedback_count
        drift = False
        if self.mode == "adwin" and self.feedback_count >= 16:
            recent = list(self.feedback_history)
            selected_cut = None
            for cut in range(8, len(recent) - 7):
                first_values = [abs(float(x["risk_score"]) - float(bool(x["observed_label"]))) for x in recent[:cut]]
                second_values = [abs(float(x["risk_score"]) - float(bool(x["observed_label"]))) for x in recent[cut:]]
                first = sum(first_values) / len(first_values)
                second = sum(second_values) / len(second_values)
                harmonic = 1.0 / (1.0 / len(first_values) + 1.0 / len(second_values))
                bound = math.sqrt(math.log(4.0 / self.delta) / (2.0 * harmonic))
                if abs(second - first) > bound:
                    selected_cut = cut
                    break
            drift = selected_cut is not None
            if selected_cut is not None:
                for _ in range(selected_cut):
                    self.feedback_history.popleft()
        elif self.mode == "page_hinkley":
            self.cumulative_deviation += error - previous - self.delta
            self.minimum_deviation = min(self.minimum_deviation, self.cumulative_deviation)
            drift = self.cumulative_deviation - self.minimum_deviation > 0.35
        if drift:
            old = self.reject_threshold
            self.reject_threshold = min(0.90, self.reject_threshold + 0.08)
            self.escalate_threshold = min(self.reject_threshold - 0.05, self.escalate_threshold + 0.06)
            self.resources.configuration_switches += int(old != self.reject_threshold)
            self.resources.update_operations += 1
            self.cumulative_deviation = 0.0
            self.minimum_deviation = 0.0

    def state_dict(self):
        return {**super().state_dict(), "running_mean": self.running_mean, "cumulative_deviation": self.cumulative_deviation, "minimum_deviation": self.minimum_deviation, "feedback_count": self.feedback_count}

    def load_state_dict(self, state):
        super().load_state_dict(state)
        self.running_mean = float(state.get("running_mean", 0.0))
        self.cumulative_deviation = float(state.get("cumulative_deviation", 0.0))
        self.minimum_deviation = float(state.get("minimum_deviation", 0.0))
        self.feedback_count = int(state.get("feedback_count", 0))
