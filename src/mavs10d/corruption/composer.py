"""Deterministic composition of bounded corruption transforms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import numpy as np


Transform = Callable[[Mapping[str, Any], float, np.random.Generator], dict[str, Any]]


@dataclass(frozen=True)
class CorruptionOperation:
    family: str
    intensity: float
    target: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError("Corruption intensity must be within [0, 1].")


class CorruptionComposer:
    def __init__(self, registry: Mapping[str, Transform]) -> None:
        self._registry = dict(registry)

    def apply(
        self,
        record: Mapping[str, Any],
        operations: Sequence[CorruptionOperation],
        rng: np.random.Generator,
    ) -> tuple[dict[str, Any], tuple[str, ...]]:
        output = dict(record)
        applied: list[str] = []
        for operation in operations:
            if operation.family not in self._registry:
                raise KeyError(f"Unknown corruption family: {operation.family}")
            output = self._registry[operation.family](output, operation.intensity, rng)
            applied.append(operation.family)
        return output, tuple(applied)


def bounded_numeric_noise(
    record: Mapping[str, Any], intensity: float, rng: np.random.Generator
) -> dict[str, Any]:
    output = dict(record)
    for key, value in record.items():
        if isinstance(value, float):
            output[key] = float(np.clip(value + rng.normal(0.0, intensity), 0.0, 1.0))
    return output
