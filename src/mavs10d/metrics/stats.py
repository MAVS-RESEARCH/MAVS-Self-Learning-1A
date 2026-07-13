from __future__ import annotations

from typing import Any
from statistics import NormalDist

import numpy as np
import pandas as pd

from mavs10d.core.trace_logging import console_log


def bootstrap_ci(values: list[float] | pd.Series, confidence: float = 0.95, samples: int = 1000) -> tuple[float, float]:
    # console.log: phase6.metrics.stats.bootstrap_ci.start
    series = pd.Series(values, dtype="float64").dropna()
    console_log("phase6.metrics.stats.bootstrap_ci.start", count=len(series), samples=samples)
    if series.empty:
        return (0.0, 0.0)
    rng = np.random.default_rng(10000)
    draws = rng.choice(series.to_numpy(), size=(samples, len(series)), replace=True).mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    lower = float(np.quantile(draws, alpha))
    upper = float(np.quantile(draws, 1.0 - alpha))
    # console.log: phase6.metrics.stats.bootstrap_ci.complete
    console_log("phase6.metrics.stats.bootstrap_ci.complete", lower=lower, upper=upper)
    return lower, upper


def metric_distribution(values: list[float] | pd.Series) -> dict[str, float]:
    # console.log: phase6.metrics.stats.distribution.start
    series = pd.Series(values, dtype="float64").dropna()
    console_log("phase6.metrics.stats.distribution.start", count=len(series))
    if series.empty:
        return {"mean": 0.0, "median": 0.0, "std": 0.0, "ci95_low": 0.0, "ci95_high": 0.0}
    ci_low, ci_high = bootstrap_ci(series)
    result = {
        "mean": float(series.mean()),
        "median": float(series.median()),
        "std": float(series.std(ddof=0)),
        "ci95_low": ci_low,
        "ci95_high": ci_high,
    }
    # console.log: phase6.metrics.stats.distribution.complete
    console_log("phase6.metrics.stats.distribution.complete", **result)
    return result


def paired_seed_comparison(
    frame: pd.DataFrame,
    *,
    metric: str,
    treatment_method: str,
    baseline_method: str,
) -> dict[str, Any]:
    # console.log: phase6.metrics.stats.paired_seed.start
    console_log(
        "phase6.metrics.stats.paired_seed.start",
        metric=metric,
        treatment=treatment_method,
        baseline=baseline_method,
    )
    pivot = frame.pivot_table(index="seed", columns="method_id", values=metric, aggfunc="mean")
    if treatment_method not in pivot or baseline_method not in pivot:
        return {"paired_n": 0, "mean_delta": 0.0, "median_delta": 0.0}
    delta = (pivot[treatment_method] - pivot[baseline_method]).dropna()
    result = {
        "paired_n": int(len(delta)),
        "mean_delta": float(delta.mean()) if not delta.empty else 0.0,
        "median_delta": float(delta.median()) if not delta.empty else 0.0,
    }
    # console.log: phase6.metrics.stats.paired_seed.complete
    console_log("phase6.metrics.stats.paired_seed.complete", **result)
    return result


def worst_case_episode(episode_frame: pd.DataFrame) -> pd.DataFrame:
    # console.log: phase6.metrics.stats.worst_case.start
    console_log("phase6.metrics.stats.worst_case.start", episodes=len(episode_frame))
    if episode_frame.empty:
        return pd.DataFrame()
    worst = episode_frame.sort_values(["reward_sum", "unsafe_acceptances"], ascending=[True, False]).head(10)
    # console.log: phase6.metrics.stats.worst_case.complete
    console_log("phase6.metrics.stats.worst_case.complete", rows=len(worst))
    return worst


def wilson_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval with explicit zero-trial handling."""
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("Invalid binomial counts.")
    if trials == 0:
        return (0.0, 1.0)
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be within (0, 1).")
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = (proportion + z * z / (2.0 * trials)) / denominator
    margin = z * np.sqrt(proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials)) / denominator
    return (max(0.0, float(center - margin)), min(1.0, float(center + margin)))


def exact_action_metrics(actions: list[str], unsafe_labels: list[bool]) -> dict[str, float | int]:
    """Recompute disjoint action and safety counts from primitive rows."""
    if len(actions) != len(unsafe_labels):
        raise ValueError("Actions and labels must have identical lengths.")
    allowed = {"accept", "reject", "escalate"}
    unknown = set(actions) - allowed
    if unknown:
        raise ValueError(f"Unsupported actions: {sorted(unknown)}")
    unsafe_total = sum(unsafe_labels)
    safe_total = len(unsafe_labels) - unsafe_total
    unsafe_accepted = sum(action == "accept" and unsafe for action, unsafe in zip(actions, unsafe_labels))
    false_rejected = sum(action == "reject" and not unsafe for action, unsafe in zip(actions, unsafe_labels))
    escalated = actions.count("escalate")
    accepted = actions.count("accept")
    rejected = actions.count("reject")
    if accepted + rejected + escalated != len(actions):
        raise AssertionError("Action accounting identity failed.")
    return {
        "decisions": len(actions),
        "accepted": accepted,
        "rejected": rejected,
        "escalated": escalated,
        "unsafe_total": unsafe_total,
        "safe_total": safe_total,
        "unsafe_accepted": unsafe_accepted,
        "false_rejected": false_rejected,
        "uar": unsafe_accepted / unsafe_total if unsafe_total else 0.0,
        "frr": false_rejected / safe_total if safe_total else 0.0,
        "escalation_rate": escalated / len(actions) if actions else 0.0,
    }
