"""Typed, bounded, canonical executable diagnostic abstract syntax trees."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from mavs10d.core.hashing import stable_hash, stable_json_dumps


AST_VERSION = "mavs-diagnostic-ast-v1"
COMMUTATIVE_OPERATIONS = frozenset({"and", "or", "add", "mul", "min", "max"})
LOGICAL_OPERATIONS = frozenset({"and", "or", "not"})
COMPARISON_OPERATIONS = frozenset({"gte", "gt", "lte", "lt", "eq"})
ARITHMETIC_OPERATIONS = frozenset({"add", "sub", "mul", "min", "max", "clip"})


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    value_type: str
    domain: str
    provenance: str
    availability: str
    trust: str
    units: str
    lower_bound: float
    upper_bound: float
    missing_behavior: str
    permitted_operations: tuple[str, ...]


def _feature(name: str, *, domain: str, provenance: str = "visible_evidence") -> FeatureSpec:
    return FeatureSpec(
        name=name,
        value_type="number",
        domain=domain,
        provenance=provenance,
        availability="declared_per_case",
        trust="provenance_validated",
        units="normalized",
        lower_bound=0.0,
        upper_bound=1.0,
        missing_behavior="raise_missing_evidence",
        permitted_operations=("compare", "bounded_arithmetic", "counterfactual", "temporal"),
    )


FEATURE_REGISTRY: dict[str, FeatureSpec] = {
    spec.name: spec
    for spec in (
        _feature("risk_score", domain="governance_risk"),
        _feature("safe_witness", domain="typed_witness"),
        _feature("danger_witness", domain="typed_witness"),
        _feature("provenance_strength", domain="evidence_integrity", provenance="source_lineage"),
        _feature("independence_score", domain="specialist_independence"),
        _feature("evidence_available", domain="evidence_availability"),
        _feature("masking_score", domain="evidence_availability"),
        _feature("policy_conflict", domain="policy_state", provenance="executable_policy"),
        _feature("temporal_persistence", domain="temporal_relation"),
        _feature("calibration_residual", domain="calibration"),
        _feature("context_match", domain="scope_context"),
        _feature("query_signal", domain="query_output", provenance="audited_query"),
        _feature("nuisance_marker", domain="counterfactual_nuisance"),
    )
}


class ASTValidationError(ValueError):
    """Raised when an executable diagnostic AST violates the audited grammar."""


def validate_ast(node: Mapping[str, Any], parameters: Mapping[str, float] | None = None) -> None:
    """Validate a complete AST and all feature/parameter references."""
    if not isinstance(node, Mapping):
        raise ASTValidationError("AST node must be an object.")
    operation = node.get("op")
    if operation == "feature":
        name = node.get("name")
        if name not in FEATURE_REGISTRY:
            raise ASTValidationError(f"Unknown or opaque feature reference: {name!r}.")
        return
    if operation == "parameter":
        name = node.get("name")
        if not isinstance(name, str) or not name:
            raise ASTValidationError("Parameter node requires a nonempty name.")
        if parameters is not None and name not in parameters:
            raise ASTValidationError(f"Unresolved parameter reference: {name}.")
        return
    if operation == "constant":
        value = node.get("value")
        if not isinstance(value, (int, float, bool)) or not np.isfinite(float(value)):
            raise ASTValidationError("Constant must be a finite scalar.")
        return
    if operation in LOGICAL_OPERATIONS:
        children = node.get("children")
        expected = 1 if operation == "not" else 2
        if not isinstance(children, Sequence) or isinstance(children, (str, bytes)) or len(children) < expected:
            raise ASTValidationError(f"{operation} requires at least {expected} child node(s).")
        if operation == "not" and len(children) != 1:
            raise ASTValidationError("not requires exactly one child.")
        for child in children:
            validate_ast(child, parameters)
        return
    if operation in COMPARISON_OPERATIONS:
        if "left" not in node or "right" not in node:
            raise ASTValidationError(f"{operation} requires left and right nodes.")
        validate_ast(node["left"], parameters)
        validate_ast(node["right"], parameters)
        return
    if operation in ARITHMETIC_OPERATIONS:
        children = node.get("children")
        if not isinstance(children, Sequence) or isinstance(children, (str, bytes)) or len(children) < 1:
            raise ASTValidationError(f"{operation} requires child nodes.")
        if operation == "sub" and len(children) != 2:
            raise ASTValidationError("sub requires exactly two children.")
        if operation == "clip" and len(children) != 1:
            raise ASTValidationError("clip requires exactly one child.")
        for child in children:
            validate_ast(child, parameters)
        if operation == "clip":
            lower = float(node.get("lower", 0.0))
            upper = float(node.get("upper", 1.0))
            if lower > upper:
                raise ASTValidationError("clip lower bound exceeds upper bound.")
        return
    raise ASTValidationError(f"Illegal AST operation: {operation!r}.")


def collect_feature_references(node: Mapping[str, Any]) -> tuple[str, ...]:
    references: set[str] = set()

    def visit(current: Mapping[str, Any]) -> None:
        if current.get("op") == "feature":
            references.add(str(current["name"]))
        for key in ("children",):
            for child in current.get(key, []):
                visit(child)
        for key in ("left", "right"):
            child = current.get(key)
            if isinstance(child, Mapping):
                visit(child)

    visit(node)
    return tuple(sorted(references))


def canonicalize_ast(node: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic canonical form without changing executable meaning."""
    operation = str(node["op"])
    if operation in {"feature", "parameter", "constant"}:
        return {key: node[key] for key in sorted(node)}
    if operation in LOGICAL_OPERATIONS | ARITHMETIC_OPERATIONS:
        children = [canonicalize_ast(child) for child in node.get("children", [])]
        if operation in COMMUTATIVE_OPERATIONS:
            flattened: list[dict[str, Any]] = []
            for child in children:
                if child.get("op") == operation:
                    flattened.extend(child.get("children", []))
                else:
                    flattened.append(child)
            children = sorted(flattened, key=stable_json_dumps)
        result = {key: node[key] for key in sorted(node) if key not in {"children"}}
        result["children"] = children
        return result
    if operation in COMPARISON_OPERATIONS:
        return {
            "op": operation,
            "left": canonicalize_ast(node["left"]),
            "right": canonicalize_ast(node["right"]),
        }
    raise ASTValidationError(f"Cannot canonicalize illegal operation: {operation!r}.")


