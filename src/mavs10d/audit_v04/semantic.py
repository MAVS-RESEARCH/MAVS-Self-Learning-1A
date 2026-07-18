"""Independent semantic normalization, hashes, and behavioral classes."""

from __future__ import annotations

from typing import Any, Mapping

from .common import stable_hash


SEMANTIC_FIELDS = (
    "expression_ast", "parameters", "positive_scope_ast", "anti_scope_ast",
    "evidence_contract", "influence_contract", "counterfactual_contract",
)


def normalized_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {"ast_version": "mavs-diagnostic-ast-v1", **{field: candidate[field] for field in SEMANTIC_FIELDS}}


def semantic_hash(candidate: Mapping[str, Any]) -> str:
    return stable_hash(normalized_payload(candidate))


def behavior_hash(rows: list[dict[str, Any]]) -> str:
    fields = ("bank", "case_id", "raw_output", "discrete_output", "positive_scope", "anti_scope", "active", "query_influence", "authority", "terminal_influence")
    normalized = [{field: _scalar(row[field]) for field in fields} for row in sorted(rows, key=lambda item: (item["bank"], item["case_id"]))]
    return stable_hash(normalized)


def _scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def name_invariant(candidate: Mapping[str, Any], replacement: str) -> bool:
    mutated = dict(candidate)
    mutated["candidate_id"] = replacement
    mutated["candidate_name"] = replacement
    return semantic_hash(candidate) == semantic_hash(mutated)
