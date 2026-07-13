from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mavs10d.core.hashing import file_sha256, stable_hash
from mavs10d.core.trace_logging import console_log


TRAIN_SEED_RANGE = (1, 999)
CALIBRATION_SEED_RANGE = (1000, 1999)
DEVELOPMENT_SEED_RANGE = (2000, 2999)
FINAL_SEED_RANGE = (10000, 19999)

TRAIN_ENV_FAMILIES = ("text_safety_stream", "synthetic_ops")
CALIBRATION_ENV_FAMILIES = ("text_safety_stream", "synthetic_ops")
FINAL_ENV_FAMILIES = (
    "tool_use_security",
    "cyber_triage",
    "multi_agent_operations",
    "correlated_representation_collapse",
    "synthetic_ops",
)
TRAIN_TRANSFORMS = ("ambiguity_injection", "confidence_miscalibration")
FINAL_TRANSFORMS = (
    "prompt_injection",
    "evidence_masking",
    "label_drift",
    "shared_wrong_premise",
    "exfiltration_bait",
    "residual_drift",
)
TRAIN_SCHEDULES = ("clean_to_mild", "mild_to_burst")
FINAL_SCHEDULES = (
    "late_correlated_collapse",
    "burst_recovery",
    "high_noise_sweep",
    "adversarial_adaptation",
)
EXTERNAL_BENCHMARK_FAMILIES = (
    "helm_safety",
    "cyberseceval",
    "swe_bench",
    "browserbench_webarena",
    "gaia",
)
NEGATIVE_CONTROLS = (
    "label_shuffle",
    "seed_shuffle",
    "schedule_shuffle",
    "benign_only_rejection_trap",
    "unsafe_only_acceptance_trap",
)
LEAKAGE_CHECKS = (
    "hash_overlap",
    "prompt_content_near_duplicate",
    "scenario_template_overlap",
    "corruption_template_overlap",
)
OVERFITTING_INDICATORS = (
    "train_calibration_final_uar_frr_reward_gap",
    "calibration_error_gap",
    "performance_collapse_under_unseen_transforms",
    "threshold_sensitivity",
    "per_environment_variance",
)
PHASE5_BENCHMARK_SETS = (
    "model_holdout_validation",
    "dynamic_governance_v1_dev",
    "dynamic_governance_v1_final",
    "correlated_failure_final",
    "stress_schedule_sweep_final",
    "ablation_study_final",
    "external_taxonomy_projection",
)
REQUIRED_MODEL_ARTIFACT_FILES = (
    "training_card.md",
    "train_manifest.json",
    "calibration.json",
    "model.joblib",
)


@dataclass(frozen=True)
class SplitPartition:
    name: str
    seed_range: tuple[int, int]
    environment_families: tuple[str, ...]
    corruption_families: tuple[str, ...]
    schedules: tuple[str, ...]
    benchmark_families: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "seed_range": list(self.seed_range),
            "environment_families": list(self.environment_families),
            "corruption_families": list(self.corruption_families),
            "schedules": list(self.schedules),
            "benchmark_families": list(self.benchmark_families),
        }


@dataclass(frozen=True)
class SplitManifest:
    training: SplitPartition
    calibration: SplitPartition
    development_validation: SplitPartition
    final: SplitPartition
    frozen_hyperparameters: dict[str, Any]
    hyperparameter_search_space: dict[str, Any]
    negative_controls: tuple[str, ...]
    leakage_checks: tuple[str, ...]
    overfitting_indicators: tuple[str, ...]
    benchmark_sets: tuple[str, ...]
    model_training_decision: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "training": self.training.to_dict(),
            "calibration": self.calibration.to_dict(),
            "development_validation": self.development_validation.to_dict(),
            "final": self.final.to_dict(),
            "frozen_hyperparameters": self.frozen_hyperparameters,
            "hyperparameter_search_space": self.hyperparameter_search_space,
            "negative_controls": list(self.negative_controls),
            "leakage_checks": list(self.leakage_checks),
            "overfitting_indicators": list(self.overfitting_indicators),
            "benchmark_sets": list(self.benchmark_sets),
            "model_training_decision": self.model_training_decision,
        }


