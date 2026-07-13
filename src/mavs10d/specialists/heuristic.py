from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mavs10d.core.trace_logging import console_log
from mavs10d.specialists.base import SpecialistOutput, clamp_score
from mavs10d.specialists.retrieval import RetrievalSpecialist
from mavs10d.specialists.symbolic import SymbolicPolicySpecialist


@dataclass(frozen=True)
class HeuristicRiskSpecialist:
    specialist_id: str = "risk_heuristic"

    def evaluate(self, scenario: dict[str, Any]) -> SpecialistOutput:
        risk = float(scenario.get("risk_score", 0.0))
        return SpecialistOutput(
            specialist_id=self.specialist_id,
            score=clamp_score(1.0 - risk),
            confidence=clamp_score(0.60 + abs(0.5 - risk)),
            source="deterministic_risk_heuristic",
            rationale="score is inverse of scenario risk proxy",
            metadata={"risk_score": risk},
        )


@dataclass(frozen=True)
class HeuristicSpecialistBank:
    specialists: tuple[Any, ...] = (
        HeuristicRiskSpecialist(),
        RetrievalSpecialist(),
        SymbolicPolicySpecialist(),
    )

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> "HeuristicSpecialistBank":
        return cls()

    def evaluate(self, scenario: dict[str, Any]) -> dict[str, dict[str, Any]]:
        # console.log: phase2.specialists.heuristic_bank.evaluate
        console_log(
            "phase2.specialists.heuristic_bank.evaluate",
            t=scenario.get("t"),
            active_phase=scenario.get("active_phase"),
            specialist_count=len(self.specialists),
        )
        outputs = [specialist.evaluate(scenario) for specialist in self.specialists]
        return {output.specialist_id: output.to_dict() for output in outputs}

