"""Pre-registered paired cross-generation estimands."""

from __future__ import annotations

import math


def constrained_objective(
    mean_reward: float,
    uar: float,
    frr: float,
    escalation_rate: float,
    normalized_compute: float,
) -> float:
    """Pre-registered higher-is-better scalar used only for paired transfer estimates."""

    return mean_reward - 2.5 * uar - 0.35 * frr - 0.15 * escalation_rate - 0.05 * normalized_compute


def forward_transfer(cumulative_objective: float, fresh_objective: float) -> float:
    return cumulative_objective - fresh_objective


def cold_start_reduction(fresh_early_loss: float, cumulative_early_loss: float) -> float:
    return fresh_early_loss - cumulative_early_loss


def learning_acceleration(fresh_ttr: float, cumulative_ttr: float) -> float:
    if cumulative_ttr == 0:
        return math.inf if fresh_ttr > 0 else math.nan
    return fresh_ttr / cumulative_ttr


def time_to_recovery(rewards: list[float], target: float, window: int = 5) -> float:
    """Return first 1-based index whose trailing window reaches target, or NaN."""

    if window <= 0:
        raise ValueError("Recovery window must be positive.")
    for index in range(window, len(rewards) + 1):
        if sum(rewards[index - window:index]) / window >= target:
            return float(index)
    return math.nan


def time_to_diagnosis(detected: list[bool]) -> float:
    """Return first 1-based inherited-harm diagnosis, or NaN when never diagnosed."""

    return float(detected.index(True) + 1) if True in detected else math.nan


def diagnostic_reuse_rate(successful_inherited: int, inherited_eligible: int) -> float:
    return _safe_ratio(successful_inherited, inherited_eligible)


def novelty_yield(certified_new: int, proposed_new: int) -> float:
    return _safe_ratio(certified_new, proposed_new)


def negative_transfer_rate(inherited_worse: int, paired_count: int) -> float:
    return _safe_ratio(inherited_worse, paired_count)


def catastrophic_governance_interference(new_catastrophes: int, paired_count: int) -> float:
    return _safe_ratio(new_catastrophes, paired_count)


def retention_score(retained_objective: float, prior_objective: float) -> float:
    if prior_objective == 0:
        return math.nan
    return retained_objective / prior_objective


def library_efficiency(objective_gain: float, retained_bytes: int) -> float:
    if retained_bytes < 0:
        raise ValueError("Retained bytes cannot be negative.")
    return objective_gain / (retained_bytes / 1048576.0) if retained_bytes else math.nan


def generation_improvement_slope(values: list[float]) -> float:
    """Ordinary least-squares slope over equally spaced generations."""

    if len(values) < 2:
        return math.nan
    x_mean = (len(values) - 1) / 2.0
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    return sum((index - x_mean) * (value - sum(values) / len(values)) for index, value in enumerate(values)) / denominator


def _safe_ratio(numerator: int, denominator: int) -> float:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("Invalid estimand counts.")
    return numerator / denominator if denominator else math.nan
