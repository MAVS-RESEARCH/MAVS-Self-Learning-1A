from dataclasses import replace
from pathlib import Path

from mavs10d.core.config import OutputConfig, load_experiment_config
from mavs10d.core.runner import ExperimentRunner
from mavs10d.core.trace_logging import iter_jsonl, validate_trace_file
from mavs10d.governance.ablations import REQUIRED_ABLATION_NAMES
from mavs10d.training.datasets import PHASE5_BENCHMARK_SETS


PHASE5_CONFIGS = [
    Path("configs/experiments/ablation_study.yaml"),
    Path("configs/experiments/model_training_optional.yaml"),
    Path("configs/experiments/model_holdout_validation.yaml"),
    Path("configs/experiments/dynamic_governance_v1_dev.yaml"),
    Path("configs/experiments/dynamic_governance_v1_final.yaml"),
    Path("configs/experiments/correlated_failure_final.yaml"),
    Path("configs/experiments/stress_schedule_sweep_final.yaml"),
    Path("configs/experiments/external_taxonomy_projection.yaml"),
]


def test_ablation_study_runs_all_config_level_variants(tmp_path: Path) -> None:
    config = load_experiment_config(Path("configs/experiments/ablation_study.yaml"))
    config = replace(config, outputs=OutputConfig(raw_traces=tmp_path / "ablation_study.jsonl"))

    result = ExperimentRunner(repo_root=Path.cwd()).run(config)
    validation = validate_trace_file(result.output_path)
    records = list(iter_jsonl(result.output_path))

    assert validation.ok, validation.errors
    assert result.records_written == config.episode_steps * len(config.seeds) * len(config.methods)
    assert len(config.methods) == len(REQUIRED_ABLATION_NAMES)
    assert {record["decision"]["trace"]["ablation"]["name"] for record in records} == set(
        REQUIRED_ABLATION_NAMES
    )
    assert all(record["decision"]["trace"]["formal_calculus"]["ablation"] for record in records)


def test_phase5_benchmark_configs_exist_and_exclude_training_seeds_and_schedules() -> None:
    benchmark_sets = set()
    for config_path in PHASE5_CONFIGS:
        config = load_experiment_config(config_path)
        benchmark_sets.add(str(config.metadata["benchmark_set"]))
        schedule_id = str(config.environment.params.get("schedule", {}).get("id", ""))
        if "final" in config.name or config.metadata["benchmark_set"] in {
            "ablation_study_final",
            "external_taxonomy_projection",
        }:
            assert all(seed >= 10000 for seed in config.seeds)
            assert schedule_id not in {"clean_to_mild", "mild_to_burst", "clean_to_mild_training"}
        if config.metadata["benchmark_set"] == "model_training_optional":
            assert all(1 <= seed <= 999 for seed in config.seeds)
        if config.metadata["benchmark_set"] == "model_holdout_validation":
            assert all(2000 <= seed <= 2999 for seed in config.seeds)

    assert set(PHASE5_BENCHMARK_SETS) <= benchmark_sets

