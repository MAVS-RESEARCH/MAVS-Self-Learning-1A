from dataclasses import replace
from pathlib import Path

from mavs10d.core.config import EnvironmentConfig, OutputConfig, load_experiment_config
from mavs10d.core.registry import build_default_registry
from mavs10d.core.runner import ExperimentRunner
from mavs10d.core.trace_logging import iter_jsonl, validate_trace_file


PHASE2_CONFIGS = [
    Path("configs/experiments/dyn_corruption_text.yaml"),
    Path("configs/experiments/tool_use_security.yaml"),
    Path("configs/experiments/cyber_triage.yaml"),
    Path("configs/experiments/multi_agent_triage.yaml"),
    Path("configs/experiments/synthetic_ops.yaml"),
    Path("configs/experiments/stress_schedule_sweep.yaml"),
]


def test_default_registry_contains_phase2_environment_types() -> None:
    registry = build_default_registry()

    for env_type in [
        "text_safety_stream",
        "tool_use_security",
        "cyber_triage",
        "multi_agent_operations",
        "synthetic_ops",
        "correlated_representation_collapse",
        "static_accuracy_adapter",
    ]:
        assert env_type in registry.environment_types()


def test_dynamic_environment_contract_and_hidden_labels() -> None:
    registry = build_default_registry()
    config = EnvironmentConfig(
        id="text_safety_contract",
        type="text_safety_stream",
        params={"episode_steps": 5},
    )
    env = registry.create_environment(config)
    obs = env.reset(seed=7)
    candidate = env.propose_candidate(obs)
    labels = env.hidden_labels()

    assert obs.risk_context["active_phase"]
    assert labels["active_phase"] == obs.risk_context["active_phase"]
    assert candidate.action_type
    assert candidate.content
    assert 0.0 <= candidate.confidence <= 1.0
    assert candidate.specialist_outputs
    assert candidate.provenance["active_phase"] == obs.risk_context["active_phase"]


def test_phase2_configs_run_and_emit_active_phase_traces(tmp_path: Path) -> None:
    runner = ExperimentRunner(repo_root=Path.cwd())
    for config_path in PHASE2_CONFIGS:
        config = load_experiment_config(config_path)
        config = replace(
            config,
            outputs=OutputConfig(raw_traces=tmp_path / f"{config.name}.jsonl"),
        )
        result = runner.run(config)
        validation = validate_trace_file(result.output_path)
        records = list(iter_jsonl(result.output_path))

        assert validation.ok, validation.errors
        assert records
        assert result.records_written == config.episode_steps * len(config.seeds)
        assert all(record["observation"]["risk_context"]["active_phase"] for record in records)
        assert all(record["hidden_label_hash"] for record in records)
        assert all("decision" in record for record in records)
        assert all("step_result" in record for record in records)
        assert all(record["step_result"]["info"]["active_phase"] for record in records)


def test_all_phase2_environment_modules_exist() -> None:
    expected = [
        Path("src/mavs10d/envs/base.py"),
        Path("src/mavs10d/envs/text_safety_env.py"),
        Path("src/mavs10d/envs/tool_use_env.py"),
        Path("src/mavs10d/envs/cyber_triage_env.py"),
        Path("src/mavs10d/envs/multi_agent_env.py"),
        Path("src/mavs10d/envs/synthetic_ops_env.py"),
        Path("src/mavs10d/envs/correlated_collapse_env.py"),
        Path("src/mavs10d/envs/static_accuracy_adapter.py"),
    ]

    assert all(path.exists() for path in expected)

