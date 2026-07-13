from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from mavs10d.core.hashing import stable_hash
from mavs10d.core.trace_logging import console_log


@dataclass(frozen=True)
class EnvironmentConfig:
    id: str
    type: str
    params: dict[str, Any]


@dataclass(frozen=True)
class MethodConfig:
    id: str
    type: str
    params: dict[str, Any]


@dataclass(frozen=True)
class OutputConfig:
    raw_traces: Path


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    run_id: str
    seeds: list[int]
    episode_steps: int
    environment: EnvironmentConfig
    methods: list[MethodConfig]
    metrics: list[str]
    outputs: OutputConfig
    metadata: dict[str, Any]
    source_path: Path | None = None
    config_hash: str | None = None

    @classmethod
    def from_mapping(
        cls, data: dict[str, Any], source_path: Path | None = None
    ) -> "ExperimentConfig":
        experiment = dict(data.get("experiment", data))
        environment = dict(experiment["env"])
        methods = [dict(method) for method in experiment["methods"]]
        outputs = dict(experiment["outputs"])
        config = cls(
            name=str(experiment["name"]),
            run_id=str(experiment.get("run_id", experiment["name"])),
            seeds=[int(seed) for seed in experiment["seeds"]],
            episode_steps=int(experiment["episode_steps"]),
            environment=EnvironmentConfig(
                id=str(environment.get("id", environment["type"])),
                type=str(environment["type"]),
                params=dict(environment.get("params", {})),
            ),
            methods=[
                MethodConfig(
                    id=str(method.get("id", method["type"])),
                    type=str(method["type"]),
                    params=dict(method.get("params", {})),
                )
                for method in methods
            ],
            metrics=[str(metric) for metric in experiment.get("metrics", [])],
            outputs=OutputConfig(raw_traces=Path(outputs["raw_traces"])),
            metadata=dict(experiment.get("metadata", {})),
            source_path=source_path,
            config_hash=stable_hash(experiment),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Experiment name is required.")
        if not self.seeds:
            raise ValueError("At least one seed is required.")
        if self.episode_steps <= 0:
            raise ValueError("episode_steps must be positive.")
        if not self.methods:
            raise ValueError("At least one method is required.")
        if not self.outputs.raw_traces:
            raise ValueError("outputs.raw_traces is required.")

    def seed_frame(self) -> pd.DataFrame:
        return pd.DataFrame({"seed": self.seeds})


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    # console.log: phase1.load_config.start
    console_log("phase1.load_config.start", path=str(path))
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {path}")
    # console.log: phase1.load_config.yaml_loaded
    console_log("phase1.load_config.yaml_loaded", path=str(path), top_level=list(data))
    return data


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)
    data = load_yaml_mapping(config_path)
    config = ExperimentConfig.from_mapping(data, source_path=config_path)
    # console.log: phase1.load_config.validated
    console_log(
        "phase1.load_config.validated",
        name=config.name,
        run_id=config.run_id,
        seeds=len(config.seeds),
        methods=len(config.methods),
        config_hash=config.config_hash,
    )
    return config

