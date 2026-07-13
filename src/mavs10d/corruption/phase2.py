"""Typed Phase 2 corruption families, compositions, and bounded schedules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import yaml


@dataclass(frozen=True)
class CorruptionFamily:
    name: str
    target: str
    interaction: str
    development: bool
    evaluation: bool
    held_out_mechanism: bool = False


@dataclass(frozen=True)
class CorruptionComposition:
    composition_id: str
    families: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 2 <= len(self.families) <= 4:
            raise ValueError("Phase 2 compositions must contain two to four families.")
        if len(set(self.families)) != len(self.families):
            raise ValueError("A Phase 2 composition cannot repeat a family.")


@dataclass(frozen=True)
class CorruptionSchedule:
    onset: int
    duration: int
    intensity: float
    target: str
    interaction: str
    recovery: int

    def __post_init__(self) -> None:
        if not 0 <= self.onset < 100:
            raise ValueError("Corruption onset must be within the episode.")
        if self.duration <= 0 or self.recovery <= 0:
            raise ValueError("Corruption duration and recovery must be positive.")
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError("Corruption intensity must be within [0, 1].")

    def state_at(self, step: int) -> tuple[float, bool, bool]:
        if step < self.onset:
            return 0.0, False, False
        end = self.onset + self.duration
        if step < end:
            progress = (step - self.onset) / max(1, self.duration - 1)
            shape = 0.70 + 0.30 * np.sin(np.pi * progress)
            return float(np.clip(self.intensity * shape, 0.0, 1.0)), True, False
        recovery_end = end + self.recovery
        if step < recovery_end:
            remaining = 1.0 - (step - end + 1) / self.recovery
            return float(np.clip(self.intensity * remaining, 0.0, 1.0)), False, True
        return 0.0, False, False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_phase2_registry(root: Path) -> tuple[dict[str, CorruptionFamily], tuple[CorruptionComposition, ...], tuple[tuple[str, ...], ...]]:
    family_data = yaml.safe_load((root / "configs/corruptions/phase2_families.yaml").read_text(encoding="utf-8"))
    composition_data = yaml.safe_load((root / "configs/corruptions/phase2_compositions.yaml").read_text(encoding="utf-8"))
    families = {
        name: CorruptionFamily(
            name=name,
            target=str(value["target"]),
            interaction=str(value["interaction"]),
            development=bool(value["development"]),
            evaluation=bool(value["evaluation"]),
            held_out_mechanism=bool(value.get("held_out_mechanism", False)),
        )
        for name, value in family_data["families"].items()
    }
    compositions = tuple(
        CorruptionComposition(str(item["id"]), tuple(str(name) for name in item["families"]))
        for item in composition_data["evaluation_compositions"]
    )
    development = tuple(tuple(str(name) for name in item) for item in composition_data["development_compositions"])
    for composition in compositions:
        unknown = set(composition.families) - set(families)
        if unknown:
            raise ValueError(f"Unknown corruption families in {composition.composition_id}: {sorted(unknown)}")
    return families, compositions, development


def sample_schedule(rng: np.random.Generator, family: CorruptionFamily) -> CorruptionSchedule:
    return CorruptionSchedule(
        onset=int(rng.integers(8, 31)),
        duration=int(rng.integers(32, 56)),
        intensity=float(rng.uniform(0.35, 0.90)),
        target=family.target,
        interaction=str(rng.choice((family.interaction, "synergistic", "antagonistic"))),
        recovery=int(rng.integers(8, 21)),
    )


def apply_visible_corruptions(
    visible: Mapping[str, Any],
    families: Sequence[str],
    intensity: float,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Apply only participant-visible effects; latent causes remain outside this mapping."""

    output = dict(visible)
    active = set(families)
    if "provenance_concentration" in active or "evidence_source_compromise" in active:
        output["provenance_concentration"] = float(np.clip(output.get("provenance_concentration", 0.0) + 0.75 * intensity, 0.0, 1.0))
    if "evidence_masking" in active:
        output["evidence_status"] = "masked"
        output["masking_score"] = float(np.clip(0.55 + 0.45 * intensity, 0.0, 1.0))
    if "ambiguity_injection" in active:
        output["ambiguity_score"] = float(np.clip(0.50 + 0.45 * intensity, 0.0, 1.0))
    if "policy_conflict" in active or "prompt_adversarial_manipulation" in active:
        output["policy_conflict"] = float(np.clip(0.55 + 0.45 * intensity, 0.0, 1.0))
    if "overconfident_consensus" in active:
        output["confidence_inflation"] = float(np.clip(0.40 + 0.55 * intensity, 0.0, 1.0))
    if "malicious_specialist" in active or "evidence_source_compromise" in active:
        output["source_compromise_signal"] = float(np.clip(0.35 + 0.60 * intensity + rng.normal(0.0, 0.03), 0.0, 1.0))
    return output
