from pathlib import Path

from mavs10d.core.registry import build_default_registry
from mavs10d.core.runner import ExperimentRunner
from mavs10d.core.trace_logging import iter_jsonl, validate_trace_file


def test_trace_writer_and_validator(tmp_path: Path) -> None:
    config_path = Path("configs/experiments/synthetic_smoke.yaml")
    from mavs10d.core.config import load_experiment_config

    config = load_experiment_config(config_path)
    config = type(config)(
        name=config.name,
        run_id="tmp_trace_test",
        seeds=config.seeds,
        episode_steps=config.episode_steps,
        environment=config.environment,
        methods=config.methods,
        metrics=config.metrics,
        outputs=type(config.outputs)(raw_traces=tmp_path / "trace.jsonl"),
        metadata=config.metadata,
        source_path=config.source_path,
        config_hash=config.config_hash,
    )

    runner = ExperimentRunner(registry=build_default_registry(), repo_root=Path.cwd())
    result = runner.run(config)
    validation = validate_trace_file(result.output_path)

    assert result.records_written == 8
    assert validation.ok, validation.errors
    assert validation.record_count == 8


def test_trace_records_include_required_metadata(tmp_path: Path) -> None:
    config_path = Path("configs/experiments/synthetic_smoke.yaml")
    from mavs10d.core.config import load_experiment_config

    config = load_experiment_config(config_path)
    config = type(config)(
        name=config.name,
        run_id="tmp_trace_metadata_test",
        seeds=[1],
        episode_steps=config.episode_steps,
        environment=config.environment,
        methods=config.methods,
        metrics=config.metrics,
        outputs=type(config.outputs)(raw_traces=tmp_path / "trace.jsonl"),
        metadata=config.metadata,
        source_path=config.source_path,
        config_hash=config.config_hash,
    )
    runner = ExperimentRunner(registry=build_default_registry(), repo_root=Path.cwd())
    result = runner.run(config)
    records = list(iter_jsonl(result.output_path))

    assert records
    assert records[0]["config_hash"] == config.config_hash
    assert "git_commit" in records[0]
    assert records[0]["trace_complete"] is True
    assert records[0]["hidden_label_hash"]

