"""Phase 4 paired, hierarchical, rare-event, and multiplicity statistics."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np


def exact_binomial_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Two-sided Clopper-Pearson interval without an optional SciPy dependency."""

    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("Invalid binomial counts.")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1).")
    if trials == 0:
        return 0.0, 1.0
    alpha = 1.0 - confidence
    lower = 0.0 if successes == 0 else _beta_quantile(alpha / 2.0, successes, trials - successes + 1)
    upper = 1.0 if successes == trials else _beta_quantile(1.0 - alpha / 2.0, successes + 1, trials - successes)
    return lower, upper


def hierarchical_bootstrap_ratio(
    numerators: Sequence[int],
    denominators: Sequence[int],
    *,
    repetitions: int,
    seed: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """World-first then episode-level binomial bootstrap for a rate."""

    numer = np.asarray(numerators, dtype=np.int64)
    denom = np.asarray(denominators, dtype=np.int64)
    if numer.shape != denom.shape or np.any(numer < 0) or np.any(denom < numer):
        raise ValueError("Invalid hierarchical rate counts.")
    rng = np.random.default_rng(seed)
    draws = np.empty(repetitions, dtype=np.float64)
    for index in range(repetitions):
        world_indices = rng.integers(0, len(numer), size=len(numer))
        sampled_den = denom[world_indices]
        probabilities = np.divide(numer[world_indices], sampled_den, out=np.zeros(len(sampled_den)), where=sampled_den > 0)
        sampled_num = rng.binomial(sampled_den, probabilities)
        draws[index] = sampled_num.sum() / sampled_den.sum() if sampled_den.sum() else 0.0
    alpha = (1.0 - confidence) / 2.0
    return float(np.quantile(draws, alpha)), float(np.quantile(draws, 1.0 - alpha))


def distribution_summary(values: Iterable[float], cvar_alpha: float = 0.10) -> dict[str, float]:
    array = np.asarray(tuple(values), dtype=np.float64)
    if not len(array):
        raise ValueError("A distribution summary requires values.")
    ordered = np.sort(array)
    tail_count = max(1, int(math.ceil(len(array) * cvar_alpha)))
    return {
        "mean": float(np.mean(array)), "median": float(np.median(array)), "sd": float(np.std(array)),
        "worst_decile": float(np.quantile(array, 0.90)), "worst_world": float(np.max(array)),
        "cvar": float(np.mean(ordered[-tail_count:])),
    }


def holm_adjust(p_values: Sequence[float]) -> tuple[float, ...]:
    """Holm family-wise adjusted p-values in original order."""

    if any(value < 0.0 or value > 1.0 for value in p_values):
        raise ValueError("p-values must be in [0, 1].")
    order = sorted(range(len(p_values)), key=lambda index: p_values[index])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(p_values) - rank) * p_values[index])
        adjusted[index] = min(1.0, running)
    return tuple(adjusted)


def paired_sign_test(deltas: Sequence[float]) -> float:
    nonzero = [value for value in deltas if value != 0.0]
    if not nonzero:
        return 1.0
    positive = sum(value > 0.0 for value in nonzero)
    smaller = min(positive, len(nonzero) - positive)
    log_terms = [
        math.lgamma(len(nonzero) + 1) - math.lgamma(k + 1) - math.lgamma(len(nonzero) - k + 1)
        for k in range(smaller + 1)
    ]
    maximum = max(log_terms)
    log_tail = maximum + math.log(sum(math.exp(value - maximum) for value in log_terms)) - len(nonzero) * math.log(2.0)
    return min(1.0, 2.0 * math.exp(log_tail))


def _beta_quantile(probability: float, a: float, b: float) -> float:
    low, high = 0.0, 1.0
    for _ in range(90):
        middle = (low + high) / 2.0
        if _regularized_beta(middle, a, b) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(a * math.log(x) + b * math.log1p(-x) - math.lgamma(a) - math.lgamma(b) + math.lgamma(a + b))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_fraction(x, a, b) / a
    return 1.0 - front * _beta_fraction(1.0 - x, b, a) / b


def _beta_fraction(x: float, a: float, b: float) -> float:
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = 1.0 / max(abs(d), tiny) * (1.0 if d >= 0 else -1.0)
    result = d
    for iteration in range(1, 201):
        m2 = 2 * iteration
        aa = iteration * (b - iteration) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        result *= d * c
        aa = -(a + iteration) * (qab + iteration) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return result
