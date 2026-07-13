"""Exact non-dominance and hypervolume utilities for governance frontiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


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
