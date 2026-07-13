from __future__ import annotations

from dataclasses import dataclass

from mavs10d.baselines.common import clamp
from mavs10d.core.trace_logging import console_log


DEFAULT_SEVERITY_WEIGHTS: dict[str, float] = {
    "disagreement": 0.08,
    "evidence_missingness": 0.12,
    "policy_conflict": 0.22,
    "corruption_signal": 0.12,
    "provenance_concentration": 0.08,
    "shared_source_suspicion": 0.14,
    "confidence_inflation": 0.10,
    "specialist_collapse_indicator": 0.14,
}


@dataclass(frozen=True)
class SeverityResult:
    raw_severity: float
    normalized_severity: float
    contribution_breakdown: dict[str, float]


def aggregate_severity(
    diagnostics: dict[str, float],
    weights: dict[str, float] | None = None,
) -> SeverityResult:
    # console.log: phase4.severity.aggregate.start
    console_log("phase4.severity.aggregate.start", diagnostics=diagnostics)
    active_weights = dict(DEFAULT_SEVERITY_WEIGHTS)
    if weights:
        active_weights.update({key: max(0.0, float(value)) for key, value in weights.items()})
    weighted_terms = {
        key: clamp(float(diagnostics.get(key, 0.0))) * weight
        for key, weight in active_weights.items()
    }
    total_weight = sum(active_weights.values()) or 1.0
    raw = sum(weighted_terms.values()) / total_weight
    normalized = clamp(
        max(
            raw,
            float(diagnostics.get("policy_conflict", 0.0)) * 0.80,
            float(diagnostics.get("specialist_collapse_indicator", 0.0)) * 0.70,
        )
    )
    result = SeverityResult(
        raw_severity=clamp(raw),
        normalized_severity=normalized,
        contribution_breakdown=weighted_terms,
    )
    # console.log: phase4.severity.aggregate.complete
    console_log(
        "phase4.severity.aggregate.complete",
        raw_severity=result.raw_severity,
        normalized_severity=result.normalized_severity,
    )
    return result

