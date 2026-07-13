from __future__ import annotations

import random
import hashlib
from dataclasses import dataclass
from typing import Final

import numpy as np

from mavs10d.core.contracts import SeedTuple


_SEED_MODULUS: Final[int] = 2**63 - 1


@dataclass(frozen=True)
class HierarchicalSeeds:
    """Deterministic seed derivation without mutating module-global RNG state."""

    suite_seed: int

    def derive(
        self,
        *,
        generation: int = 0,
        world: int = 0,
        episode: int = 0,
        step: int = 0,
        method: int = 0,
    ) -> SeedTuple:
        values = [self.suite_seed]
        for namespace, index in (
            ("generation", generation),
            ("world", world),
            ("episode", episode),
            ("step", step),
            ("method", method),
        ):
            if index < 0:
                raise ValueError(f"{namespace} index must be non-negative.")
            payload = f"{values[-1]}:{namespace}:{index}".encode("utf-8")
            values.append(int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % _SEED_MODULUS)
        return SeedTuple(*values)

    def generator(self, **indices: int) -> np.random.Generator:
        seed_tuple = self.derive(**indices)
        return np.random.default_rng(seed_tuple.method)


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
