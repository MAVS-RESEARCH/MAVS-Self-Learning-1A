"""Visible-only meta-diagnostics for ontology incompleteness and governance instability."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class MetaDiagnosticState:
    novelty: float
    coverage_gap: float
    scope_leakage: float
    evidence_masking: float
    witness_conflict: float
    counterfactual_instability: float
    selector_uncertainty: float
    diagnostic_redundancy: float
    calibration_residual: float
    policy_conflict: float
    evidence_unavailable: float
    recurrence: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    def dominant(self) -> tuple[str, float]:
        values = self.to_dict()
        values.pop("recurrence", None)
        return max(values.items(), key=lambda item: (item[1], item[0]))


def evaluate_meta_diagnostics(
    visible_features: Mapping[str, Any],
    *,
    nearest_support: float,
    selector_applicability: float,
    recurrence: float,
) -> MetaDiagnosticState:
    """Compute bounded meta-diagnostics without outcome or evaluator state."""

    get = lambda name: _unit(float(visible_features.get(name, 0.0)))
    safe = _unit(float(visible_features.get("safe_witness", 0.0)))
    danger = _unit(float(visible_features.get("danger_witness", 0.0)))
    availability = bool(visible_features.get("evidence_available", True))
    explicit_conflict = min(safe, danger) * 2.0
    bounded_applicability = _unit(selector_applicability)
    selector_boundary_uncertainty = 2.0 * min(bounded_applicability, 1.0 - bounded_applicability)
    return MetaDiagnosticState(
        novelty=_unit(max(1.0 - nearest_support, get("coverage_gap"))),
        coverage_gap=get("coverage_gap"),
        scope_leakage=get("scope_leakage"),
        evidence_masking=max(get("evidence_masking"), 1.0 if not availability else 0.0),
        witness_conflict=_unit(max(get("witness_conflict"), explicit_conflict)),
        counterfactual_instability=get("counterfactual_instability"),
        selector_uncertainty=_unit(max(get("selector_uncertainty"), selector_boundary_uncertainty)),
        diagnostic_redundancy=get("diagnostic_redundancy"),
        calibration_residual=get("calibration_residual"),
        policy_conflict=get("policy_conflict"),
        evidence_unavailable=max(get("evidence_unavailable"), 1.0 if not availability else 0.0),
        recurrence=_unit(recurrence),
    )


def trigger_reasons(
    state: MetaDiagnosticState,
    *,
    confirmed_error: bool,
    recurring_escalations: int,
    significant_regression: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if confirmed_error:
        reasons.append("confirmed_error")
    if recurring_escalations >= 5:
        reasons.append("recurring_escalation")
    if state.novelty >= 0.70:
        reasons.append("unexplained_novelty")
    if state.scope_leakage >= 0.65:
        reasons.append("scope_leakage")
    if state.counterfactual_instability >= 0.65:
        reasons.append("instability")
    if significant_regression:
        reasons.append("significant_regression")
    return tuple(dict.fromkeys(reasons))


def _unit(value: float) -> float:
    return min(1.0, max(0.0, value))
