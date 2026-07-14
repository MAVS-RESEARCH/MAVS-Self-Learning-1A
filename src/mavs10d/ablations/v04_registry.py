"""Typed single-factor registry for the Version 0.4 Phase 8 causal matrix."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from mavs10d.core.hashing import stable_hash


GROUP_REFERENCES = {
    "synthesis_integrity": "I0",
    "perception_closure_runtime": "P0",
    "persistence_consolidation": "L0",
}

EXPECTED_IDS = (
    *(f"I{index}" for index in range(12)),
    *(f"P{index}" for index in range(16)),
    *(f"L{index}" for index in range(11)),
)

REFERENCE_DEFAULTS: dict[str, dict[str, Any]] = {
    "synthesis_integrity": {
        "structure_search": "protected_contrast_search",
        "semantic_deduplication": True,
        "behavioral_deduplication": True,
        "parameter_fitting": "bounded_search",
        "operation_constraints": True,
        "certifier_metadata_exposure": False,
        "hidden_field_exposure": False,
        "perception_extension_witness_gate": True,
        "counterfactual_dependency_audit": True,
        "template_collapse_alarm": True,
        "proposal_engine": "structured",
    },
    "perception_closure_runtime": {
        "resolver": "perception_closure",
        "explicit_hypothesis_set": True,
        "conditional_perception_extension": True,
        "active_query_planner": True,
        "positive_anti_scope_contract": True,
        "sparse_basis_selection": True,
        "causal_arbitration": "typed_non_additive",
        "typed_channels": True,
        "interaction_certificates": True,
        "local_closure_certificate": "decision_homogeneous",
        "uncertainty_fallback": "exhaust_valid_paths",
        "external_escalation": "residual_only",
        "unresolved_fallback": "escalate",
        "correlation_policy": "causal_provenance",
        "evidence_access": "visible_only",
    },
    "persistence_consolidation": {
        "retained_governance_state": "cumulative",
        "post_g1_learning": "enabled",
        "consolidation_and_retirement": True,
        "negative_knowledge": True,
        "persistence_payload": "full_governance_knowledge",
        "active_eligibility_cap": True,
        "periodic_recertification": True,
    },
}


@dataclass(frozen=True)
class AblationDefinition:
    schema_version: str
    id: str
    group: str
    reference_id: str
    isolated_factor: str
    toggle: dict[str, Any]
    unchanged_fields: tuple[str, ...]
    causal_question: str
    expected_direction: str
    required_metrics: tuple[str, ...]
    pass_fail_interpretation: str
    source_path: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], source_path: str) -> "AblationDefinition":
        return cls(
            schema_version=str(value["schema_version"]),
            id=str(value["id"]),
            group=str(value["group"]),
            reference_id=str(value["reference_id"]),
            isolated_factor=str(value["isolated_factor"]),
            toggle={str(key): item for key, item in value["toggle"].items()},
            unchanged_fields=tuple(map(str, value["unchanged_fields"])),
            causal_question=str(value["causal_question"]),
            expected_direction=str(value["expected_direction"]),
            required_metrics=tuple(map(str, value["required_metrics"])),
            pass_fail_interpretation=str(value["pass_fail_interpretation"]),
            source_path=source_path,
        )

    def full_config(self) -> dict[str, Any]:
        config = dict(REFERENCE_DEFAULTS[self.group])
        config.update(self.toggle)
        return config

    def normalized_diff(self) -> dict[str, Any]:
        reference = REFERENCE_DEFAULTS[self.group]
        return {
            key: {"reference": reference[key], "ablation": value}
            for key, value in sorted(self.toggle.items())
            if reference.get(key) != value
        }

    def serializable(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "group": self.group,
            "reference_id": self.reference_id,
            "isolated_factor": self.isolated_factor,
            "toggle": self.toggle,
            "unchanged_fields": list(self.unchanged_fields),
            "causal_question": self.causal_question,
            "expected_direction": self.expected_direction,
            "required_metrics": list(self.required_metrics),
            "pass_fail_interpretation": self.pass_fail_interpretation,
        }


class AblationRegistry:
    """Load, validate, and freeze all legal Phase 8 semantic toggles."""

    def __init__(self, definitions: Iterable[AblationDefinition]) -> None:
        ordered = sorted(definitions, key=lambda item: EXPECTED_IDS.index(item.id) if item.id in EXPECTED_IDS else 10_000)
        self._definitions = {item.id: item for item in ordered}
        self.validate()

    @classmethod
    def from_directory(cls, directory: Path) -> "AblationRegistry":
        definitions = []
        for path in sorted(directory.glob("*.yaml")):
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            definitions.append(AblationDefinition.from_mapping(payload, path.as_posix()))
        return cls(definitions)

    def validate(self) -> None:
        observed = tuple(self._definitions)
        missing = sorted(set(EXPECTED_IDS) - set(observed))
        extra = sorted(set(observed) - set(EXPECTED_IDS))
        if missing or extra:
            raise ValueError(f"Phase 8 matrix mismatch; missing={missing}, extra={extra}")
        factors: dict[str, set[str]] = {group: set() for group in GROUP_REFERENCES}
        for condition_id in EXPECTED_IDS:
            definition = self._definitions[condition_id]
            if GROUP_REFERENCES.get(definition.group) != definition.reference_id:
                raise ValueError(f"{condition_id} has an invalid group/reference pairing.")
            is_reference = condition_id == definition.reference_id
            if is_reference and definition.toggle:
                raise ValueError(f"Reference {condition_id} must have an empty semantic diff.")
            if not is_reference and len(definition.toggle) != 1:
                raise ValueError(f"Ablation {condition_id} must change exactly one serialized semantic factor.")
            diff = definition.normalized_diff()
            if not is_reference and len(diff) != 1:
                raise ValueError(f"Ablation {condition_id} does not differ from its reference by exactly one value.")
            if not is_reference:
                factor = next(iter(definition.toggle))
                if factor != definition.isolated_factor:
                    raise ValueError(f"Ablation {condition_id} toggle does not match its declared isolated factor.")
                if factor in factors[definition.group] and factor != "persistence_payload":
                    raise ValueError(f"Factor {factor} is duplicated within {definition.group}.")
                factors[definition.group].add(factor)
            if len(definition.unchanged_fields) < 5:
                raise ValueError(f"Ablation {condition_id} has an incomplete unchanged contract.")

    def __iter__(self):
        return (self._definitions[condition_id] for condition_id in EXPECTED_IDS)

    def __getitem__(self, condition_id: str) -> AblationDefinition:
        return self._definitions[condition_id]

    def manifest(self) -> dict[str, Any]:
        records = [item.serializable() for item in self]
        return {
            "schema_version": "1.0.0",
            "condition_count": len(records),
            "condition_ids": list(EXPECTED_IDS),
            "group_references": GROUP_REFERENCES,
            "matrix_hash": stable_hash(records),
            "definitions": records,
        }
