from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mavs10d.core.config import (  # noqa: E402
    EnvironmentConfig,
    ExperimentConfig,
    MethodConfig,
    OutputConfig,
    load_experiment_config,
)
from mavs10d.core.runner import ExperimentRunner  # noqa: E402
from mavs10d.core.trace_logging import console_log  # noqa: E402
from mavs10d.training.datasets import FINAL_SEED_RANGE, require_training_card_and_manifest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a MAVS Phase 6 experiment suite.")
    parser.add_argument("--suite", required=True, help="Suite YAML path.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print effective configs without running.")
    parser.add_argument("--only", nargs="*", help="Optional suite experiment ids to run.")
    parser.add_argument("--max-seeds", type=int, help="Bound seed count for local stress checks.")
    parser.add_argument("--max-episode-steps", type=int, help="Bound episode steps for local stress checks.")
    parser.add_argument("--output-dir", help="Override raw output directory.")
    return parser.parse_args()


def load_suite(path: str | Path) -> dict[str, Any]:
    # console.log: phase6.script.run_suite.load.start
    console_log("phase6.script.run_suite.load.start", suite=str(path))
    suite_path = Path(path)
    with suite_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    suite = dict(data.get("suite", data))
    suite["_suite_path"] = str(suite_path)
    # console.log: phase6.script.run_suite.load.complete
    console_log("phase6.script.run_suite.load.complete", experiments=len(suite.get("experiments", [])))
    return suite


def build_effective_config(
    suite: dict[str, Any],
    entry: dict[str, Any],
    *,
    max_seeds: int | None = None,
    max_episode_steps: int | None = None,
    output_dir: str | None = None,
) -> ExperimentConfig:
    # console.log: phase6.script.run_suite.config.start
    console_log("phase6.script.run_suite.config.start", experiment_id=entry.get("id"))
    base = load_experiment_config(REPO_ROOT / entry["config"])
    overrides = dict(entry.get("overrides", {}))
    seeds = _seed_list(overrides.get("seeds", base.seeds))
    if max_seeds is not None:
        seeds = seeds[:max_seeds]
    episode_steps = int(overrides.get("episode_steps", base.episode_steps))
    if max_episode_steps is not None:
        episode_steps = min(episode_steps, int(max_episode_steps))
    environment = _environment_config(base.environment, overrides.get("env"), episode_steps)
    methods = _method_configs(overrides.get("methods"), base.methods)
    metadata = {
        **base.metadata,
        **dict(overrides.get("metadata", {})),
        "suite": suite.get("name"),
        "experiment_code": entry.get("code"),
        "phase": "phase6",
        "model_training": "none",
        "negative_controls": suite.get("negative_controls", []),
    }
    output = Path(overrides.get("output", base.outputs.raw_traces))
    if output_dir:
        output = Path(output_dir) / output.name
    config = replace(
        base,
        name=str(overrides.get("name", base.name)),
        run_id=str(overrides.get("run_id", base.run_id)),
        seeds=seeds,
        episode_steps=episode_steps,
        environment=environment,
        methods=methods,
        outputs=OutputConfig(raw_traces=output),
        metadata=metadata,
    )
    validate_phase6_config(config, entry)
    # console.log: phase6.script.run_suite.config.complete
    console_log(
        "phase6.script.run_suite.config.complete",
        experiment_id=entry.get("id"),
        seeds=len(config.seeds),
        episode_steps=config.episode_steps,
        methods=len(config.methods),
    )
    return config


def validate_phase6_config(config: ExperimentConfig, entry: dict[str, Any]) -> None:
    # console.log: phase6.script.run_suite.validate.start
    console_log("phase6.script.run_suite.validate.start", experiment_id=entry.get("id"))
    if entry.get("final", True):
        low, high = FINAL_SEED_RANGE
        bad_seeds = [seed for seed in config.seeds if seed < low or seed > high]
        if bad_seeds:
            raise ValueError(f"Phase 6 final config references non-final seeds: {bad_seeds[:5]}")
    for method in config.methods:
        artifact_dir = method.params.get("artifact_dir")
        if artifact_dir:
            require_training_card_and_manifest(REPO_ROOT / str(artifact_dir))
    required = dict(entry.get("required_minimum", {}))
    declared = dict(entry.get("declared_minimum", {}))
    if required and declared:
        for key, value in required.items():
            if int(declared.get(key, 0)) < int(value):
                raise ValueError(f"Suite entry {entry.get('id')} declares insufficient {key}")
    # console.log: phase6.script.run_suite.validate.complete
    console_log("phase6.script.run_suite.validate.complete", experiment_id=entry.get("id"))


def run_suite(
    suite_path: str | Path,
    *,
    dry_run: bool = False,
    only: list[str] | None = None,
    max_seeds: int | None = None,
    max_episode_steps: int | None = None,
    output_dir: str | None = None,
) -> list[dict[str, Any]]:
    # console.log: phase6.script.run_suite.start
    console_log("phase6.script.run_suite.start", suite=str(suite_path), dry_run=dry_run)
    suite = load_suite(suite_path)
    runner = ExperimentRunner(repo_root=REPO_ROOT)
    selected = set(only or [])
    manifest_rows: list[dict[str, Any]] = []
    for entry in suite.get("experiments", []):
        if selected and entry.get("id") not in selected:
            continue
        config = build_effective_config(
            suite,
            entry,
            max_seeds=max_seeds,
            max_episode_steps=max_episode_steps,
            output_dir=output_dir,
        )
        if dry_run:
            row = {"id": entry.get("id"), "status": "validated", "records": 0, "output": str(config.outputs.raw_traces)}
        else:
            result = runner.run(config)
            row = {
                "id": entry.get("id"),
                "status": "complete",
                "records": result.records_written,
                "output": str(result.output_path),
                "config_hash": result.config_hash,
            }
        manifest_rows.append(row)
    _write_suite_manifest(manifest_rows, output_dir)
    # console.log: phase6.script.run_suite.complete
    console_log("phase6.script.run_suite.complete", experiments=len(manifest_rows))
    return manifest_rows


def _seed_list(value: Any) -> list[int]:
    if isinstance(value, dict):
        start = int(value["start"])
        count = int(value["count"])
        return list(range(start, start + count))
    return [int(seed) for seed in value]


def _environment_config(
    base: EnvironmentConfig,
    override: dict[str, Any] | None,
    episode_steps: int,
) -> EnvironmentConfig:
    if not override:
        params = {**base.params, "episode_steps": episode_steps}
        return replace(base, params=params)
    params = dict(override.get("params", base.params))
    params["episode_steps"] = episode_steps
    return EnvironmentConfig(
        id=str(override.get("id", base.id)),
        type=str(override.get("type", base.type)),
        params=params,
    )


def _method_configs(value: Any, base_methods: list[MethodConfig]) -> list[MethodConfig]:
    if not value:
        return base_methods
    return [
        MethodConfig(
            id=str(item["id"]),
            type=str(item["type"]),
            params=dict(item.get("params", {})),
        )
        for item in value
    ]


def _write_suite_manifest(rows: list[dict[str, Any]], output_dir: str | None) -> None:
    root = Path(output_dir) if output_dir else REPO_ROOT / "results" / "processed"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "suite_run_manifest.json"
    path.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_suite(
        args.suite,
        dry_run=args.dry_run,
        only=args.only,
        max_seeds=args.max_seeds,
        max_episode_steps=args.max_episode_steps,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
