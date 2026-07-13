"""Intervention and resource-burden metric identities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class BurdenObservation:
    escalated: bool
    intervention_count: int
    latency_ms: float
    calls: int
    tokens: int
    update_compute_ms: float
    retained_bytes: int


def burden_metrics(rows: Iterable[BurdenObservation]) -> dict[str, float]:
    values = tuple(rows)
    n = len(values)
    if n == 0:
        return {key: 0.0 for key in _METRIC_KEYS}
    return {
        "escalation_rate": sum(item.escalated for item in values) / n,
        "interventions_per_decision": sum(item.intervention_count for item in values) / n,
        "latency_ms_per_decision": sum(item.latency_ms for item in values) / n,
        "calls_per_decision": sum(item.calls for item in values) / n,
        "tokens_per_decision": sum(item.tokens for item in values) / n,
        "update_compute_ms_per_decision": sum(item.update_compute_ms for item in values) / n,
        "retained_bytes_max": float(max(item.retained_bytes for item in values)),
    }


_METRIC_KEYS = (
    "escalation_rate",
    "interventions_per_decision",
    "latency_ms_per_decision",
    "calls_per_decision",
    "tokens_per_decision",
    "update_compute_ms_per_decision",
    "retained_bytes_max",
)
