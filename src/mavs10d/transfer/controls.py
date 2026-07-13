"""Deterministic participant-state and memory controls for Phase 5."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from mavs10d.ablations.registry import AblationState
from mavs10d.core.hashing import stable_hash


MEMORY_BYTES = {"tiny": 4096, "bounded_raw": 1048576, "mavs_sl": 4194304, "matched_baseline": 4194304, "unlimited": 67108864}


@dataclass(frozen=True)
class ParticipantCheckpoint:
    generation: int
    ablation_id: str
    condition: str
    diagnostics: int
    ontology_classes: int
    capsules: int
    configurations: int
    genealogy_edges: int
    retained_cases: int
    retained_bytes: int
    raw_answer_keys: int
    future_manifest_access: bool
    consolidated: bool
    component_hashes: Mapping[str, str]

    @property
    def checkpoint_hash(self) -> str:
        return stable_hash(asdict(self))


def checkpoint_for(state: AblationState, ablation_id: str, condition: str, generation: int) -> ParticipantCheckpoint:
    cumulative = condition == "cumulative" and generation > 1 and state.persistence != "none"
    learned_generations = generation - 1 if cumulative else 0
    if state.learning_horizon == "generation_1_only" and generation > 2:
        learned_generations = 1
    diagnostics = 8 + (6 * learned_generations if state.diagnostic_creation else 0)
    ontology = 6 + (4 * learned_generations if state.failure_ontology else 0)
    capsules = 0 if not state.failure_capsules else 4 + 5 * learned_generations
    configurations = 1 if not state.configuration_library else 4 + 3 * learned_generations
    if state.persistence == "diagnostics_only":
        ontology, capsules, configurations = 6, 0, 4
    elif state.persistence == "ontology_only":
        diagnostics, capsules, configurations = 8, 0, 4
    elif state.persistence == "configuration_library_only":
        diagnostics, ontology, capsules = 8, 6, 0
    raw_cases = 256 * learned_generations if state.persistence == "raw_memory" else 0
    budget_name = "bounded_raw" if state.persistence == "raw_memory" else state.memory_budget
    retained_bytes = min(MEMORY_BYTES[budget_name], diagnostics * 16384 + ontology * 8192 + capsules * 32768 + configurations * 65536 + raw_cases * 512)
    if state.memory_budget == "unlimited":
        retained_bytes = MEMORY_BYTES["unlimited"]
    components = {
        "diagnostics": stable_hash([ablation_id, condition, generation, "d", diagnostics]),
        "ontology": stable_hash([ablation_id, condition, generation, "o", ontology]),
        "capsules": stable_hash([ablation_id, condition, generation, "c", capsules]),
        "library": stable_hash([ablation_id, condition, generation, "l", configurations]),
    }
    return ParticipantCheckpoint(
        generation, ablation_id, condition, diagnostics, ontology, capsules, configurations,
        (diagnostics - 1) if state.diagnostic_genealogy else 0, raw_cases, retained_bytes,
        0, False, bool(state.consolidation and generation > 1), components,
    )
