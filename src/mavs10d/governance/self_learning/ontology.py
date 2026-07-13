"""Versioned failure ontology with split, merge, projection, and genealogy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from mavs10d.core.hashing import stable_hash


@dataclass(frozen=True)
class FailureFamily:
    family_id: str
    semantic_definition: str
    context_predicates: Mapping[str, Any]
    observable_signature: Mapping[str, Any]
    causal_hypotheses: tuple[str, ...]
    severity_scale: Mapping[str, float]
    permissible_responses: tuple[str, ...]
    known_confounders: tuple[str, ...]
    confidence: float
    status: str
    parent_ids: tuple[str, ...]
    projections: tuple[str, ...]
    version: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Ontology confidence must be within [0, 1].")
        if self.status not in {"provisional", "approved", "retired", "merged"}:
            raise ValueError("Invalid failure-family status.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FailureOntology:
    def __init__(self) -> None:
        self._families: dict[str, FailureFamily] = {}
        self._genealogy: list[dict[str, Any]] = []

    def add(self, family: FailureFamily, reason: str) -> None:
        if family.family_id in self._families:
            raise ValueError("Failure-family IDs are immutable and unique.")
        self._families[family.family_id] = family
        self._record("add", (), (family.family_id,), reason)

    def approve(self, family_id: str, reason: str) -> None:
        family = self._families[family_id]
        self._families[family_id] = FailureFamily(**{**family.to_dict(), "status": "approved", "version": family.version + 1})
        self._record("approve", (family_id,), (family_id,), reason)

    def split(self, parent_id: str, children: tuple[FailureFamily, ...], reason: str) -> None:
        if len(children) < 2:
            raise ValueError("Ontology split requires at least two children.")
        parent = self._families[parent_id]
        for child in children:
            if parent_id not in child.parent_ids:
                raise ValueError("Split children must reference their parent.")
            self.add(child, reason)
        self._families[parent_id] = FailureFamily(**{**parent.to_dict(), "status": "retired", "version": parent.version + 1})
        self._record("split", (parent_id,), tuple(item.family_id for item in children), reason)

    def merge(self, parent_ids: tuple[str, ...], merged: FailureFamily, reason: str) -> None:
        if len(parent_ids) < 2 or set(parent_ids) != set(merged.parent_ids):
            raise ValueError("Merged family must name every parent.")
        for parent_id in parent_ids:
            parent = self._families[parent_id]
            self._families[parent_id] = FailureFamily(**{**parent.to_dict(), "status": "merged", "version": parent.version + 1})
        self.add(merged, reason)
        self._record("merge", parent_ids, (merged.family_id,), reason)

    def retire(self, family_id: str, reason: str) -> None:
        family = self._families[family_id]
        self._families[family_id] = FailureFamily(**{**family.to_dict(), "status": "retired", "version": family.version + 1})
        self._record("retire", (family_id,), (), reason)

    def active(self) -> tuple[FailureFamily, ...]:
        return tuple(item for item in self._families.values() if item.status in {"provisional", "approved"})

    def all(self) -> tuple[FailureFamily, ...]:
        return tuple(self._families.values())

    def genealogy(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._genealogy)

    @property
    def ontology_hash(self) -> str:
        return stable_hash({"families": [item.to_dict() for item in self._families.values()], "genealogy": self._genealogy})

    def _record(self, operation: str, parents: tuple[str, ...], children: tuple[str, ...], reason: str) -> None:
        payload = {"operation": operation, "parents": parents, "children": children, "reason": reason, "sequence": len(self._genealogy)}
        self._genealogy.append({**payload, "event_hash": stable_hash(payload)})
