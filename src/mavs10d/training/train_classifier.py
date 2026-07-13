from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mavs10d.core.trace_logging import console_log
from mavs10d.training.datasets import SplitManifest, validate_phase5_split_manifest


@dataclass(frozen=True)
class TrainingRunResult:
    status: str
    model_id: str | None
    artifact_dir: Path | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "model_id": self.model_id,
            "artifact_dir": str(self.artifact_dir) if self.artifact_dir else None,
            "reason": self.reason,
        }


def train_optional_classifier(
    manifest: SplitManifest,
    *,
    artifact_dir: str | Path | None = None,
    allow_training: bool = False,
) -> TrainingRunResult:
    # console.log: phase5.training.train_classifier.start
    console_log(
        "phase5.training.train_classifier.start",
        allow_training=allow_training,
        artifact_dir=str(artifact_dir) if artifact_dir else None,
    )
    errors = validate_phase5_split_manifest(manifest)
    if errors:
        raise ValueError(f"invalid split manifest: {errors}")
    if not allow_training:
        result = TrainingRunResult(
            status="skipped",
            model_id=None,
            artifact_dir=None,
            reason="no_models_trained_in_phase5",
        )
        # console.log: phase5.training.train_classifier.skipped
        console_log("phase5.training.train_classifier.skipped", reason=result.reason)
        return result
    if artifact_dir is None:
        raise ValueError("artifact_dir is required when allow_training=True")
    result = TrainingRunResult(
        status="blocked",
        model_id="optional_calibrated_classifier",
        artifact_dir=Path(artifact_dir),
        reason="training implementation is scaffolded; artifact freeze is required before evaluation",
    )
    # console.log: phase5.training.train_classifier.blocked
    console_log("phase5.training.train_classifier.blocked", reason=result.reason)
    return result

