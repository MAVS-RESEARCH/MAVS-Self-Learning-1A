from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mavs10d.core.trace_logging import console_log
from mavs10d.training.datasets import (
    SplitManifest,
    freeze_model_artifact_hash_manifest,
    validate_phase5_split_manifest,
)


@dataclass(frozen=True)
class HoldoutEvaluationPlan:
    artifact_dir: Path
    benchmark_family: str
    status: str
    checks: list[str]
    artifact_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_dir": str(self.artifact_dir),
            "benchmark_family": self.benchmark_family,
            "status": self.status,
            "checks": self.checks,
            "artifact_hash": self.artifact_hash,
        }


def plan_holdout_evaluation(
    artifact_dir: str | Path,
    manifest: SplitManifest,
    *,
    benchmark_family: str,
) -> HoldoutEvaluationPlan:
    # console.log: phase5.training.evaluate_holdout.start
    console_log(
        "phase5.training.evaluate_holdout.start",
        artifact_dir=str(artifact_dir),
        benchmark_family=benchmark_family,
    )
    errors = validate_phase5_split_manifest(manifest)
    if errors:
        raise ValueError(f"invalid split manifest: {errors}")
    frozen_artifact = freeze_model_artifact_hash_manifest(artifact_dir)
    if benchmark_family in manifest.training.environment_families:
        raise ValueError("holdout validation must use benchmark families different from training")
    plan = HoldoutEvaluationPlan(
        artifact_dir=Path(artifact_dir),
        benchmark_family=benchmark_family,
        status="ready_for_frozen_artifact_evaluation",
        checks=[
            "training_card_present",
            "manifest_present",
            "calibration_present",
            "model_artifact_present",
            "frozen_artifact_hash_present",
            "holdout_family_disjoint_from_training",
        ],
        artifact_hash=str(frozen_artifact["artifact_hash"]),
    )
    # console.log: phase5.training.evaluate_holdout.complete
    console_log("phase5.training.evaluate_holdout.complete", status=plan.status)
    return plan
