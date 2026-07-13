from pathlib import Path

from mavs10d.core.config import load_experiment_config
from mavs10d.core.runner import ExperimentRunner
from mavs10d.core.trace_logging import iter_jsonl, validate_trace_file


def test_runner_is_deterministic_for_same_seed_and_config(tmp_path: Path) -> None:
    original = load_experiment_config(Path("configs/experiments/synthetic_smoke.yaml"))
    output_a = tmp_path / "a.jsonl"
    output_b = tmp_path / "b.jsonl"
    config_a = type(original)(
        name=original.name,
        run_id="determinism_a",
        seeds=[11, 12],
        episode_steps=original.episode_steps,
        environment=original.environment,
        methods=original.methods,
        metrics=original.metrics,
        outputs=type(original.outputs)(raw_traces=output_a),
        metadata=original.metadata,
        source_path=original.source_path,
        config_hash=original.config_hash,
    )
    config_b = type(original)(
        name=original.name,
        run_id="determinism_a",
        seeds=[11, 12],
        episode_steps=original.episode_steps,
        environment=original.environment,
        methods=original.methods,
        metrics=original.metrics,
        outputs=type(original.outputs)(raw_traces=output_b),
        metadata=original.metadata,
        source_path=original.source_path,
        config_hash=original.config_hash,
    )
    runner = ExperimentRunner(repo_root=Path.cwd())
    runner.run(config_a)
    runner.run(config_b)

    records_a = list(iter_jsonl(output_a))
    records_b = list(iter_jsonl(output_b))
    for record in records_a + records_b:
        record["created_at_utc"] = "normalized"

    assert records_a == records_b
    assert validate_trace_file(output_a).ok
    assert validate_trace_file(output_b).ok


def test_runner_handles_larger_phase1_stress_case(tmp_path: Path) -> None:
    original = load_experiment_config(Path("configs/experiments/synthetic_smoke.yaml"))
    config = type(original)(
        name="synthetic_smoke_stress",
        run_id="synthetic_smoke_stress",
        seeds=list(range(1, 21)),
        episode_steps=original.episode_steps,
        environment=original.environment,
        methods=original.methods,
        metrics=original.metrics,
        outputs=type(original.outputs)(raw_traces=tmp_path / "stress.jsonl"),
        metadata={**original.metadata, "stress": True},
        source_path=original.source_path,
        config_hash=original.config_hash,
    )
    result = ExperimentRunner(repo_root=Path.cwd()).run(config)
    validation = validate_trace_file(result.output_path)

    assert result.records_written == 80
    assert validation.ok, validation.errors
    assert validation.record_count == 80

