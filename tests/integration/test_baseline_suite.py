from pathlib import Path

from mavs10d.core.config import load_experiment_config
from mavs10d.core.registry import build_default_registry
from mavs10d.core.runner import ExperimentRunner
from mavs10d.core.trace_logging import iter_jsonl, validate_trace_file


BASELINE_TYPES = [
    "policy_rails",
    "validator_stack",
    "confidence_gate",
    "disagreement_gate",
    "self_consistency",
    "conformal_static",
    "conformal_adaptive",
    "reject_option",
]


def test_default_registry_contains_all_phase3_baselines() -> None:
    registry = build_default_registry()

    for baseline_type in BASELINE_TYPES:
        assert baseline_type in registry.method_types()
        assert baseline_type in registry.baseline_types()


def test_baseline_suite_runs_through_common_runner(tmp_path: Path) -> None:
    config = load_experiment_config(Path("configs/experiments/baseline_suite_dev.yaml"))
    config = type(config)(
        name=config.name,
        run_id=config.run_id,
        seeds=config.seeds,
        episode_steps=config.episode_steps,
        environment=config.environment,
        methods=config.methods,
        metrics=config.metrics,
        outputs=type(config.outputs)(raw_traces=tmp_path / "baseline_suite_dev.jsonl"),
        metadata=config.metadata,
        source_path=config.source_path,
        config_hash=config.config_hash,
    )
    result = ExperimentRunner(repo_root=Path.cwd()).run(config)
    validation = validate_trace_file(result.output_path)
    records = list(iter_jsonl(result.output_path))

    assert validation.ok, validation.errors
    assert result.records_written == config.episode_steps * len(config.seeds) * len(config.methods)
    assert {record["method_id"] for record in records} == {method.id for method in config.methods}
    assert all(record["trace_complete"] for record in records)
    assert all(record["decision"]["trace"]["final_threshold"] is not None for record in records)
    assert all(record["candidate"]["specialist_outputs"] for record in records)

