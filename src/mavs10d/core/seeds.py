from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SeedState:
    seed: int
    python_random_state: object
    numpy_random_state: list[int]


def set_deterministic_seed(seed: int) -> SeedState:
    random.seed(seed)
    np.random.seed(seed)
    return SeedState(
        seed=seed,
        python_random_state=random.getstate(),
        numpy_random_state=np.random.get_state()[1].tolist(),  # type: ignore[call-overload]
    )


def derive_seed(base_seed: int, namespace: str, offset: int = 0) -> int:
    total = base_seed + offset
    for character in namespace:
        total = (total * 131 + ord(character)) % (2**32 - 1)
    return total


def seed_sequence(seeds: list[int]) -> list[int]:
    if not seeds:
        raise ValueError("At least one seed is required.")
    return [int(seed) for seed in seeds]
