from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mavs10d.specialists.base import SpecialistOutput, clamp_score


@dataclass(frozen=True)
class RetrievalSpecialist:
    specialist_id: str = "retrieval_proxy"

    def evaluate(self, scenario: dict[str, Any]) -> SpecialistOutput:
        evidence_visible = bool(scenario.get("evidence_visible", True))
        risk = float(scenario.get("risk_score", 0.0))
        score = clamp_score(1.0 - risk - (0.20 if not evidence_visible else 0.0))
        confidence = 0.80 if evidence_visible else 0.45
        return SpecialistOutput(
            specialist_id=self.specialist_id,
            score=score,
            confidence=confidence,
            source="deterministic_retrieval_proxy",
            rationale="visible evidence lowers estimated risk" if evidence_visible else "evidence masked",
            metadata={"evidence_visible": evidence_visible},
        )

