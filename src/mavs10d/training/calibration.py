from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mavs10d.baselines.common import clamp
from mavs10d.core.trace_logging import console_log
from mavs10d.training.datasets import CALIBRATION_SEED_RANGE


@dataclass(frozen=True)
class CalibrationResult:
    threshold: float
    source: str
    seed_range: tuple[int, int]
    score_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "source": self.source,
            "seed_range": list(self.seed_range),
            "score_count": self.score_count,
        }


def calibrate_threshold_from_scores(
    scores: list[float],
    *,
    quantile: float = 0.80,
    seed_range: tuple[int, int] = CALIBRATION_SEED_RANGE,
) -> CalibrationResult:
    # console.log: phase5.training.calibration.threshold.start
    console_log(
        "phase5.training.calibration.threshold.start",
        score_count=len(scores),
        quantile=quantile,
        seed_range=seed_range,
    )
    if seed_range != CALIBRATION_SEED_RANGE:
        raise ValueError("threshold calibration must use calibration-only seed range 1000-1999")
    if not scores:
        raise ValueError("scores are required for calibration")
    ordered = sorted(clamp(float(score)) for score in scores)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * clamp(quantile)))))
    result = CalibrationResult(
        threshold=ordered[index],
        source="calibration_only_scores",
        seed_range=seed_range,
        score_count=len(ordered),
    )
    # console.log: phase5.training.calibration.threshold.complete
    console_log(
        "phase5.training.calibration.threshold.complete",
        threshold=result.threshold,
        score_count=result.score_count,
    )
    return result


def calibration_manifest() -> dict[str, Any]:
    # console.log: phase5.training.calibration.manifest
    console_log("phase5.training.calibration.manifest")
    return {
        "seed_range": list(CALIBRATION_SEED_RANGE),
        "allowed_environment_families": ["text_safety_stream", "synthetic_ops"],
        "purpose": "threshold and conformal calibration only",
        "not_for_final_claims": True,
    }

