"""Risk-constrained Neyman-Pearson and cost-sensitive Phase 1 rules."""

from __future__ import annotations

from mavs10d.baselines.phase1_common import Phase1Baseline, visible_risk
from mavs10d.core.types import CandidateAction, Observation


class NeymanPearsonBaseline(Phase1Baseline):
    def score(self, obs: Observation, candidate: CandidateAction) -> float:
        risk = visible_risk(candidate)
        mode = str(self.config.params.get("mode", "risk_constrained"))
        if mode == "risk_constrained":
            odds = risk / max(1e-9, 1.0 - risk)
            ratio = float(self.config.params.get("likelihood_ratio", 2.0))
            return min(1.0, odds / ratio)
        if mode == "cost_sensitive":
            preference = str(obs.risk_context["cost_preference"])
            unsafe_cost = {"safety_first": 1.0, "balanced": 0.75, "low_intervention": 0.55}[preference]
            intervention_cost = {"safety_first": 0.15, "balanced": 0.30, "low_intervention": 0.45}[preference]
            return min(1.0, risk * unsafe_cost / max(0.05, intervention_cost))
        raise ValueError(f"Unsupported Neyman-Pearson mode: {mode}")
