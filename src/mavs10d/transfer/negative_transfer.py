"""Paired inherited-state harm detection and quarantine semantics."""

from __future__ import annotations

import numpy as np


def inherited_harm(cumulative_reward: np.ndarray, fresh_reward: np.ndarray) -> np.ndarray:
    if cumulative_reward.shape != fresh_reward.shape:
        raise ValueError("Negative-transfer comparisons require paired arrays.")
    return cumulative_reward < fresh_reward


def severe_harm(cumulative_reward: np.ndarray, fresh_reward: np.ndarray, threshold: float = 1.0) -> np.ndarray:
    return (fresh_reward - cumulative_reward) >= threshold


def detected_harm(harm: np.ndarray, detector_enabled: bool, shift_score: np.ndarray) -> np.ndarray:
    return harm & (shift_score >= 0.55) if detector_enabled else np.zeros_like(harm, dtype=bool)
