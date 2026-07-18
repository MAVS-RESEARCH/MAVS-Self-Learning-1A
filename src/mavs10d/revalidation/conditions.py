"""Frozen Phase 9 condition registry and causal adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Phase9Condition:
    """A serialized comparator with an explicit state and claim rule."""

    id: str
    method: str
    state_rule: str
    competitive: bool = True
    oracle: bool = False
    source: str = "phase9_core"
    isolated_factor: str = "reference"
    configuration_json: str = "{}"

    @property
    def synthesis_enabled(self) -> bool:
        return self.method == "perception_closure_v04" or self.id.startswith(("I", "P", "L"))


def condition_registry(track_id: str) -> tuple[Phase9Condition, ...]:
    """Return the preregistered track-specific registry without result-directed selection."""

    if track_id not in {"paired_original_bank", "blind_bank"}:
        raise ValueError(f"Unknown Phase 9 track: {track_id}")
    raw = yaml.safe_load((REPO_ROOT / "configs/perception_closure_v04/phase9/condition_registry.yaml").read_text(encoding="utf-8"))
    conditions = [Phase9Condition(**item) for item in raw["core"]]
    phase = yaml.safe_load((REPO_ROOT / "configs/phases/phase9.yaml").read_text(encoding="utf-8"))
    if track_id == "paired_original_bank":
        for index in range(50):
            candidate = f"legacy_registry_A{index:02d}"
            definition = yaml.safe_load((REPO_ROOT / f"configs/ablations/A{index:02d}.yaml").read_text(encoding="utf-8"))
            conditions.append(Phase9Condition(candidate, "legacy_mavs_sl_registry", "legacy_registry", source="phase5_A0_A49", isolated_factor=definition["exact_condition"], configuration_json=json.dumps(definition["changes"], sort_keys=True, separators=(",", ":"))))
        ablations = [*(f"I{i}" for i in range(12)), *(f"P{i}" for i in range(16)), *(f"L{i}" for i in range(11))]
    else:
        ablations = list(phase["condition_sets"]["track_b"]["claim_critical_ablations"])
    for identifier in ablations:
        conditions.append(Phase9Condition(identifier, "perception_closure_v04", _ablation_state(identifier), competitive=identifier != "P15", oracle=identifier == "P15", source="phase8", isolated_factor=identifier))
    seen: set[str] = set()
    if any(item.id in seen or seen.add(item.id) for item in conditions):
        raise RuntimeError("Duplicate Phase 9 condition identifier.")
    return tuple(conditions)


def _ablation_state(identifier: str) -> str:
    if identifier == "L1":
        return "fresh"
    if identifier == "L2":
        return "frozen_after_g1"
    return "cumulative"


def condition_manifest(track_id: str) -> list[dict[str, Any]]:
    return [item.__dict__ | {"synthesis_enabled": item.synthesis_enabled} for item in condition_registry(track_id)]
