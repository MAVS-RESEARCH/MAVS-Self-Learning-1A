"""Complete frozen Phase 4 operating-point registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mavs10d.baselines.phase4_base import OperatingPoint, expand_grid
from mavs10d.core.hashing import stable_hash


REPO_ROOT = Path(__file__).resolve().parents[3]
SWEEP_PATH = REPO_ROOT / "configs/baselines/phase4_sweeps.yaml"


def load_operating_points() -> tuple[OperatingPoint, ...]:
    payload = yaml.safe_load(SWEEP_PATH.read_text(encoding="utf-8"))
    points: list[OperatingPoint] = []
    for registry_name, entry in payload["families"].items():
        family = str(entry.get("family", registry_name))
        for mechanism in entry["mechanisms"]:
            for condition in entry["conditions"]:
                for index, parameters in enumerate(expand_grid(entry["grid"])):
                    point_id = f"{family}.{mechanism}.{condition}.p{index:02d}"
                    points.append(
                        OperatingPoint(
                            point_id=point_id,
                            family=family,
                            mechanism=str(mechanism),
                            condition=str(condition),
                            parameters=parameters,
                            budget=dict(entry["budget"]),
                            module=str(entry["module"]),
                            competitive=bool(entry["competitive"]),
                            oracle=family == "oracle",
                            fidelity_label="diagnostic_bound" if family in {"trivial", "oracle"} else "faithful_benchmark_adaptation",
                            source_registry="docs/baseline_sources.md",
                        )
                    )
    identifiers = [point.point_id for point in points]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Phase 4 operating-point IDs must be unique.")
    return tuple(points)


def registry_manifest() -> dict[str, Any]:
    points = load_operating_points()
    payload = {"schema_version": "1.0.0", "points": [point.to_dict() for point in points]}
    return {**payload, "registry_hash": stable_hash(payload)}

