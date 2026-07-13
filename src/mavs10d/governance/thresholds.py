from __future__ import annotations

from dataclasses import dataclass

from mavs10d.baselines.common import clamp
from mavs10d.core.trace_logging import console_log


@dataclass(frozen=True)
class ThresholdResult:
    base_threshold: float
    threshold_delta: float
    final_threshold: float
    mitigation_relaxation: float
    hard_veto_applied: bool


def compute_threshold(
    *,
    base_threshold: float,
    severity: float,
    mitigation_strength: float,
    hard_veto: bool,
    severity_sensitivity: float = 0.25,
    max_mitigation_relaxation: float = 0.10,
    lower_bound: float = 0.05,
    upper_bound: float = 0.95,
) -> ThresholdResult:
    # console.log: phase4.thresholds.compute.start
    console_log(
        "phase4.thresholds.compute.start",
        base_threshold=base_threshold,
        severity=severity,
        mitigation_strength=mitigation_strength,
        hard_veto=hard_veto,
    )
    bounded_mitigation = 0.0 if hard_veto else min(clamp(mitigation_strength), max_mitigation_relaxation)
    strictness_delta = -abs(severity_sensitivity) * clamp(severity)
    threshold_delta = strictness_delta + bounded_mitigation
    final_threshold = clamp(base_threshold + threshold_delta, lower_bound, upper_bound)
    result = ThresholdResult(
        base_threshold=base_threshold,
        threshold_delta=final_threshold - base_threshold,
        final_threshold=final_threshold,
        mitigation_relaxation=bounded_mitigation,
        hard_veto_applied=hard_veto,
    )
    # console.log: phase4.thresholds.compute.complete
    console_log(
        "phase4.thresholds.compute.complete",
        final_threshold=result.final_threshold,
        threshold_delta=result.threshold_delta,
        mitigation_relaxation=result.mitigation_relaxation,
    )
    return result

