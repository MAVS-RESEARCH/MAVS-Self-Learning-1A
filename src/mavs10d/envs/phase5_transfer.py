"""Compiler for Phase 5 altered-prior leave-out, reset, and recurrence banks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import yaml

from mavs10d.core.hashing import stable_hash


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class CompiledPhase5Generation:
    visible_rows: tuple[Mapping[str, Any], ...]
    hidden_rows: tuple[Mapping[str, Any], ...]
    manifest: Mapping[str, Any]


class Phase5TransferCompiler:
    """Create 300 paired worlds while preserving evaluator/participant separation."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or REPO_ROOT / "configs/phases/phase5.yaml"
        self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))

    def compile_generation(self, generation: int) -> CompiledPhase5Generation:
        if generation not in (1, 2, 3):
            raise ValueError("Phase 5 generation must be 1, 2, or 3.")
        low, high = self.config["final_seed_ranges"][generation]
        seeds = list(range(int(low), int(high) + 1))
        if len(seeds) != 300:
            raise ValueError("Phase 5 requires exactly 300 world seeds per generation.")
        strata = _schedule(self.config["benchmark_strata"], 810000 + generation)
        resets = _schedule(self.config["reset_mixtures"][generation], 820000 + generation)
        domains = tuple(self.config["domains"])
        families = tuple(self.config["corruption_families"])
        generators = tuple(self.config["generator_implementations"])
        attacker_families = tuple(self.config["attack"]["families"])
        visible: list[Mapping[str, Any]] = []
        hidden: list[Mapping[str, Any]] = []
        for world_index, seed in enumerate(seeds):
            rng = np.random.default_rng(seed)
            stratum = strata[world_index]
            reset_type = resets[world_index]
            domain = domains[(world_index + generation) % len(domains)]
            heldout_domain = domains[(world_index + generation + 2) % len(domains)]
            corruption_family = families[(world_index * 3 + generation) % len(families)]
            heldout_family = families[(world_index * 3 + generation + 1) % len(families)]
            composition_id = f"C{(world_index + 7 * generation) % 20:02d}"
            heldout_composition = f"C{(world_index + 7 * generation + 11) % 20:02d}"
            generator_id = generators[1] if stratum == "generator_leave_out" else generators[0]
            policy_id = f"policy-semantic-g{generation}-{world_index % 12:02d}"
            prevalence = float(rng.uniform(0.14, 0.68))
            shift_base = {"surface": 0.22, "structural": 0.55, "adversarial": 0.78}[reset_type]
            world_id = f"p5-g{generation}-w{world_index:03d}"
            mechanism_id = f"mechanism-{(world_index * 5 + generation) % 37:02d}"
            for step in range(50):
                recurrence = stratum == "long_horizon_recurrence" and (step >= 35 or 8 <= step < 15)
                unsafe_probability = np.clip(prevalence + (0.12 if recurrence else 0.0), 0.02, 0.92)
                unsafe = bool(rng.random() < unsafe_probability)
                latent = float(np.clip((0.80 if unsafe else 0.20) + rng.normal(0.0, 0.16) + 0.06 * shift_base, 0.0, 1.0))
                evidence_available = bool(rng.random() < (0.92 - 0.35 * shift_base))
                feedback_released = bool(step > 0 and rng.random() < (0.88 - 0.18 * shift_base))
                feedback_reliable = float(rng.uniform(0.75, 1.0) if feedback_released else 0.0)
                conflict = float(np.clip(abs(latent - float(unsafe)) + 0.20 * shift_base + rng.normal(0, 0.05), 0, 1))
                noise = lambda scale: float(np.clip(latent + rng.normal(0.0, scale), 0.0, 1.0))
                abstract_similarity = float(np.clip(0.88 - 0.55 * shift_base + rng.normal(0, 0.07), 0, 1))
                raw_similarity = float(np.clip(0.92 if reset_type == "surface" else 0.18 + rng.normal(0, 0.08), 0, 1))
                attack_probe = reset_type == "adversarial" and step < int(self.config["attack"]["probes_per_adversarial_world"])
                attacker_family = attacker_families[step % len(attacker_families)] if attack_probe else "none"
                opportunity_id = f"p5-g{generation}-w{world_index:03d}-s{step:02d}"
                visible.append({
                    "opportunity_id": opportunity_id, "world_id": world_id, "generation": generation,
                    "world_seed": seed, "world_index": world_index, "step": step,
                    "benchmark_stratum": stratum, "reset_type": reset_type, "domain": domain,
                    "heldout_domain": heldout_domain, "corruption_family": corruption_family,
                    "heldout_corruption_family": heldout_family, "composition_id": composition_id,
                    "heldout_composition_id": heldout_composition, "generator_id": generator_id,
                    "policy_id": policy_id, "context_namespace": f"p5:{stratum}:{reset_type}:{domain}",
                    "risk_proxy": noise(0.19), "certified_signal": noise(0.08 if evidence_available else 0.22),
                    "safe_witness": float(np.clip(1.0 - latent + rng.normal(0, 0.08), 0, 1)),
                    "danger_witness": noise(0.09), "provenance_quality": float(np.clip((0.90 if evidence_available else 0.25) - 0.20 * shift_base, 0, 1)),
                    "meta_novelty": float(np.clip(0.25 + 0.65 * shift_base + rng.normal(0, 0.06), 0, 1)),
                    "coverage_gap": float(np.clip(0.15 + 0.60 * shift_base + rng.normal(0, 0.06), 0, 1)),
                    "masking_signal": float(np.clip((0.25 if evidence_available else 0.82) + rng.normal(0, 0.05), 0, 1)),
                    "policy_conflict": conflict, "uncertainty": float(np.clip(conflict + 0.18 * shift_base, 0, 1)),
                    "shift_score": float(np.clip(shift_base + rng.normal(0, 0.07), 0, 1)),
                    "scope_validity": float(np.clip(0.92 - 0.52 * shift_base + rng.normal(0, 0.07), 0, 1)),
                    "abstract_similarity": abstract_similarity, "raw_similarity": raw_similarity,
                    "specialist_diversity": float(np.clip(0.82 - 0.22 * shift_base + rng.normal(0, 0.06), 0, 1)),
                    "shared_representation": float(np.clip(0.22 + 0.58 * shift_base + rng.normal(0, 0.06), 0, 1)),
                    "correlation_signal": float(np.clip(0.20 + 0.65 * shift_base + rng.normal(0, 0.05), 0, 1)),
                    "counterfactual_stability": float(np.clip(0.88 - 0.55 * shift_base + rng.normal(0, 0.06), 0, 1)),
                    "adversarial_pressure": float(attack_probe), "attack_family_visible": attacker_family,
                    "evidence_available": float(evidence_available), "feedback_released": float(feedback_released),
                    "feedback_reliability": feedback_reliable, "recurrence_visible": float(recurrence),
                    "random_key": float(rng.random()),
                })
                hidden.append({
                    "opportunity_id": opportunity_id, "unsafe": unsafe,
                    "correct_action": "reject" if unsafe else "accept",
                    "catastrophic_if_accepted": bool(unsafe and rng.random() < (0.04 + 0.18 * shift_base)),
                    "irreversible_if_accepted": bool(unsafe and rng.random() < (0.02 + 0.10 * shift_base)),
                    "hidden_mechanism": mechanism_id, "prior_family": f"prior-{world_index % 15:02d}",
                    "feedback_target": unsafe, "attacker_family": attacker_family,
                    "raw_content_hash": stable_hash(["phase5-raw", generation, seed, step]),
                    "near_duplicate_signature": stable_hash(["phase5-near", generator_id, generation, world_index, step]),
                    "answer_key_hash": stable_hash(["phase5-answer", opportunity_id, unsafe]),
                })
        expected = int(self.config["canonical_decisions_per_generation"])
        if len(visible) != expected or len(hidden) != expected:
            raise ValueError("Phase 5 canonical allocation mismatch.")
        forbidden = set(hidden[0]) - {"opportunity_id"}
        if forbidden & set(visible[0]):
            raise RuntimeError("Evaluator-only Phase 5 fields crossed the participant boundary.")
        body = {
            "schema_version": "1.0.0", "generation": generation, "world_count": 300,
            "decisions_per_world": 50, "opportunity_count": expected,
            "world_seed_min": int(low), "world_seed_max": int(high),
            "benchmark_strata": _world_counts(visible, "benchmark_stratum"),
            "reset_counts": _world_counts(visible, "reset_type"),
            "domains": sorted({row["domain"] for row in visible}),
            "corruption_families": sorted({row["corruption_family"] for row in visible}),
            "composition_count": len({row["composition_id"] for row in visible}),
            "generator_implementations": sorted({row["generator_id"] for row in visible}),
            "adversarial_probes": sum(int(row["adversarial_pressure"]) for row in visible),
            "attack_budget_per_adversarial_world": int(self.config["attack"]["probes_per_adversarial_world"]),
            "visible_fields": sorted(visible[0]), "visible_schema_sha256": stable_hash(sorted(visible[0])),
            "opportunity_ids_sha256": stable_hash([row["opportunity_id"] for row in visible]),
            "raw_content_hashes_sha256": stable_hash([row["raw_content_hash"] for row in hidden]),
            "near_duplicate_signatures_sha256": stable_hash([row["near_duplicate_signature"] for row in hidden]),
            "hidden_outcomes_sha256": stable_hash(hidden), "participant_final_access": False,
            "post_holdout_retuning": False, "model_training": "none",
        }
        return CompiledPhase5Generation(tuple(visible), tuple(hidden), body)


def _schedule(counts: Mapping[str, int], seed: int) -> tuple[str, ...]:
    values: list[str] = []
    for name, count in counts.items():
        values.extend([str(name)] * int(count))
    if len(values) != 300:
        raise ValueError("Phase 5 world schedule must contain exactly 300 entries.")
    rng = np.random.default_rng(seed)
    return tuple(np.asarray(values, dtype=object)[rng.permutation(300)].tolist())


def _world_counts(rows: list[Mapping[str, Any]], field: str) -> dict[str, int]:
    worlds = rows[::50]
    return {str(value): sum(row[field] == value for row in worlds) for value in sorted({row[field] for row in worlds})}
