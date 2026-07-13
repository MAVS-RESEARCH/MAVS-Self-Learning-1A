"""Resolution-IV fractional-factorial and targeted interaction definitions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Mapping

import numpy as np


FACTORS = (
    "meta_diagnostics", "synthesis", "retained_replay",
    "counterfactual_validation", "certification", "configuration_library",
)
DEFINING_WORDS = ("ABCE", "BCDF", "ADEF")


@dataclass(frozen=True)
class FactorialRun:
    run_id: str
    levels: Mapping[str, int]


def resolution_iv_design() -> tuple[FactorialRun, ...]:
    runs: list[FactorialRun] = []
    for index, (a, b, c, d) in enumerate(product((-1, 1), repeat=4)):
        levels = (a, b, c, d, a * b * c, b * c * d)
        runs.append(FactorialRun(f"F{index:02d}", dict(zip(FACTORS, levels))))
    validate_resolution_iv(tuple(runs))
    return tuple(runs)


def validate_resolution_iv(runs: tuple[FactorialRun, ...]) -> None:
    if len(runs) != 16 or min(map(len, DEFINING_WORDS)) != 4:
        raise ValueError("The Phase 5 factorial must be a 16-run resolution-IV design.")
    matrix = np.asarray([[run.levels[factor] for factor in FACTORS] for run in runs], dtype=np.int8)
    if not np.all(matrix.sum(axis=0) == 0):
        raise ValueError("Factorial main effects must be balanced.")
    cross = matrix.T @ matrix
    if not np.array_equal(cross, np.eye(len(FACTORS), dtype=np.int8) * len(runs)):
        raise ValueError("Factorial main-effect columns must be mutually orthogonal.")


def factor_state(levels: Mapping[str, int]) -> dict[str, bool]:
    return {
        "meta_diagnostics": levels["meta_diagnostics"] > 0,
        "diagnostic_creation": levels["synthesis"] > 0,
        "retained_replay": levels["retained_replay"] > 0,
        "counterfactual_validation": levels["counterfactual_validation"] > 0,
        "adversarial_certification": levels["certification"] > 0,
        "configuration_library": levels["configuration_library"] > 0,
    }
