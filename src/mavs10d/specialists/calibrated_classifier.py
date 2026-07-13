from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mavs10d.core.trace_logging import console_log
from mavs10d.specialists.base import SpecialistOutput, clamp_score
from mavs10d.training.datasets import freeze_model_artifact_hash_manifest


@dataclass(frozen=True)
class CalibratedClassifierSpecialist:
    specialist_id: str
    artifact_dir: Path
    threshold: float

    @classmethod
    def from_artifact_dir(
        cls,
        artifact_dir: str | Path,
        *,
        specialist_id: str = "calibrated_classifier",
    ) -> "CalibratedClassifierSpecialist":
        # console.log: phase5.specialists.calibrated_classifier.from_artifact
        console_log(
            "phase5.specialists.calibrated_classifier.from_artifact",
            artifact_dir=str(artifact_dir),
        )
        root = Path(artifact_dir)
        freeze_model_artifact_hash_manifest(root)
        with (root / "calibration.json").open("r", encoding="utf-8") as handle:
            calibration = json.load(handle)
        return cls(
            specialist_id=specialist_id,
            artifact_dir=root,
            threshold=float(calibration.get("threshold", 0.50)),
        )

    def evaluate(self, scenario: dict[str, Any]) -> SpecialistOutput:
        # console.log: phase5.specialists.calibrated_classifier.evaluate
        console_log(
            "phase5.specialists.calibrated_classifier.evaluate",
            specialist_id=self.specialist_id,
            t=scenario.get("t"),
        )
        risk = float(scenario.get("risk_score", 0.0))
        calibrated_score = clamp_score(1.0 - risk)
        return SpecialistOutput(
            specialist_id=self.specialist_id,
            score=calibrated_score,
            confidence=clamp_score(abs(calibrated_score - self.threshold) + 0.50),
            source="frozen_calibrated_classifier",
            rationale="frozen calibrated classifier score derived from scenario risk proxy",
            metadata={
                "artifact_dir": str(self.artifact_dir),
                "threshold": self.threshold,
                "model_artifact_required": True,
                "frozen_artifact_required": True,
            },
        )


def validate_classifier_artifact(artifact_dir: str | Path) -> bool:
    # console.log: phase5.specialists.calibrated_classifier.validate_artifact
    console_log(
        "phase5.specialists.calibrated_classifier.validate_artifact",
        artifact_dir=str(artifact_dir),
    )
    CalibratedClassifierSpecialist.from_artifact_dir(artifact_dir)
    return True
