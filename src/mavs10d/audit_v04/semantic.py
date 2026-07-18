"""Independent semantic normalization, hashes, and behavioral classes."""

from __future__ import annotations

from typing import Any, Mapping

from .common import stable_hash


SEMANTIC_FIELDS = (
    "expression_ast", "parameters", "positive_scope_ast", "anti_scope_ast",
    "evidence_contract", "influence_contract", "counterfactual_contract",
)


COMMUTATIVE = {"and", "or", "add", "mul", "min", "max"}


def canonicalize_ast(node: Mapping[str, Any]) -> dict[str, Any]:
    operation = str(node["op"])
    if operation in {"feature", "parameter", "constant"}:
        return {key: node[key] for key in sorted(node)}
    if "children" in node:
        children = [canonicalize_ast(child) for child in node.get("children", [])]
        if operation in COMMUTATIVE:
            flattened: list[dict[str, Any]] = []
            for child in children:
                flattened.extend(child.get("children", [])) if child.get("op") == operation else flattened.append(child)
            children = sorted(flattened, key=lambda value: __import__("json").dumps(value, sort_keys=True, separators=(",", ":")))
        result = {key: node[key] for key in sorted(node) if key != "children"}
        result["children"] = children
        return result
    if "left" in node and "right" in node:
        return {"op": operation, "left": canonicalize_ast(node["left"]), "right": canonicalize_ast(node["right"])}
    raise ValueError(f"P10_NONCANONICAL_AST: {operation}")


def normalized_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ast_version": "mavs-diagnostic-ast-v1",
        "expression_ast": canonicalize_ast(candidate["expression_ast"]),
        "parameters": dict(sorted(candidate["parameters"].items())),
        "positive_scope_ast": canonicalize_ast(candidate["positive_scope_ast"]),
        "anti_scope_ast": canonicalize_ast(candidate["anti_scope_ast"]),
        "evidence_contract": candidate["evidence_contract"],
        "influence_contract": candidate["influence_contract"],
        "counterfactual_contract": candidate["counterfactual_contract"],
    }


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


def template_signature(node: Mapping[str, Any]) -> str:
    def strip(value: Any) -> Any:
        if isinstance(value, list):
            return [strip(item) for item in value]
        if not isinstance(value, dict):
            return value
        operation = value.get("op")
        if operation == "feature":
            return {"op": "feature", "name": "<feature>"}
        if operation == "parameter":
            return {"op": "parameter", "name": "<parameter>"}
        if operation == "constant":
            return {"op": "constant", "value": "<constant>"}
        return {key: strip(child) for key, child in value.items()}
    return stable_hash(strip(canonicalize_ast(node)))