def build_default_phase5_split_manifest() -> SplitManifest:
    # console.log: phase5.training.datasets.build_manifest
    console_log("phase5.training.datasets.build_manifest")
    return SplitManifest(
        training=SplitPartition(
            name="training",
            seed_range=TRAIN_SEED_RANGE,
            environment_families=TRAIN_ENV_FAMILIES,
            corruption_families=TRAIN_TRANSFORMS,
            schedules=TRAIN_SCHEDULES,
        ),
        calibration=SplitPartition(
            name="calibration",
            seed_range=CALIBRATION_SEED_RANGE,
            environment_families=CALIBRATION_ENV_FAMILIES,
            corruption_families=TRAIN_TRANSFORMS,
            schedules=("calibration_clean_to_mild", "calibration_mild_to_burst"),
        ),
        development_validation=SplitPartition(
            name="development_validation",
            seed_range=DEVELOPMENT_SEED_RANGE,
            environment_families=("text_safety_stream", "synthetic_ops", "tool_use_security"),
            corruption_families=("ambiguity_injection", "confidence_miscalibration", "prompt_injection"),
            schedules=("development_dynamic_governance_v1",),
        ),
        final=SplitPartition(
            name="final",
            seed_range=FINAL_SEED_RANGE,
            environment_families=FINAL_ENV_FAMILIES,
            corruption_families=FINAL_TRANSFORMS,
            schedules=FINAL_SCHEDULES,
            benchmark_families=EXTERNAL_BENCHMARK_FAMILIES,
        ),
        frozen_hyperparameters={
            "model_family": "none",
            "classifier": "not_trained",
            "threshold_selection": "calibration_only",
        },
        hyperparameter_search_space={
            "classifier": ["logistic_regression", "calibrated_linear"],
            "calibration_method": ["isotonic", "temperature_scaling"],
            "regularization_c": [0.1, 1.0, 10.0],
        },
        negative_controls=NEGATIVE_CONTROLS,
        leakage_checks=LEAKAGE_CHECKS,
        overfitting_indicators=OVERFITTING_INDICATORS,
        benchmark_sets=PHASE5_BENCHMARK_SETS,
        model_training_decision="no_models_trained_in_phase5",
    )


def validate_phase5_split_manifest(manifest: SplitManifest | dict[str, Any]) -> list[str]:
    # console.log: phase5.training.datasets.validate_manifest.start
    console_log("phase5.training.datasets.validate_manifest.start")
    data = manifest.to_dict() if isinstance(manifest, SplitManifest) else dict(manifest)
    errors: list[str] = []
    partitions = [
        data["training"],
        data["calibration"],
        data["development_validation"],
        data["final"],
    ]
    for left_index, left in enumerate(partitions):
        for right in partitions[left_index + 1 :]:
            if _ranges_overlap(tuple(left["seed_range"]), tuple(right["seed_range"])):
                errors.append(f"seed range overlap: {left['name']} and {right['name']}")
    training_envs = set(data["training"]["environment_families"])
    final_envs = set(data["final"]["environment_families"])
    if training_envs & final_envs - {"synthetic_ops"}:
        errors.append("final benchmark uses disallowed training environment family")
    if set(data["training"]["corruption_families"]) & set(data["final"]["corruption_families"]):
        errors.append("final benchmark uses training corruption family")
    if set(data["training"]["schedules"]) & set(data["final"]["schedules"]):
        errors.append("final benchmark uses training schedule")
    if tuple(data["training"]["seed_range"]) != TRAIN_SEED_RANGE:
        errors.append("training seed range must be 1-999")
    if tuple(data["calibration"]["seed_range"]) != CALIBRATION_SEED_RANGE:
        errors.append("calibration seed range must be 1000-1999")
    if tuple(data["development_validation"]["seed_range"]) != DEVELOPMENT_SEED_RANGE:
        errors.append("development validation seed range must be 2000-2999")
    if tuple(data["final"]["seed_range"]) != FINAL_SEED_RANGE:
        errors.append("final seed range must be 10000-19999")
    for control in NEGATIVE_CONTROLS:
        if control not in data.get("negative_controls", []):
            errors.append(f"missing negative control: {control}")
    for check in LEAKAGE_CHECKS:
        if check not in data.get("leakage_checks", []):
            errors.append(f"missing leakage check: {check}")
    for benchmark in PHASE5_BENCHMARK_SETS:
        if benchmark not in data.get("benchmark_sets", []):
            errors.append(f"missing benchmark set: {benchmark}")
    # console.log: phase5.training.datasets.validate_manifest.complete
    console_log(
        "phase5.training.datasets.validate_manifest.complete",
        errors=len(errors),
    )
    return errors


