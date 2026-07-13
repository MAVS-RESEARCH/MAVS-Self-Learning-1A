from pathlib import Path

import pytest

from mavs10d.core.config import ExperimentConfig, load_experiment_config


def test_load_synthetic_smoke_config() -> None:
    config = load_experiment_config(Path("configs/experiments/synthetic_smoke.yaml"))

    assert config.name == "synthetic_smoke"
    assert config.seeds == [1, 2]
    assert config.episode_steps == 4
    assert config.environment.type == "synthetic_smoke"
    assert config.methods[0].type == "risk_threshold"
    assert config.config_hash
    assert list(config.seed_frame()["seed"]) == [1, 2]


def test_config_hash_is_stable() -> None:
    config_a = load_experiment_config(Path("configs/experiments/synthetic_smoke.yaml"))
    config_b = load_experiment_config(Path("configs/experiments/synthetic_smoke.yaml"))

    assert config_a.config_hash == config_b.config_hash


def test_config_validation_rejects_missing_seeds() -> None:
    with pytest.raises(ValueError, match="At least one seed"):
        ExperimentConfig.from_mapping(
            {
                "experiment": {
                    "name": "bad",
                    "seeds": [],
                    "episode_steps": 1,
                    "env": {"type": "synthetic_smoke"},
                    "methods": [{"type": "risk_threshold"}],
                    "outputs": {"raw_traces": "results/raw/bad.jsonl"},
                }
            }
        )

