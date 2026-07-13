"""Component-level counterfactual responsibility assignment."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from mavs10d.governance.self_learning.meta_diagnostics import MetaDiagnosticState


ATTRIBUTABLE_COMPONENTS: tuple[str, ...] = (
    "diagnostics",
    "evidence_availability",
    "severity",
    "weights",
    "mitigation",
    "thresholds",
    "hard_veto",
    "selector",
    "scope",
)


@dataclass(frozen=True)
class AttributionResult:
    component_scores: Mapping[str, float]
    ranked_components: tuple[str, ...]
    baseline_loss: float
    counterfactual_loss: Mapping[str, float]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def attribute_failure(state: MetaDiagnosticState, *, baseline_loss: float = 1.0) -> AttributionResult:
    """Approximate removal/freeze responsibility using bounded visible meta-signals."""

    raw = {
        "diagnostics": max(state.witness_conflict, state.diagnostic_redundancy, state.counterfactual_instability),
        "evidence_availability": max(state.evidence_masking, state.evidence_unavailable),
        "severity": max(state.calibration_residual, state.policy_conflict * 0.6),
        "weights": max(state.diagnostic_redundancy, state.calibration_residual * 0.5),
        "mitigation": max(state.policy_conflict, state.witness_conflict * 0.5),
        "thresholds": max(state.calibration_residual, state.coverage_gap * 0.4),
        "hard_veto": max(state.witness_conflict, state.policy_conflict, state.scope_leakage * 0.5),
        "selector": max(state.selector_uncertainty, state.novelty * 0.5),
        "scope": max(state.scope_leakage, state.coverage_gap),
    }
    scores = {name: round(min(1.0, max(0.0, raw[name])), 6) for name in ATTRIBUTABLE_COMPONENTS}
    ranked = tuple(sorted(scores, key=lambda name: (-scores[name], ATTRIBUTABLE_COMPONENTS.index(name))))
    counterfactual = {name: round(max(0.0, baseline_loss - score), 6) for name, score in scores.items()}
    return AttributionResult(scores, ranked, baseline_loss, counterfactual)
