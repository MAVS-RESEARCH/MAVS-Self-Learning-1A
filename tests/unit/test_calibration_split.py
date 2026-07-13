import json
from dataclasses import replace
from pathlib import Path

import pytest

from mavs10d.specialists.calibrated_classifier import validate_classifier_artifact
from mavs10d.specialists.small_lm import SmallLMConfig
from mavs10d.training.calibration import calibrate_threshold_from_scores
from mavs10d.training.datasets import (
    CALIBRATION_SEED_RANGE,
    FINAL_SEED_RANGE,
    SplitPartition,
    build_default_phase5_split_manifest,
    corruption_template_overlap,
    freeze_model_artifact_hash_manifest,
    hash_overlap,
    prompt_content_near_duplicates,
    scenario_template_overlap,
    validate_phase5_split_manifest,
)
from mavs10d.training.evaluate_holdout import plan_holdout_evaluation
from mavs10d.training.train_classifier import train_optional_classifier


def test_default_split_manifest_satisfies_phase5_controls() -> None:
    manifest = build_default_phase5_split_manifest()

    assert validate_phase5_split_manifest(manifest) == []
    assert manifest.training.seed_range == (1, 999)
    assert manifest.calibration.seed_range == CALIBRATION_SEED_RANGE
    assert manifest.final.seed_range == FINAL_SEED_RANGE
    assert manifest.model_training_decision == "no_models_trained_in_phase5"


def test_split_manifest_rejects_seed_overlap_and_training_transform_leakage() -> None:
    manifest = build_default_phase5_split_manifest()
    invalid = replace(
        manifest,
        final=SplitPartition(
            name="final",
            seed_range=(900, 1100),
            environment_families=("tool_use_security",),
            corruption_families=("ambiguity_injection",),
            schedules=("clean_to_mild",),
        ),
    )

    errors = validate_phase5_split_manifest(invalid)

    assert any("seed range overlap" in error for error in errors)
    assert any("training corruption family" in error for error in errors)
    assert any("training schedule" in error for error in errors)


def test_leakage_check_helpers_detect_overlap() -> None:
    train = [
        {
            "prompt": "Review account action",
            "content": "candidate",
            "scenario_template": "account_review",
            "corruption_template": "ambiguity_injection",
        }
    ]
    final = [
        {
            "prompt": "Review account action",
            "content": "candidate",
            "scenario_template": "account_review",
            "corruption_template": "prompt_injection",
        }
    ]

    assert hash_overlap(train, train)
    assert prompt_content_near_duplicates(train, final) == [(0, 0)]
    assert scenario_template_overlap(train, final) == {"account_review"}
    assert corruption_template_overlap(train, final) == set()


def test_calibration_requires_calibration_seed_range() -> None:
    result = calibrate_threshold_from_scores([0.1, 0.2, 0.8], seed_range=CALIBRATION_SEED_RANGE)

    assert result.threshold == 0.8
    with pytest.raises(ValueError, match="calibration-only seed range"):
        calibrate_threshold_from_scores([0.1, 0.2], seed_range=(1, 999))


def test_optional_training_is_skipped_without_model_artifacts() -> None:
    manifest = build_default_phase5_split_manifest()

    result = train_optional_classifier(manifest, allow_training=False)

    assert result.status == "skipped"
    assert result.reason == "no_models_trained_in_phase5"


def test_model_artifact_requires_training_card_manifest_and_calibration(tmp_path: Path) -> None:
    manifest = build_default_phase5_split_manifest()

    with pytest.raises(FileNotFoundError, match="training_card"):
        plan_holdout_evaluation(tmp_path, manifest, benchmark_family="tool_use_security")

    (tmp_path / "training_card.md").write_text("# Training Card\n", encoding="utf-8")
    (tmp_path / "train_manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
    (tmp_path / "calibration.json").write_text(json.dumps({"threshold": 0.5}), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="model.joblib"):
        validate_classifier_artifact(tmp_path)

    (tmp_path / "model.joblib").write_text("placeholder frozen model", encoding="utf-8")
    frozen_artifact = freeze_model_artifact_hash_manifest(tmp_path)
    assert frozen_artifact["frozen"] is True
    assert frozen_artifact["file_hashes"]["model.joblib"]
    assert validate_classifier_artifact(tmp_path)
    plan = plan_holdout_evaluation(tmp_path, manifest, benchmark_family="tool_use_security")
    assert plan.status == "ready_for_frozen_artifact_evaluation"
    assert plan.artifact_hash == frozen_artifact["artifact_hash"]


def test_small_lm_config_enforces_phase5_model_scale_rules() -> None:
    disabled = SmallLMConfig.from_params({"enabled": False})
    assert disabled.enabled is False

    with pytest.raises(ValueError, match="1B-3B"):
        SmallLMConfig.from_params(
            {
                "enabled": True,
                "model_name": "oversized",
                "revision": "abc",
                "parameter_count_b": 7.0,
                "quantization": "int4",
            }
        )