def example_hash(example: dict[str, Any]) -> str:
    # console.log: phase5.training.datasets.example_hash
    console_log("phase5.training.datasets.example_hash", keys=sorted(example))
    return stable_hash(example)


def hash_overlap(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> set[str]:
    # console.log: phase5.training.datasets.hash_overlap
    console_log("phase5.training.datasets.hash_overlap", left=len(left), right=len(right))
    return {example_hash(item) for item in left} & {example_hash(item) for item in right}


def prompt_content_near_duplicates(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
) -> list[tuple[int, int]]:
    # console.log: phase5.training.datasets.near_duplicates
    console_log("phase5.training.datasets.near_duplicates", left=len(left), right=len(right))
    pairs: list[tuple[int, int]] = []
    left_text = [_normalized_text(item) for item in left]
    right_text = [_normalized_text(item) for item in right]
    for left_index, left_value in enumerate(left_text):
        for right_index, right_value in enumerate(right_text):
            if left_value and left_value == right_value:
                pairs.append((left_index, right_index))
    return pairs


def scenario_template_overlap(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> set[str]:
    # console.log: phase5.training.datasets.scenario_template_overlap
    console_log("phase5.training.datasets.scenario_template_overlap")
    return {str(item.get("scenario_template", "")) for item in left} & {
        str(item.get("scenario_template", "")) for item in right
    } - {""}


def corruption_template_overlap(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> set[str]:
    # console.log: phase5.training.datasets.corruption_template_overlap
    console_log("phase5.training.datasets.corruption_template_overlap")
    return {str(item.get("corruption_template", "")) for item in left} & {
        str(item.get("corruption_template", "")) for item in right
    } - {""}


def require_training_card_and_manifest(artifact_dir: str | Path) -> None:
    # console.log: phase5.training.datasets.require_artifact_docs
    console_log("phase5.training.datasets.require_artifact_docs", artifact_dir=str(artifact_dir))
    root = Path(artifact_dir)
    missing = [
        path.name
        for path in [
            root / "training_card.md",
            root / "train_manifest.json",
            root / "calibration.json",
        ]
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(f"Model artifact is missing required files: {missing}")


def freeze_model_artifact_hash_manifest(artifact_dir: str | Path) -> dict[str, Any]:
    # console.log: phase5.training.datasets.freeze_artifact_hash.start
    console_log("phase5.training.datasets.freeze_artifact_hash.start", artifact_dir=str(artifact_dir))
    root = Path(artifact_dir)
    require_training_card_and_manifest(root)
    missing = [name for name in REQUIRED_MODEL_ARTIFACT_FILES if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(f"Model artifact is missing required files: {missing}")
    file_hashes = {name: file_sha256(root / name) for name in REQUIRED_MODEL_ARTIFACT_FILES}
    manifest = {
        "artifact_dir": str(root),
        "required_files": list(REQUIRED_MODEL_ARTIFACT_FILES),
        "file_hashes": file_hashes,
        "artifact_hash": stable_hash(file_hashes),
        "frozen": True,
    }
    # console.log: phase5.training.datasets.freeze_artifact_hash.complete
    console_log(
        "phase5.training.datasets.freeze_artifact_hash.complete",
        artifact_hash=manifest["artifact_hash"],
    )
    return manifest


def _ranges_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return max(left[0], right[0]) <= min(left[1], right[1])


def _normalized_text(example: dict[str, Any]) -> str:
    prompt = str(example.get("prompt", "")).lower().strip()
    content = str(example.get("content", "")).lower().strip()
    return " ".join(f"{prompt} {content}".split())
