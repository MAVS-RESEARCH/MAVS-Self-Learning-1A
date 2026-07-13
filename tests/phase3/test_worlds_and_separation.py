from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

from mavs10d.envs.phase3_gauntlet import OPERATION_FEATURES, Phase3WorldCompiler, load_repair_curricula


def test_ten_curricula_cover_every_versioned_operation_once() -> None:
    curricula = load_repair_curricula()
    assert len(curricula) == 10
    assert Counter(item.operation for item in curricula) == Counter({operation: 1 for operation in OPERATION_FEATURES})
    assert len({item.hidden_mechanism for item in curricula}) == 10


def test_curriculum_seed_namespaces_are_mutually_disjoint() -> None:
    curricula = load_repair_curricula()
    synthesis = {item.synthesis_seed for item in curricula}
    holdout = {item.holdout_seed for item in curricula}
    adversarial = {item.adversarial_seed for item in curricula}
    assert not synthesis & holdout
    assert not synthesis & adversarial
    assert not holdout & adversarial
    assert not any(900000 <= seed <= 999999 for seed in synthesis | holdout | adversarial)


def test_exact_generation_allocation_and_stage_coverage() -> None:
    compiled = Phase3WorldCompiler().compile_generation(1)
    assert len(compiled.visible) == len(compiled.hidden) == 20_000
    assert Counter(item.curriculum_id for item in compiled.visible) == Counter({f"R{index:02d}": 2000 for index in range(1, 11)})
    assert compiled.manifest["stage_counts"] == {
        "certification": 2000,
        "containment": 1000,
        "discovery": 2000,
        "proposal": 1000,
        "recurrence": 4000,
        "rollback_challenge": 2000,
        "shadow": 4000,
        "transfer": 4000,
    }


def test_visible_projection_excludes_hidden_intervention_and_labels() -> None:
    compiled = Phase3WorldCompiler().compile_generation(1)
    visible_keys = set(compiled.visible[0].to_dict())
    assert not {"unsafe", "correct_action", "expected_operation", "hidden_repair_mechanism"} & visible_keys
    visible_text = json.dumps([item.to_dict() for item in compiled.visible[:100]])
    assert all(item.hidden_mechanism not in visible_text for item in load_repair_curricula())
    supports = [json.loads(item.visible_features_json)["nearest_validated_support"] for item in compiled.visible]
    assert min(supports) == 0.1 and max(supports) == 0.9


def test_certification_bank_has_exact_independent_suite_counts() -> None:
    compiled = Phase3WorldCompiler().compile_generation(1)
    counts = Counter((item.curriculum_id, item.suite) for item in compiled.certification_cases)
    for curriculum in load_repair_curricula():
        assert counts[(curriculum.curriculum_id, "trigger_replay")] == 32
        assert counts[(curriculum.curriculum_id, "retained_replay")] == 32
        assert counts[(curriculum.curriculum_id, "disjoint_temporal_holdout")] == 32
        assert counts[(curriculum.curriculum_id, "boundary")] == 32
        assert counts[(curriculum.curriculum_id, "counterfactual")] == 32
        assert counts[(curriculum.curriculum_id, "independent_adversarial")] == 64
        assert counts[(curriculum.curriculum_id, "shadow")] == 100


def test_phase3_config_is_exact_and_no_training_is_declared() -> None:
    config = yaml.safe_load(Path("configs/phases/phase3.yaml").read_text(encoding="utf-8"))
    assert config["canonical_decisions_per_generation"] == config["curricula_count"] * config["decisions_per_curriculum"] == 20_000
    assert config["conditions"] == ["cumulative", "fresh"]
    assert config["model_training"] == "none"
    assert config["post_holdout_retuning"] is False
