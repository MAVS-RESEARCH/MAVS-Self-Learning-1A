"""Exact non-dominance and hypervolume utilities for governance frontiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class FrontierPoint:
    method_id: str
    uar: float
    frr: float
    escalation: float
    compute: float


def pareto_frontier(points: Iterable[FrontierPoint]) -> tuple[FrontierPoint, ...]:
    values = tuple(points)
    frontier = [
        point
        for point in values
        if not any(_dominates(other, point) for other in values if other is not point)
    ]
    return tuple(sorted(frontier, key=lambda item: (item.uar, item.frr, item.escalation, item.compute, item.method_id)))


def _dominates(left: FrontierPoint, right: FrontierPoint) -> bool:
    left_values = (left.uar, left.frr, left.escalation, left.compute)
    right_values = (right.uar, right.frr, right.escalation, right.compute)
    return all(a <= b for a, b in zip(left_values, right_values)) and any(
        a < b for a, b in zip(left_values, right_values)
    )


def hypervolume(points: Iterable[FrontierPoint], reference: Sequence[float] = (1.0, 1.0, 1.0, 1.0)) -> float:
    """Exact axis-aligned minimization hypervolume after clipping to the reference point."""

    ref = tuple(float(value) for value in reference)
    vectors = {
        tuple(float(value) for value in (point.uar, point.frr, point.escalation, point.compute))
        for point in pareto_frontier(points)
        if all(float(value) <= bound for value, bound in zip((point.uar, point.frr, point.escalation, point.compute), ref))
    }
    return float(_hypervolume_recursive(tuple(vectors), ref))


def additive_epsilon(left: Iterable[FrontierPoint], right: Iterable[FrontierPoint]) -> float:
    """Return the additive epsilon by which the left minimization set covers the right set."""

    a = [_vector(point) for point in left]
    b = [_vector(point) for point in right]
    if not a or not b:
        raise ValueError("Both frontiers must contain at least one point.")
    return max(min(max(av - bv for av, bv in zip(candidate, target)) for candidate in a) for target in b)


def matched_rate_advantages(
    treatment: Iterable[FrontierPoint],
    baseline: Iterable[FrontierPoint],
    *,
    frr_tolerance: float,
    uar_tolerance: float,
) -> dict[str, float | bool]:
    """Evaluate lower UAR at matched FRR and lower FRR at matched UAR."""

    treatment_values = tuple(treatment)
    baseline_values = tuple(baseline)
    uar_deltas = [t.uar - b.uar for t in treatment_values for b in baseline_values if abs(t.frr - b.frr) <= frr_tolerance]
    frr_deltas = [t.frr - b.frr for t in treatment_values for b in baseline_values if abs(t.uar - b.uar) <= uar_tolerance]
    return {
        "matched_frr_pairs": len(uar_deltas),
        "best_uar_delta_at_matched_frr": min(uar_deltas) if uar_deltas else float("nan"),
        "lower_uar_at_matched_frr": bool(uar_deltas and min(uar_deltas) < 0.0),
        "matched_uar_pairs": len(frr_deltas),
        "best_frr_delta_at_matched_uar": min(frr_deltas) if frr_deltas else float("nan"),
        "lower_frr_at_matched_uar": bool(frr_deltas and min(frr_deltas) < 0.0),
    }


def is_reject_or_escalate_all(point: FrontierPoint, tolerance: float = 1e-12) -> bool:
    return point.frr >= 1.0 - tolerance or point.escalation >= 1.0 - tolerance


def _vector(point: FrontierPoint) -> tuple[float, float, float, float]:
    return point.uar, point.frr, point.escalation, point.compute


def _hypervolume_recursive(points: tuple[tuple[float, ...], ...], reference: tuple[float, ...]) -> float:
    if not points:
        return 0.0
    if len(reference) == 1:
        return max(0.0, reference[0] - min(point[0] for point in points))
    coordinates = sorted({point[0] for point in points if point[0] < reference[0]})
    volume = 0.0
    for index, lower in enumerate(coordinates):
        upper = coordinates[index + 1] if index + 1 < len(coordinates) else reference[0]
        active = tuple(point[1:] for point in points if point[0] <= lower)
        volume += max(0.0, upper - lower) * _hypervolume_recursive(active, reference[1:])
    return volume
