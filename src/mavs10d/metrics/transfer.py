"""Pre-registered paired cross-generation estimands."""

from __future__ import annotations

import math


def forward_transfer(cumulative_objective: float, fresh_objective: float) -> float:
    return cumulative_objective - fresh_objective


def cold_start_reduction(fresh_early_loss: float, cumulative_early_loss: float) -> float:
    return fresh_early_loss - cumulative_early_loss


def learning_acceleration(fresh_ttr: float, cumulative_ttr: float) -> float:
    if cumulative_ttr == 0:
        return math.inf if fresh_ttr > 0 else math.nan
    return fresh_ttr / cumulative_ttr


def diagnostic_reuse_rate(successful_inherited: int, inherited_eligible: int) -> float:
    return _safe_ratio(successful_inherited, inherited_eligible)


def novelty_yield(certified_new: int, proposed_new: int) -> float:
    return _safe_ratio(certified_new, proposed_new)


def negative_transfer_rate(inherited_worse: int, paired_count: int) -> float:
    return _safe_ratio(inherited_worse, paired_count)


def _safe_ratio(numerator: int, denominator: int) -> float:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("Invalid estimand counts.")
    return numerator / denominator if denominator else math.nan
