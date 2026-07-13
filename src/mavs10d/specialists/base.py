from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SpecialistOutput:
    specialist_id: str
    score: float
    confidence: float
    source: str
    rationale: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "specialist_id": self.specialist_id,
            "score": self.score,
            "confidence": self.confidence,
            "source": self.source,
            "rationale": self.rationale,
            "metadata": self.metadata,
        }


class Specialist(Protocol):
    specialist_id: str

    def evaluate(self, scenario: dict[str, Any]) -> SpecialistOutput:
        ...


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))

