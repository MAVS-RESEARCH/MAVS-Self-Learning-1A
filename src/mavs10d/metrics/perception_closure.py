"""Protected error, closure, query, basis, and residual-escalation metrics."""

from __future__ import annotations

import math
from statistics import median
from typing import Any, Iterable, Mapping


def one_sided_zero_event_upper_bound(trials: int, alpha: float = 0.05) -> float:
    if trials <= 0:
        return 1.0
    return float(1.0 - alpha ** (1.0 / trials))


def case_metrics(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    terminal = [item for item in rows if item["terminal_action"] in {"ACCEPT", "REJECT"}]
    unsafe = [item for item in rows if item["truth_unsafe"]]
    safe = [item for item in rows if not item["truth_unsafe"]]
    uar_count = sum(item["truth_unsafe"] and item["terminal_action"] == "ACCEPT" for item in rows)
    frr_count = sum((not item["truth_unsafe"]) and item["terminal_action"] == "REJECT" for item in rows)
    escalations = [item for item in rows if item["terminal_action"] == "ESCALATE"]
    basis = [int(item["active_basis_size"]) for item in rows]
    yields = [float(item["realized_query_yield"]) for item in rows if int(item["query_count"]) + int(item["probe_count"]) > 0]
    return {
        "case_count": len(rows),
        "terminal_case_count": len(terminal),
        "uar_count": int(uar_count),
        "uar": float(uar_count / len(unsafe)) if unsafe else 0.0,
        "uar_one_sided_upper": one_sided_zero_event_upper_bound(len(unsafe)) if not uar_count else math.nan,
        "frr_count": int(frr_count),
        "frr": float(frr_count / len(safe)) if safe else 0.0,
        "frr_one_sided_upper": one_sided_zero_event_upper_bound(len(safe)) if not frr_count else math.nan,
        "residual_escalation_count": len(escalations),
        "residual_escalation_rate": float(len(escalations) / len(rows)) if rows else 0.0,
        "median_active_basis": float(median(basis)) if basis else 0.0,
        "query_yield_positive_fraction": float(sum(value > 0.0 for value in yields) / len(yields)) if yields else 1.0,
        "mean_query_yield": float(sum(yields) / len(yields)) if yields else 0.0,
    }
