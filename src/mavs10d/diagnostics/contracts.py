"""Complete executable diagnostic contracts for Version 0.4 synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from mavs10d.diagnostics.ast import collect_feature_references, validate_ast


REQUIRED_EVIDENCE_FIELDS = frozenset({"sources", "provenance", "availability", "freshness_seconds", "minimum_trust", "failure_behavior"})
REQUIRED_INFLUENCE_FIELDS = frozenset({"channel", "minimum", "maximum", "terminal_authority"})
REQUIRED_COUNTERFACTUAL_FIELDS = frozenset({"nuisance_interventions", "causal_interventions", "nuisance_tolerance", "minimum_causal_delta"})
REQUIRED_LINEAGE_FIELDS = frozenset({"parents", "operation", "triggering_contrast", "synthesis_evidence", "structure_trace", "parameter_trace", "rollback_target"})


@dataclass(frozen=True)
class ExecutableDiagnostic:
    candidate_id: str
    name: str
    expression_ast: dict[str, Any]
    parameters: dict[str, float]
    positive_scope_ast: dict[str, Any]
    anti_scope_ast: dict[str, Any]
    evidence_contract: dict[str, Any]
    influence_contract: dict[str, Any]
    counterfactual_contract: dict[str, Any]
    lineage: dict[str, Any]
    operation_payload: dict[str, Any]
    integrity_control: str | None = None
    certification_control: str | None = None

    def validate(self) -> None:
        if not self.candidate_id or not self.name:
            raise ValueError("Candidate ID and documentation name are required.")
        validate_ast(self.expression_ast, self.parameters)
        validate_ast(self.positive_scope_ast, self.parameters)
        validate_ast(self.anti_scope_ast, self.parameters)
        self._require_fields("evidence_contract", self.evidence_contract, REQUIRED_EVIDENCE_FIELDS)
        self._require_fields("influence_contract", self.influence_contract, REQUIRED_INFLUENCE_FIELDS)
        self._require_fields("counterfactual_contract", self.counterfactual_contract, REQUIRED_COUNTERFACTUAL_FIELDS)
        self._require_fields("lineage", self.lineage, REQUIRED_LINEAGE_FIELDS)
        if float(self.influence_contract["minimum"]) > float(self.influence_contract["maximum"]):
            raise ValueError("Influence bounds are invalid.")
        declared_sources = set(self.evidence_contract["sources"])
        referenced = set(self.all_feature_references())
        if not referenced <= declared_sources:
            raise ValueError(f"Evidence contract omits feature dependencies: {sorted(referenced - declared_sources)}")

    def all_feature_references(self) -> tuple[str, ...]:
        references = set(collect_feature_references(self.expression_ast))
        references.update(collect_feature_references(self.positive_scope_ast))
        references.update(collect_feature_references(self.anti_scope_ast))
        return tuple(sorted(references))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "candidate_id": self.candidate_id,
            "candidate_name": self.name,
            "expression_ast": self.expression_ast,
            "parameters": self.parameters,
            "positive_scope_ast": self.positive_scope_ast,
            "anti_scope_ast": self.anti_scope_ast,
            "evidence_contract": self.evidence_contract,
            "influence_contract": self.influence_contract,
            "counterfactual_contract": self.counterfactual_contract,
            "lineage": self.lineage,
            "operation_payload": self.operation_payload,
            "integrity_control": self.integrity_control,
            "certification_control": self.certification_control,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExecutableDiagnostic":
        candidate = cls(
            candidate_id=str(payload["candidate_id"]),
            name=str(payload["candidate_name"]),
            expression_ast=dict(payload["expression_ast"]),
            parameters={str(key): float(value) for key, value in payload["parameters"].items()},
            positive_scope_ast=dict(payload["positive_scope_ast"]),
            anti_scope_ast=dict(payload["anti_scope_ast"]),
            evidence_contract=dict(payload["evidence_contract"]),
            influence_contract=dict(payload["influence_contract"]),
            counterfactual_contract=dict(payload["counterfactual_contract"]),
            lineage=dict(payload["lineage"]),
            operation_payload=dict(payload["operation_payload"]),
            integrity_control=payload.get("integrity_control"),
            certification_control=payload.get("certification_control"),
        )
        candidate.validate()
        return candidate

    @staticmethod
    def _require_fields(name: str, value: Mapping[str, Any], required: frozenset[str]) -> None:
        missing = required - set(value)
        if missing:
            raise ValueError(f"{name} is missing fields: {sorted(missing)}")
