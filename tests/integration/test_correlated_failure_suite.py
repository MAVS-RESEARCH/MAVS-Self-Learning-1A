from dataclasses import replace
from pathlib import Path

from mavs10d.core.config import OutputConfig, load_experiment_config
from mavs10d.core.registry import build_default_registry
from mavs10d.core.runner import ExperimentRunner
from mavs10d.core.trace_logging import iter_jsonl, validate_trace_file


def test_phase4_registry_contains_mavs_gc_and_heuristic_baselines() -> None:
    registry = build_default_registry()

    assert "mavs_gc" in registry.method_types()
    for baseline in ["judge", "debate", "critique_revise"]:
        assert baseline in registry.method_types()
        assert baseline in registry.baseline_types()


def test_correlated_failure_suite_runs_through_common_runner(tmp_path: Path) -> None:
    config = load_experiment_config(Path("configs/experiments/correlated_failure.yaml"))
    config = replace(config, outputs=OutputConfig(raw_traces=tmp_path / "correlated_failure.jsonl"))

    result = ExperimentRunner(repo_root=Path.cwd()).run(config)
    validation = validate_trace_file(result.output_path)
    records = list(iter_jsonl(result.output_path))

    assert validation.ok, validation.errors
    assert result.records_written == config.episode_steps * len(config.seeds) * len(config.methods)
    assert {"mavs_gc_phase4", "judge_phase4", "debate_phase4", "critique_revise_phase4"} == {
        record["method_id"] for record in records
    }
    mavs_records = [record for record in records if record["method_id"] == "mavs_gc_phase4"]
    assert mavs_records
    assert all("formal_calculus" in record["decision"]["trace"] for record in mavs_records)
    assert any(
        "shared_retrieval_context"
        in [
            item["type"]
            for item in record["candidate"]["provenance"].get("transform_history", [])
        ]
        for record in records
    )