def evaluate_ast(
    node: Mapping[str, Any],
    features: Mapping[str, Any],
    parameters: Mapping[str, float] | None = None,
) -> np.ndarray:
    """Evaluate a validated AST against a deterministic vectorized feature mapping."""
    parameters = parameters or {}
    validate_ast(node, parameters)
    length = _feature_length(features)

    def evaluate(current: Mapping[str, Any]) -> np.ndarray:
        operation = current["op"]
        if operation == "feature":
            name = str(current["name"])
            if name not in features:
                raise KeyError(f"Required evidence feature is unavailable: {name}.")
            value = np.asarray(features[name])
            return np.full(length, value.item()) if value.ndim == 0 else value.astype(float, copy=False)
        if operation == "parameter":
            return np.full(length, float(parameters[str(current["name"])]), dtype=float)
        if operation == "constant":
            return np.full(length, float(current["value"]), dtype=float)
        if operation in COMPARISON_OPERATIONS:
            left, right = evaluate(current["left"]), evaluate(current["right"])
            return {
                "gte": np.greater_equal,
                "gt": np.greater,
                "lte": np.less_equal,
                "lt": np.less,
                "eq": np.equal,
            }[operation](left, right)
        children = [evaluate(child) for child in current.get("children", [])]
        if operation == "and":
            return np.logical_and.reduce([child.astype(bool) for child in children])
        if operation == "or":
            return np.logical_or.reduce([child.astype(bool) for child in children])
        if operation == "not":
            return np.logical_not(children[0].astype(bool))
        if operation == "add":
            return np.add.reduce(children)
        if operation == "sub":
            return children[0] - children[1]
        if operation == "mul":
            return np.multiply.reduce(children)
        if operation == "min":
            return np.minimum.reduce(children)
        if operation == "max":
            return np.maximum.reduce(children)
        if operation == "clip":
            return np.clip(children[0], float(current.get("lower", 0.0)), float(current.get("upper", 1.0)))
        raise ASTValidationError(f"Illegal operation during evaluation: {operation!r}.")

    result = evaluate(node)
    if result.shape != (length,):
        raise ASTValidationError(f"AST result shape {result.shape} does not equal expected {(length,)}.")
    return result


def ast_complexity(node: Mapping[str, Any]) -> int:
    descendants = list(node.get("children", []))
    for key in ("left", "right"):
        child = node.get(key)
        if isinstance(child, Mapping):
            descendants.append(child)
    return 1 + sum(ast_complexity(child) for child in descendants)


def ast_hash(node: Mapping[str, Any]) -> str:
    return stable_hash({"ast_version": AST_VERSION, "ast": canonicalize_ast(node)})


def template_signature(node: Mapping[str, Any]) -> str:
    """Hash executable shape while removing leaf names and scalar values."""
    canonical = canonicalize_ast(node)

    def strip(current: Any) -> Any:
        if isinstance(current, list):
            return [strip(value) for value in current]
        if not isinstance(current, dict):
            return current
        operation = current.get("op")
        if operation == "feature":
            return {"op": "feature", "name": "<feature>"}
        if operation == "parameter":
            return {"op": "parameter", "name": "<parameter>"}
        if operation == "constant":
            return {"op": "constant", "value": "<constant>"}
        return {key: strip(value) for key, value in current.items()}

    return stable_hash(strip(canonical))


def feature_registry_payload() -> dict[str, dict[str, Any]]:
    return {name: asdict(spec) for name, spec in sorted(FEATURE_REGISTRY.items())}


def _feature_length(features: Mapping[str, Any]) -> int:
    lengths = {np.asarray(value).shape[0] for value in features.values() if np.asarray(value).ndim > 0}
    if not lengths:
        return 1
    if len(lengths) != 1:
        raise ASTValidationError(f"Feature vectors have inconsistent lengths: {sorted(lengths)}.")
    return lengths.pop()
